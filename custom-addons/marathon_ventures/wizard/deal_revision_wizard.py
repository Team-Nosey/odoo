# -*- coding: utf-8 -*-
"""Deal Revisions Wizard.

This wizard implements the *Deal Revisions* tool described in the
Marathon Ventures *Salesforce Orders II — Revisions* documentation. The
SF version exposes nine tabs:

    1. LTC          — cancel everything after a Last-To-Clear date.
    2. Rate         — change rate from a Monday onwards.
    3. Extend       — duplicate weekly schedules up through an end date.
    4. Frequency    — change Units Available from a Monday onwards.
    5. Test         — flag schedules as Test for one or more weeks.
    6. Cap          — change cap % from a Monday onwards.
    7. Daypart      — adjust days-allowed / start-end / daypart.
    8. Hiatus       — black out a date range across all dayparts.
    9. Max Per Day  — adjust max/day from a Monday onwards.

Each operation respects the SF rule that the start date must be a
Monday (or, for Hiatus, the exact start/end of the hiatus).
"""

from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class DealRevisionWizard(models.TransientModel):
    _name = 'marathon.deal.revision.wizard'
    _description = 'Deal Revisions Wizard'

    deal_id = fields.Many2one(
        'marathon.deal', string='Deal', required=True, readonly=True,
    )
    operation = fields.Selection(
        [
            ('ltc', 'LTC (Cancellation)'),
            ('rate', 'Rate'),
            ('extend', 'Extend (Additional Weeks)'),
            ('frequency', 'Frequency'),
            ('test', 'Test'),
            ('cap', 'Cap'),
            ('daypart', 'Daypart'),
            ('hiatus', 'Hiatus'),
            ('max_per_day', 'Max Per Day'),
        ],
        string='Operation', required=True, default='ltc',
    )

    schedule_ids = fields.Many2many(
        'marathon.schedule', string='Lines to Update',
        domain="[('deal_parent_id', '=', deal_id)]",
        help='Tick the schedules that should be affected.',
    )
    select_all = fields.Boolean(
        string='Select All Lines',
        help='Convenience flag — populates Schedules from the deal.',
    )

    start_week = fields.Date(
        string='Start Week (Monday)',
        help='Effective Monday for the change. The selected week and all '
             'subsequent weeks are affected (Test only affects one week).',
    )

    # ---- per-operation parameters -------------------------------------- #
    new_rate = fields.Monetary(
        string='New Rate', currency_field='currency_id',
    )
    new_units = fields.Integer(string='New Units Available')
    new_cap = fields.Selection(
        [('0', 'No Cap'), ('25', '25%'), ('50', '50%'),
         ('75', '75%'), ('100', '100%')],
        string='New Cap',
    )
    new_max_per_day = fields.Integer(string='New Max Per Day')
    extend_to_week = fields.Date(
        string='Extend Through Week (Monday)',
        help='The last Monday week that should be present in the deal after '
             'extending. Existing schedules are duplicated up to this date.',
    )

    # Daypart sub-form
    new_daypart = fields.Selection(
        [
            ('em', 'EM'), ('da', 'DA'), ('ef', 'EF'), ('ne', 'NE'),
            ('pa', 'PA'), ('pr', 'PR'), ('ln', 'LN'), ('lf', 'LF'),
            ('on', 'ON'), ('we', 'WE'), ('sd', 'SD'), ('su', 'SU'),
            ('ros', 'ROS'),
        ],
        string='New Daypart',
    )
    new_start_time = fields.Float(string='New Start Time')
    new_end_time = fields.Float(string='New End Time')
    new_days_mon = fields.Boolean(string='Mon')
    new_days_tue = fields.Boolean(string='Tue')
    new_days_wed = fields.Boolean(string='Wed')
    new_days_thu = fields.Boolean(string='Thu')
    new_days_fri = fields.Boolean(string='Fri')
    new_days_sat = fields.Boolean(string='Sat')
    new_days_sun = fields.Boolean(string='Sun')

    # Hiatus
    hiatus_start = fields.Date(string='Hiatus Start Date')
    hiatus_end = fields.Date(string='Hiatus End Date')
    hiatus_time_before = fields.Float(string='Hiatus Time Before')
    hiatus_time_after = fields.Float(string='Hiatus Time After')

    # Test (one week)
    is_test_value = fields.Boolean(string='Mark As Test', default=True)

    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        related='deal_id.currency_id', readonly=True,
    )

    # ------------------------------------------------------------------- #
    @api.onchange('select_all', 'deal_id')
    def _onchange_select_all(self):
        if self.select_all and self.deal_id:
            self.schedule_ids = self.deal_id.schedule_ids
        elif not self.select_all:
            self.schedule_ids = False

    # ------------------------------------------------------------------- #
    # Validation helpers
    # ------------------------------------------------------------------- #
    def _check_monday(self, d, label='Start Week'):
        if d and d.weekday() != 0:
            raise UserError(_(
                "%s must be a Monday (received %s, which is a %s).",
                label, d, d.strftime('%A'),
            ))

    def _selected_lines(self):
        self.ensure_one()
        if not self.schedule_ids:
            raise UserError(_(
                "No schedules selected. Tick at least one line — or use the "
                "'Select All' checkbox — before clicking Update."
            ))
        return self.schedule_ids

    # ------------------------------------------------------------------- #
    # Main dispatch
    # ------------------------------------------------------------------- #
    def action_update(self):
        self.ensure_one()
        op = self.operation
        meth = getattr(self, '_apply_%s' % op, None)
        if not meth:
            raise UserError(_("Unknown operation: %s", op))
        meth()
        self.deal_id.message_post(
            body=_("Deal Revisions: '%s' applied (%d lines).",
                   dict(self._fields['operation'].selection).get(op),
                   len(self.schedule_ids)),
        )
        self.deal_id.revised = True
        return {'type': 'ir.actions.act_window_close'}

    # ------------------------------------------------------------------- #
    # 1. LTC — cancel everything from start_week onward; in-week trim
    #    of days allowed past the LTC date.
    # ------------------------------------------------------------------- #
    def _apply_ltc(self):
        if not self.start_week:
            raise UserError(_("LTC date is required."))
        ltc = self.start_week
        for s in self._selected_lines():
            if s.week and s.week > ltc:
                s.is_cancelled = True
                s.cancel_date = ltc
            elif s.week and ltc.weekday() == 0 == s.week.weekday() and s.week == ltc:
                # The same week as LTC — keep up to LTC weekday only.
                # (Detailed in-week trim is left for the per-schedule view.)
                wd = ltc.weekday()
                if wd < 5:  # ltc on Mon-Fri -> remove later weekdays
                    if wd < 1:
                        s.days_tue = False
                    if wd < 2:
                        s.days_wed = False
                    if wd < 3:
                        s.days_thu = False
                    if wd < 4:
                        s.days_fri = False
                # weekend always trimmed when LTC is mid-week
                s.days_sat = False
                s.days_sun = False
            elif s.week and s.week < ltc:
                # before the LTC week — leave alone
                continue
        self.deal_id.ltc_date = ltc

    # ------------------------------------------------------------------- #
    # 2. Rate
    # ------------------------------------------------------------------- #
    def _apply_rate(self):
        self._check_monday(self.start_week)
        if not self.start_week or self.new_rate is None:
            raise UserError(_("Both Start Week and New Rate are required."))
        for s in self._selected_lines():
            if s._is_in_or_after(self.start_week):
                s.rate = self.new_rate

    # ------------------------------------------------------------------- #
    # 3. Extend — duplicate the latest week up to the target end week
    # ------------------------------------------------------------------- #
    def _apply_extend(self):
        self._check_monday(self.extend_to_week, label='Extend Through Week')
        if not self.extend_to_week:
            raise UserError(_("Extend Through Week is required."))
        target = self.extend_to_week
        for s in self._selected_lines():
            if not s.week:
                continue
            current = s.week
            # walk forward by 7 days at a time, copying until target reached
            week = current + timedelta(days=7)
            while week <= target:
                # Avoid duplicating an existing week with the same daypart
                exists = self.env['marathon.schedule'].search_count([
                    ('deal_parent_id', '=', s.deal_parent_id.id),
                    ('week', '=', week),
                    ('daypart', '=', s.daypart),
                    ('start_time', '=', s.start_time),
                    ('end_time', '=', s.end_time),
                ])
                if not exists:
                    s.copy({
                        'week': week,
                        'is_cancelled': False,
                        'cancel_date': False,
                    })
                week += timedelta(days=7)

    # ------------------------------------------------------------------- #
    # 4. Frequency
    # ------------------------------------------------------------------- #
    def _apply_frequency(self):
        self._check_monday(self.start_week)
        if not self.start_week or self.new_units is None:
            raise UserError(_("Both Start Week and New Units Available are required."))
        for s in self._selected_lines():
            if s._is_in_or_after(self.start_week):
                s.units_available = self.new_units

    # ------------------------------------------------------------------- #
    # 5. Test — affects only the selected single week
    # ------------------------------------------------------------------- #
    def _apply_test(self):
        self._check_monday(self.start_week)
        if not self.start_week:
            raise UserError(_("Start Week is required."))
        for s in self._selected_lines():
            if s.week == self.start_week:
                s.is_test = self.is_test_value

    # ------------------------------------------------------------------- #
    # 6. Cap
    # ------------------------------------------------------------------- #
    def _apply_cap(self):
        self._check_monday(self.start_week)
        if not self.start_week or not self.new_cap:
            raise UserError(_("Both Start Week and New Cap are required."))
        for s in self._selected_lines():
            if s._is_in_or_after(self.start_week):
                s.cap = self.new_cap

    # ------------------------------------------------------------------- #
    # 7. Daypart
    # ------------------------------------------------------------------- #
    def _apply_daypart(self):
        self._check_monday(self.start_week)
        if not self.start_week:
            raise UserError(_("Start Week is required."))
        vals = {}
        if self.new_daypart:
            vals['daypart'] = self.new_daypart
        if self.new_start_time:
            vals['start_time'] = self.new_start_time
        if self.new_end_time:
            vals['end_time'] = self.new_end_time
        # Always overwrite days_* so unticking a day actually removes it
        vals.update({
            'days_mon': self.new_days_mon,
            'days_tue': self.new_days_tue,
            'days_wed': self.new_days_wed,
            'days_thu': self.new_days_thu,
            'days_fri': self.new_days_fri,
            'days_sat': self.new_days_sat,
            'days_sun': self.new_days_sun,
        })
        for s in self._selected_lines():
            if s._is_in_or_after(self.start_week):
                s.write(vals)

    # ------------------------------------------------------------------- #
    # 8. Hiatus
    # ------------------------------------------------------------------- #
    def _apply_hiatus(self):
        if not (self.hiatus_start and self.hiatus_end):
            raise UserError(_("Hiatus Start Date and End Date are required."))
        if self.hiatus_end < self.hiatus_start:
            raise UserError(_("Hiatus End Date must be on or after Hiatus Start Date."))
        for s in self._selected_lines() or self.deal_id.schedule_ids:
            # Schedule's week containing any part of [hiatus_start, hiatus_end]
            if not s.week:
                continue
            week_end = s.week + timedelta(days=6)
            if s.week > self.hiatus_end or week_end < self.hiatus_start:
                continue
            # Disable each day that falls within the hiatus range
            for i, attr in enumerate(['days_mon', 'days_tue', 'days_wed',
                                       'days_thu', 'days_fri',
                                       'days_sat', 'days_sun']):
                day = s.week + timedelta(days=i)
                if self.hiatus_start <= day <= self.hiatus_end:
                    setattr(s, attr, False)
            # Persist the hiatus range on the schedule for traceability
            s.hiatus_start = self.hiatus_start
            s.hiatus_end = self.hiatus_end
            if self.hiatus_time_before:
                s.hiatus_time_before = self.hiatus_time_before
            if self.hiatus_time_after:
                s.hiatus_time_after = self.hiatus_time_after

    # ------------------------------------------------------------------- #
    # 9. Max Per Day
    # ------------------------------------------------------------------- #
    def _apply_max_per_day(self):
        self._check_monday(self.start_week)
        if not self.start_week:
            raise UserError(_("Start Week is required."))
        for s in self._selected_lines():
            if s._is_in_or_after(self.start_week):
                s.max_per_day = self.new_max_per_day or 0

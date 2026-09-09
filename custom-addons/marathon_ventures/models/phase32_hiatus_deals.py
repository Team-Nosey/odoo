# -*- coding: utf-8 -*-
"""Phase 32 - Hiatus Deals page (port of Salesforce HiatusDealsControllerV2).

Salesforce -> Odoo mapping
==========================

Objects / fields
----------------
  Deal__c                       -> mv.deal
    Name                        -> name
    Program__c                  -> program            (M2O mv.programs)
    ContactAccount__c           -> contactaccount     (Char, computed+stored)
    Brands__c                   -> brands             (M2O mv.brands)
    Advertiser__c               -> brands.advertiser.name  (see note below)
    Length__c                   -> length             (Selection, 'v_30' -> '30')
    Hiatus_Dates__c             -> hiatus_dates       (Char CSV of yyyy-mm-dd)
    Hiatus_Removed__c           -> hiatus_removed     (ADDED BY THIS FILE)
    Status__c                   -> status             (sold/canceled/budget/historical)
    CreatedDate                 -> create_date

  Schedules__c                  -> mv.schedules
    Deal_Parent__c              -> deal_parent
    Week__c                     -> week               (Date, Monday of a Mon-Sun week)
    Status__c                   -> status             (sold/canceled/sold_unflighted)
    Days_Allowed__c             -> days_allowed       (M2M mv.days_allowed.tag,
                                                       tags named/coded Mon..Sun)

  Programs__c                   -> mv.programs
  Advertiser__c (object)        -> mv.advertiser

Deliberate deviations from the Apex, and why
--------------------------------------------
1. ADVERTISER FILTER GOES THROUGH THE RELATION.
   `mv.deal.advertiser` exists as a stored computed Char, but its compute
   (`_compute_advertiser`) is still an unimplemented stub that assigns
   False - so the column is empty for every deal in the database. Rather
   than mass-recompute a stored field, this port reads and filters via
   `brands.advertiser.name`, which is the same data the SF formula
   (`Brands__r.Advertiser__r.Name`) resolved. If `_compute_advertiser` is
   implemented later, nothing here needs to change.

2. WEEK DERIVATION USES A Mon-Sun WEEK.
   The Apex does `firstDate.toStartOfWeek().addDays(1)`, i.e. Sunday + 1.
   For a date that IS a Sunday that yields the FOLLOWING Monday, which
   points at the wrong broadcast week - `Week__c` holds the Monday of a
   Mon..Sun week (the Apex's own loadSchedulesForDates comment says a date
   can fall anywhere in [Week, Week+6]). This port snaps to the Monday of
   the week CONTAINING the date, consistent with the rest of this module
   (phase12 `_broadcast_quarter_bounds`, phase25 `_quarter_mondays`).
   Net effect: Sunday dates now resolve to the correct week.

3. TEXT COMPARISONS ARE CASE-INSENSITIVE.
   SOQL `!=` on a text field is case-insensitive; Odoo's is not. The
   `ClientCode__c != 'm1'` and `Team__c != 'Onyx'` program filters are
   therefore applied in Python so behaviour matches SF.

4. ScheduleHiatus.hiatusSingleDay IS REIMPLEMENTED FROM ITS DOCUMENTED
   BEHAVIOUR - the Apex utility itself was not supplied. Per the calling
   code's comments it: strips the date's weekday from every schedule whose
   week contains the date, and cancels a schedule left with no days,
   LEAVING the stale day in Days_Allowed. That last quirk is what makes
   the restore path gate revival purely on status == canceled rather than
   on the day being absent. See _mv_hiatus_strip_day / _mv_hiatus_restore_day.
"""
import logging
from datetime import datetime, time as dtime, timedelta

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Tag names/codes seeded in data/days_allowed_seed.xml, Monday-first.
_DAY_ORDER = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

_CREATED_DATE_LOOKBACK_DAYS = 180
_CANDIDATE_QUERY_LIMIT = 2000
_MAX_RESULT_ROWS = 200
_OPTION_QUERY_LIMIT = 200

# Status an active (non-canceled) schedule carries - used when Clear Hiatus
# revives a schedule that was canceled because its last day was hiatused.
_ACTIVE_SCHEDULE_STATUS = 'sold'

# mv.deal.hiatus_dates is Char(255); a yyyy-mm-dd token plus separator is
# 11 chars, so refuse past this to avoid silent truncation.
_MAX_HIATUS_DATES = 22


def _iso(d):
    return fields.Date.to_string(d) if d else ''


def _monday_of(d):
    """Monday of the Mon-Sun week containing `d`."""
    return d - timedelta(days=d.weekday()) if d else d


def _day_name(d):
    """'Mon'..'Sun' for a date, matching the days_allowed tag names."""
    return _DAY_ORDER[d.weekday()] if d else ''


def _parse_dates_csv(csv):
    """CSV of yyyy-mm-dd -> ordered list of unique date objects.

    Unparseable tokens are skipped, matching the Apex which swallowed
    Date.valueOf failures.
    """
    out = []
    seen = set()
    for token in (csv or '').split(','):
        token = (token or '').strip()
        if not token or token in seen:
            continue
        seen.add(token)
        try:
            parsed = fields.Date.to_date(token)
        except (ValueError, TypeError):
            continue
        if parsed:
            out.append(parsed)
    return sorted(out)


def _format_hiatus_csv(csv):
    """'2026-01-05,2026-01-06' -> '01/05/2026, 01/06/2026'."""
    parts = []
    for token in (csv or '').split(','):
        token = (token or '').strip()
        if not token:
            continue
        try:
            d = fields.Date.to_date(token)
        except (ValueError, TypeError):
            d = None
        parts.append('%02d/%02d/%04d' % (d.month, d.day, d.year) if d else token)
    return ', '.join(parts)


class MvDealHiatus(models.Model):
    _name = 'mv.deal'
    _inherit = 'mv.deal'

    # SF: Hiatus_Removed__c. Did not exist in the migrated schema; the page
    # needs it so "Remove" can exclude a deal from future searches without
    # deleting anything.
    hiatus_removed = fields.Boolean(
        string='Hiatus Removed',
        default=False,
        copy=False,
        index=True,
        help='Set when a user removes this deal from the Hiatus Deals '
             'results. Excluded from future Hiatus Deals searches; the '
             'deal itself is untouched.',
    )

    # ==================================================================
    # Option providers
    # ==================================================================
    @api.model
    def hiatus_get_program_options(self):
        """SF getProgramOptions(). Domain-filters what SQL can do, then
        applies the two case-insensitive text exclusions in Python."""
        Programs = self.env['mv.programs']
        candidates = Programs.search(
            [
                ('inactive', '=', False),
                ('cable_synd', '!=', False),
                ('account_exec_1', '!=', False),
                # SOQL: NOT Name LIKE '% PP'. Odoo's `like` auto-wraps in
                # %..%, so `=like` is needed to pass the pattern verbatim.
                ('name', 'not =like', '% PP'),
            ],
            order='name asc',
        )
        options = []
        for prog in candidates:
            client_code = (prog.clientcode or '').strip().lower()
            team = (prog.team or '').strip().lower()
            if client_code == 'm1' or team == 'onyx':
                continue
            options.append({
                'label': prog.name or '',
                'value': str(prog.id),
                'recordId': prog.id,
            })
        return options

    @api.model
    def hiatus_get_advertiser_options(self, search_term=''):
        """SF getAdvertiserOptions(). Option VALUE is the advertiser name,
        because the deal side is matched by text."""
        domain = [('hold_placed_on_advertiser_account', '=', False)]
        term = (search_term or '').strip()
        if term:
            domain.append(('name', 'ilike', term))
        advertisers = self.env['mv.advertiser'].search(
            domain, order='name asc', limit=_OPTION_QUERY_LIMIT,
        )
        return [
            {'label': a.name or '', 'value': a.name or '', 'recordId': a.id}
            for a in advertisers
            if a.name
        ]

    @api.model
    def hiatus_get_agency_options(self, selected_dates_csv='', program_id=False):
        """SF getAgencyOptions(). Distinct ContactAccount values across the
        deals that match the current Program / date selection."""
        dates = _parse_dates_csv(selected_dates_csv)
        week = _monday_of(dates[0]) if dates else None
        prog_id = int(program_id) if program_id else False

        if not week and not prog_id:
            raise UserError(_(
                'Please select a date on the calendar and a program before '
                'loading agencies.'
            ))

        domain = self._mv_hiatus_base_deal_domain()
        domain.append(('contactaccount', '!=', False))
        if week:
            deal_ids = self._mv_hiatus_deal_ids_with_schedule(week, dates)
            domain.append(('id', 'in', deal_ids or [0]))
        if prog_id:
            domain.append(('program', '=', prog_id))

        deals = self.search(
            domain, order='contactaccount asc', limit=_CANDIDATE_QUERY_LIMIT,
        )
        agencies = sorted({
            d.contactaccount.strip()
            for d in deals
            if d.contactaccount and d.contactaccount.strip()
        })
        return [
            {'label': a, 'value': a, 'recordId': None}
            for a in agencies
        ]

    # ==================================================================
    # Search
    # ==================================================================
    @api.model
    def _mv_hiatus_base_deal_domain(self):
        """Conditions common to the agency + search queries."""
        cutoff_date = fields.Date.context_today(self) - timedelta(
            days=_CREATED_DATE_LOOKBACK_DAYS,
        )
        # create_date is a Datetime; build an explicit midnight datetime
        # rather than relying on date->datetime coercion in the domain.
        cutoff = datetime.combine(cutoff_date, dtime.min)
        return [
            ('create_date', '>=', fields.Datetime.to_string(cutoff)),
            ('status', '!=', 'canceled'),
            ('hiatus_removed', '=', False),
        ]

    @api.model
    def _mv_hiatus_day_tag_ids(self, dates):
        """days_allowed tag ids for the weekdays covered by `dates`.

        SF used `Days_Allowed__c INCLUDES ('Mon')` OR-ed per day. The Odoo
        equivalent is a single M2M `in` against those tag ids, which is
        already an OR.
        """
        day_names = sorted({_day_name(d) for d in dates if d})
        if not day_names:
            return []
        tags = self.env['mv.days_allowed.tag'].search([
            '|', ('code', 'in', day_names), ('name', 'in', day_names),
        ])
        return tags.ids

    @api.model
    def _mv_hiatus_deal_ids_with_schedule(self, week, dates):
        """Deal ids having a non-canceled schedule in `week` whose
        days_allowed covers at least one selected weekday."""
        domain = [
            ('week', '=', week),
            ('status', '!=', 'canceled'),
        ]
        tag_ids = self._mv_hiatus_day_tag_ids(dates)
        if tag_ids:
            domain.append(('days_allowed', 'in', tag_ids))
        scheds = self.env['mv.schedules'].search(domain)
        return list({s.deal_parent.id for s in scheds if s.deal_parent})

    @api.model
    def hiatus_search_deals(
        self,
        selected_dates_csv='',
        program_id=False,
        agencies=None,
        advertiser_search_text='',
        advertiser_exact_match=False,
    ):
        """SF searchDeals(). Returns rows already sorted, capped and
        group-headered, ready for the table."""
        dates = _parse_dates_csv(selected_dates_csv)
        date_strs = [_iso(d) for d in dates]
        week = _monday_of(dates[0]) if dates else None
        prog_id = int(program_id) if program_id else False
        exact = bool(advertiser_exact_match)

        domain = self._mv_hiatus_base_deal_domain()

        if week:
            # A deal already hiatused on a selected date has had that
            # weekday stripped from its schedule, so the schedule match
            # alone would drop it. OR in a direct hiatus_dates match so it
            # stays visible (SF "Req 1").
            deal_ids = self._mv_hiatus_deal_ids_with_schedule(week, dates)
            or_branch = [('id', 'in', deal_ids or [0])]
            for ds in date_strs:
                or_branch.append(('hiatus_dates', 'ilike', ds))
            # n leaves need n-1 OR operators in prefix notation.
            domain += ['|'] * (len(or_branch) - 1) + or_branch

        if prog_id:
            domain.append(('program', '=', prog_id))

        agency_list = [a for a in (agencies or []) if a]
        if agency_list:
            domain.append(('contactaccount', 'in', agency_list))

        term = (advertiser_search_text or '').strip()
        if term:
            # Via the relation - see deviation note 1 at the top of this file.
            domain.append((
                'brands.advertiser.name',
                '=' if exact else 'ilike',
                term,
            ))

        candidates = self.search(
            domain, order='create_date desc', limit=_CANDIDATE_QUERY_LIMIT,
        )

        days_by_deal = self._mv_hiatus_days_allowed_by_deal(candidates, week)

        selected_set = set(date_strs)
        rows = []
        for deal in candidates:
            rows.append(self._mv_hiatus_build_row(
                deal, selected_set, days_by_deal.get(deal.id, ''),
            ))

        # SF DealRow.compareTo: group key, then Length ascending.
        rows.sort(key=lambda r: (r['groupKey'], r['lengthSort']))
        rows = rows[:_MAX_RESULT_ROWS]
        self._mv_hiatus_apply_group_headers(rows)
        return rows

    @api.model
    def _mv_hiatus_days_allowed_by_deal(self, deals, week):
        """{deal_id: 'Mon;Wed;Fri'} union of days across that deal's
        non-canceled schedules in `week`."""
        if not deals or not week:
            return {}
        scheds = self.env['mv.schedules'].search([
            ('deal_parent', 'in', deals.ids),
            ('week', '=', week),
            ('status', '!=', 'canceled'),
        ])
        acc = {}
        for sched in scheds:
            names = {
                (tag.code or tag.name)
                for tag in sched.days_allowed
                if (tag.code or tag.name)
            }
            if not names:
                continue
            acc.setdefault(sched.deal_parent.id, set()).update(names)
        return {
            deal_id: ';'.join(d for d in _DAY_ORDER if d in days)
            for deal_id, days in acc.items()
        }

    @api.model
    def _mv_hiatus_length_label(self, deal):
        """Selection label for length ('v_30' -> '30'), matching the way
        <apex:column> rendered Length__c without a trailing '.0'."""
        if not deal.length:
            return ''
        label = dict(
            self._fields['length'].selection or []
        ).get(deal.length, deal.length)
        return str(label)

    @api.model
    def _mv_hiatus_build_row(self, deal, selected_dates, days_allowed):
        advertiser_name = (
            deal.brands.advertiser.name
            if deal.brands and deal.brands.advertiser else ''
        ) or ''
        contact_account = deal.contactaccount or ''
        length_label = self._mv_hiatus_length_label(deal)

        try:
            length_sort = int(float(length_label)) if length_label else 0
        except (TypeError, ValueError):
            length_sort = 0

        hiatus_dates = deal.hiatus_dates or ''
        # SF: green only when EVERY selected date is already present.
        if selected_dates:
            has_all = all(ds in hiatus_dates for ds in selected_dates)
        else:
            has_all = False

        group_label = contact_account
        if advertiser_name:
            group_label = '%s — %s' % (group_label, advertiser_name)

        return {
            'id': deal.id,
            'name': deal.name or '',
            'dealUrl': '/odoo/action-marathon_ventures.action_mv_deal/%s' % deal.id,
            'programId': deal.program.id if deal.program else None,
            'programName': deal.program.name if deal.program else '',
            'programUrl': (
                '/odoo/action-marathon_ventures.action_mv_programs/%s'
                % deal.program.id
            ) if deal.program else '',
            'contactAccount': contact_account,
            'brandId': deal.brands.id if deal.brands else None,
            'brandName': deal.brands.name if deal.brands else '',
            'brandUrl': (
                '/odoo/action-marathon_ventures.action_mv_brands/%s'
                % deal.brands.id
            ) if deal.brands else '',
            'advertiser': advertiser_name,
            'length': length_label,
            'lengthSort': length_sort,
            'daysAllowed': days_allowed or '',
            'hiatusDates': hiatus_dates,
            'formattedHiatus': _format_hiatus_csv(hiatus_dates),
            'hasSelectedDates': has_all,
            'groupKey': '%s|%s' % (contact_account, advertiser_name),
            'groupLabel': group_label,
            'showGroupHeader': False,
        }

    @api.model
    def _mv_hiatus_apply_group_headers(self, rows):
        last = None
        for row in rows:
            row['showGroupHeader'] = row['groupKey'] != last
            last = row['groupKey']

    # ==================================================================
    # Row actions
    # ==================================================================
    @api.model
    def hiatus_remove_from_results(self, deal_id):
        """SF removeDealFromResults()."""
        if not deal_id:
            return False
        deal = self.browse(int(deal_id)).exists()
        if not deal:
            raise UserError(_('Deal not found.'))
        deal.write({'hiatus_removed': True})
        return True

    @api.model
    def _mv_hiatus_validate_action(self, deal_ids, dates, action_label):
        if not dates:
            raise UserError(_(
                'Select at least one date on the calendar before clicking '
                '"%s".'
            ) % action_label)
        ids = [int(i) for i in (deal_ids or []) if i]
        if not ids:
            raise UserError(_('Check at least one deal in the results.'))
        deals = self.browse(ids).exists()
        if not deals:
            raise UserError(_('None of the selected deals still exist.'))
        return deals

    @api.model
    def hiatus_apply(self, deal_ids, selected_dates_csv=''):
        """SF applyHiatus(). Adds the dates to each deal's hiatus_dates and
        strips the matching weekday(s) from their schedules."""
        dates = _parse_dates_csv(selected_dates_csv)
        deals = self._mv_hiatus_validate_action(
            deal_ids, dates, _('Hiatus Selected Deals'),
        )
        to_add = {_iso(d) for d in dates}

        for deal in deals:
            existing = {_iso(d) for d in _parse_dates_csv(deal.hiatus_dates)}
            merged = sorted(existing | to_add)
            if len(merged) > _MAX_HIATUS_DATES:
                raise UserError(_(
                    'Deal %(deal)s would hold %(count)s hiatus dates, which '
                    'exceeds what the Hiatus Dates field can store '
                    '(%(max)s). Clear some existing dates first.'
                ) % {
                    'deal': deal.name or deal.id,
                    'count': len(merged),
                    'max': _MAX_HIATUS_DATES,
                })
            deal.write({'hiatus_dates': ','.join(merged)})

        self._mv_hiatus_strip_days(deals, dates)
        return len(deals)

    @api.model
    def hiatus_clear(self, deal_ids, selected_dates_csv=''):
        """SF clearHiatusDates(). Removes the dates and puts the weekday(s)
        back on the schedules, reviving any that were canceled."""
        dates = _parse_dates_csv(selected_dates_csv)
        deals = self._mv_hiatus_validate_action(
            deal_ids, dates, _('Clear Hiatus Selected Deals'),
        )
        to_remove = {_iso(d) for d in dates}

        for deal in deals:
            existing = {_iso(d) for d in _parse_dates_csv(deal.hiatus_dates)}
            remaining = sorted(existing - to_remove)
            deal.write({'hiatus_dates': ','.join(remaining) if remaining else False})

        self._mv_hiatus_restore_days(deals, dates)
        return len(deals)

    # ==================================================================
    # Schedule availability (SF "Req 2" / ScheduleHiatus)
    # ==================================================================
    @api.model
    def _mv_hiatus_schedules_for_dates(self, deals, dates):
        """Schedules of `deals` whose Mon-Sun week could contain any date."""
        if not deals or not dates:
            return self.env['mv.schedules']
        lo = _monday_of(min(dates))
        hi = max(dates)
        return self.env['mv.schedules'].search([
            ('deal_parent', 'in', deals.ids),
            ('week', '>=', lo),
            ('week', '<=', hi),
        ])

    @api.model
    def _mv_hiatus_strip_days(self, deals, dates):
        """Reimplementation of ScheduleHiatus.hiatusSingleDay, applied per
        date. For each schedule whose week contains the date, remove that
        weekday's tag; if it was the LAST day, cancel the schedule and
        deliberately LEAVE the stale tag in place (see deviation note 4).
        """
        schedules = self._mv_hiatus_schedules_for_dates(deals, dates)
        for sched in schedules:
            if not sched.week:
                continue
            for d in dates:
                if d < sched.week or d > sched.week + timedelta(days=6):
                    continue
                day = _day_name(d)
                if not day:
                    continue
                matching = sched.days_allowed.filtered(
                    lambda t: (t.code or t.name) == day
                )
                if not matching:
                    continue
                remaining = sched.days_allowed - matching
                if remaining:
                    sched.write({'days_allowed': [(6, 0, remaining.ids)]})
                else:
                    # Last day hiatused -> cancel, leave days_allowed stale.
                    sched.write({'status': 'canceled'})
        return True

    @api.model
    def _mv_hiatus_restore_days(self, deals, dates):
        """Mirror of _mv_hiatus_strip_days. Re-adds each cleared weekday and
        revives a canceled schedule.

        Revival is gated ONLY on status == canceled, never on the day being
        absent: the strip path leaves the stale tag behind when it cancels,
        so a day-presence check would refuse to revive exactly the
        schedules that need it.
        """
        schedules = self._mv_hiatus_schedules_for_dates(deals, dates)
        if not schedules:
            return True
        tag_by_day = {}
        for tag in self.env['mv.days_allowed.tag'].search([]):
            key = tag.code or tag.name
            if key:
                tag_by_day[key] = tag

        for sched in schedules:
            if not sched.week:
                continue
            for d in dates:
                if d < sched.week or d > sched.week + timedelta(days=6):
                    continue
                day = _day_name(d)
                tag = tag_by_day.get(day)
                if not tag:
                    continue
                vals = {}
                if tag not in sched.days_allowed:
                    vals['days_allowed'] = [(4, tag.id)]
                if sched.status == 'canceled':
                    vals['status'] = _ACTIVE_SCHEDULE_STATUS
                if vals:
                    sched.write(vals)
        return True

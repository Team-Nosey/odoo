# -*- coding: utf-8 -*-
"""Wizard: bulk-clone a schedule into N additional weeks.

Mirrors the SF "Additional Schedules" feature on the Schedule page —
extends the same line for several upcoming consecutive weeks.
"""

from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ScheduleBulkWizard(models.TransientModel):
    _name = 'marathon.schedule.bulk.wizard'
    _description = 'Bulk Schedule Creation Wizard'

    deal_id = fields.Many2one('marathon.deal', string='Deal', required=True)
    template_schedule_id = fields.Many2one(
        'marathon.schedule', string='Template Schedule', required=True,
    )
    additional_weeks = fields.Integer(
        string='Number of Additional Weeks', default=1,
        help='How many weeks to clone after the template schedule.',
    )

    def action_create(self):
        self.ensure_one()
        if self.additional_weeks < 1:
            raise UserError(_("Number of Additional Weeks must be at least 1."))
        s = self.template_schedule_id
        if not s.week:
            raise UserError(_("Template schedule has no Week set."))
        created = self.env['marathon.schedule']
        for i in range(1, self.additional_weeks + 1):
            new_week = s.week + timedelta(days=7 * i)
            # Skip if a duplicate already exists
            exists = self.env['marathon.schedule'].search_count([
                ('deal_parent_id', '=', s.deal_parent_id.id),
                ('week', '=', new_week),
                ('daypart', '=', s.daypart),
                ('start_time', '=', s.start_time),
                ('end_time', '=', s.end_time),
            ])
            if exists:
                continue
            created |= s.copy({
                'week': new_week,
                'is_cancelled': False,
                'cancel_date': False,
            })
        self.deal_id.message_post(
            body=_("%d additional schedules created from %s.",
                   len(created), s.display_name),
        )
        return {
            'type': 'ir.actions.act_window',
            'name': _('Created Schedules'),
            'res_model': 'marathon.schedule',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', created.ids)],
            'target': 'current',
        }

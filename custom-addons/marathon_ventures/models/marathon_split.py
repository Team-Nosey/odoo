# -*- coding: utf-8 -*-
"""Salesforce object: ``Split__c`` — split rev share / commission allocations."""

from odoo import api, fields, models


class MarathonSplit(models.Model):
    _name = 'marathon.split'
    _description = 'Split'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Split Name', required=True, tracking=True)
    deal_id = fields.Many2one('marathon.deal', string='Deal', tracking=True)
    program_id = fields.Many2one(
        'marathon.program', string='Program',
        related='deal_id.program_id', store=True, readonly=True,
    )
    user_id = fields.Many2one('res.users', string='User', tracking=True)
    role = fields.Selection(
        [
            ('account_exec', 'Account Executive'),
            ('lead', 'Lead'),
            ('assistant', 'Assistant'),
            ('planner', 'Planner'),
            ('vendor', 'Vendor'),
        ],
        string='Role',
    )
    split_percent = fields.Float(string='Split %', default=100.0)
    commission_percent = fields.Float(string='Commission %')
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')
    notes = fields.Text(string='Notes')
    is_active = fields.Boolean(string='Active', default=True)

    # =================================================================== #
    # === SF parity fields (auto-generated, full Salesforce field set) === #
    # =================================================================== #
    days_allowed = fields.Char(string="Days Allowed")
    double_check_date = fields.Datetime(string="Double Check Date")
    double_check = fields.Boolean(string="Double Check", default=False)
    end_time = fields.Float(string="End Time")
    isci_no_char = fields.Char(string="ISCI No Char")
    isci = fields.Char(string="ISCI")
    length = fields.Selection([('15', '15'), ('20', '20'), ('30', '30'), ('60', '60'), ('90', '90'), ('120', '120'), ('150', '150'), ('180', '180'), ('210', '210'), ('240', '240'), ('300', '300'), ('1710', '1710')], string="Length")
    rotation = fields.Float(string="Rotation")
    spot_name = fields.Char(string="Spot Name")
    start_time = fields.Float(string="Start Time")
    traffic = fields.Many2one('marathon.traffic', string="Traffic", ondelete='cascade')
    video_file = fields.Many2one('marathon.video.file', string="Video File", ondelete='set null')
    x800_number = fields.Char(string="800 Number")
    sf_active = fields.Boolean(string='Active (SF)', default=False)
    # === END SF parity fields ===
    @api.constrains('split_percent', 'commission_percent')
    def _check_percentages(self):
        for s in self:
            for label, val in [('Split %', s.split_percent),
                                ('Commission %', s.commission_percent)]:
                if val < 0 or val > 100:
                    from odoo.exceptions import ValidationError
                    raise ValidationError(
                        '%s must be between 0 and 100 (got %s).' % (label, val)
                    )

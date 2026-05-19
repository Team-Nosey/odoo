# -*- coding: utf-8 -*-
"""Salesforce object: ``Working_Log__c`` — operational log entries used
during prelog reconciliation."""

from odoo import api, fields, models


class MarathonWorkingLog(models.Model):
    _name = 'marathon.working.log'
    _description = 'Working Log'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'log_date desc'

    name = fields.Char(string='Working Log Name', required=True, tracking=True)
    program_id = fields.Many2one('marathon.program', string='Program', tracking=True)
    deal_id = fields.Many2one('marathon.deal', string='Deal')
    schedule_id = fields.Many2one('marathon.schedule', string='Schedule')

    log_date = fields.Date(string='Log Date', tracking=True)
    week = fields.Date(string='Week')
    user_id = fields.Many2one('res.users', string='Logged By',
                              default=lambda self: self.env.user)
    revision = fields.Integer(string='Revision')
    revision_cycle = fields.Integer(string='Revision Cycle')
    locked = fields.Boolean(string='Locked', tracking=True)

    state = fields.Selection(
        [
            ('open', 'Open'),
            ('reviewed', 'Reviewed'),
            ('reconciled', 'Reconciled'),
            ('closed', 'Closed'),
        ],
        string='State', default='open', tracking=True,
    )

    notes = fields.Text(string='Notes')
    issues_found = fields.Text(string='Issues Found')
    resolution = fields.Text(string='Resolution')

    prelog_data_ids = fields.One2many(
        'marathon.prelog.data', 'working_log_id', string='Prelog Data',
    )
    prelog_count = fields.Integer(
        string='# Prelog Data', compute='_compute_prelog_count',
    )

    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id,
    )

    # =================================================================== #
    # === SF parity fields (auto-generated, full Salesforce field set) === #
    # =================================================================== #
    air_date_air_time = fields.Char(string="Air Date/Air Time")
    air_date = fields.Date(string="Air Date")
    air_time = fields.Char(string="Air Time")
    asset_id = fields.Char(string="Asset Id")
    broadcast_network = fields.Char(string="Broadcast Network")
    created_date_time = fields.Datetime(string="Created Date Time")
    current_version = fields.Boolean(string="Current Version")
    day_of_week = fields.Char(string="Day of Week")
    discrepancy_reasoning = fields.Char(string="Discrepancy Reasoning")
    discrepancy = fields.Boolean(string="Discrepancy", default=False)
    double_check_pod = fields.Char(string="Double Check Pod")
    equiv_30 = fields.Float(string="Equiv :30")
    framed_duration = fields.Char(string="Framed Duration")
    hour_of_day = fields.Char(string="Hour of Day")
    isci = fields.Char(string="ISCI")
    main_network_temp = fields.Boolean(string="Main Network Temp", default=False)
    main_network = fields.Boolean(string="Main Network")
    pod = fields.Char(string="Pod")
    podded_day = fields.Char(string="Podded Day")
    program_version = fields.Integer(string="Program Version")
    segment_duration = fields.Char(string="Segment Duration")
    segment = fields.Integer(string="Segment")
    series = fields.Char(string="Series")
    spot_rate = fields.Monetary(string="Spot Rate", currency_field='currency_id')
    unfilled_time = fields.Integer(string="Unfilled Time")
    version = fields.Integer(string="Version")
    x800_number = fields.Char(string="800 Number")
    sf_prelog_data_id = fields.Many2one('marathon.prelog.data', string='Prelog Data (SF)', ondelete='set null')
    sf_title = fields.Char(string='Title')
    sf_type = fields.Selection([('Media', 'Media'), ('Episode', 'Episode')], string='Type')
    # === END SF parity fields ===

    @api.depends('prelog_data_ids')
    def _compute_prelog_count(self):
        for r in self:
            r.prelog_count = len(r.prelog_data_ids)

    def action_lock(self):
        for r in self:
            r.locked = True
            r.state = 'closed'

    def action_unlock(self):
        for r in self:
            r.locked = False
            r.state = 'open'


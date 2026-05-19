# -*- coding: utf-8 -*-
"""Salesforce objects: ``PrelogData__c`` and ``PrelogDataMirror__c``."""

from datetime import timedelta

from odoo import _, api, fields, models


class MarathonPrelogData(models.Model):
    _name = 'marathon.prelog.data'
    _description = 'Prelog Data'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'air_date desc'

    name = fields.Char(string='Name', default='/', readonly=True, copy=False)
    schedule_id = fields.Many2one(
        'marathon.schedule', string='Schedule', required=True,
        ondelete='cascade', tracking=True,
    )
    working_log_id = fields.Many2one(
        'marathon.working.log', string='Working Log',
    )
    prelog_data_mirror_id = fields.Many2one(
        'marathon.prelog.data.mirror', string='Prelog Data Mirror',
    )
    split_id = fields.Many2one('marathon.split', string='Split')

    advertiser_product = fields.Char(string='Advertiser / Product')
    agency = fields.Char(string='Agency')
    air_date = fields.Date(string='Air Date')
    batch_id = fields.Char(string='Batch ID')
    break_code = fields.Char(string='Break Code')
    broadcast_network = fields.Char(string='Broadcast Network')
    commercial_type = fields.Char(string='Commercial Type')
    field1 = fields.Char(string='Field 1')
    framed_duration = fields.Char(string='Framed Duration')
    isci = fields.Char(string='ISCI')
    line = fields.Integer(string='Line')
    locked = fields.Boolean(string='Locked')
    locked_working_log = fields.Boolean(string='Locked Working Log')
    log_schedule_mismatch = fields.Boolean(string='Log/Schedule Mismatch')
    main_network = fields.Boolean(string='Main Network')
    material_description = fields.Char(string='Material Description')
    order_product_description = fields.Char(string='Order/Product Description')
    pod = fields.Char(string='Pod')
    prelog_data_mirror_reference = fields.Char(string='Prelog Data Mirror Reference')
    rate = fields.Monetary(string='Rate', currency_field='currency_id')
    removed = fields.Boolean(string='Removed')
    schedule_ad_id = fields.Char(string='Schedule Ad ID')
    schedule_length = fields.Char(string='Schedule Length')
    schedule_time = fields.Char(string='Schedule Time')
    segment = fields.Integer(string='Segment')
    series = fields.Char(string='Series')
    snowflake_transferred = fields.Boolean(string='Snowflake Transferred')
    time_period = fields.Char(string='Time Period')
    title = fields.Char(string='Title')
    type = fields.Selection(
        [('Media', 'Media'), ('Episode', 'Episode')],
        string='Type',
    )
    unique_spot = fields.Char(string='Unique Spot')
    version = fields.Integer(string='Version')
    current_version = fields.Boolean(string='Current Version')
    current_version_rollup = fields.Boolean(string='Current Version Rollup')
    duration = fields.Char(string='Duration')
    air_time_hour = fields.Integer(string='Air Time Hour')
    hour_of_day = fields.Char(string='Hour of Day')
    day_of_week = fields.Char(string='Day of Week')
    week = fields.Date(string='Week', compute='_compute_week', store=True)
    schedule_week = fields.Date(
        string='Schedule Week', related='schedule_id.week', store=True, readonly=True,
    )
    agency_match_error = fields.Boolean(string='Agency Match Error')
    estimated_000_primary_demo = fields.Float(string='Estimated 000 (Primary Demo)')
    actual_000_primary_demo = fields.Float(string='Actual 000 (Primary Demo)')
    total_000_primary_demo = fields.Float(string='Total 000 (Primary Demo)')
    liability_000 = fields.Float(string='Liability 000')
    max_per_day_count = fields.Integer(string='Max Per Day Count')
    prelog_equiv_30 = fields.Float(string='Prelog Equiv :30')
    total_dollars_earned = fields.Monetary(
        string='Total Dollars Earned', currency_field='currency_id',
    )
    network = fields.Char(string='Network')
    product = fields.Char(string='Product')
    current_home = fields.Char(string='Current Home')
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id,
    )
    @api.depends('air_date')
    def _compute_week(self):
        for r in self:
            if r.air_date:
                r.week = r.air_date - timedelta(days=r.air_date.weekday())
            else:
                r.week = False


class MarathonPrelogDataMirror(models.Model):
    _name = 'marathon.prelog.data.mirror'
    _description = 'Prelog Data Mirror'
    _order = 'air_date desc'

    name = fields.Char(string='Name', default='/')
    deal_id = fields.Many2one('marathon.deal', string='Deal')
    schedule_id = fields.Many2one('marathon.schedule', string='Schedule')
    prelog_data_id = fields.Many2one('marathon.prelog.data', string='Prelog Data')
    advertiser_product = fields.Char(string='Advertiser / Product')
    agency = fields.Char(string='Agency')
    air_date = fields.Date(string='Air Date')
    batch_id = fields.Char(string='Batch ID')
    break_code = fields.Char(string='Break Code')
    commercial_type = fields.Char(string='Commercial Type')
    current_home = fields.Char(string='Current Home')
    error_reason = fields.Selection(
        [('Unit Length not found', 'Unit Length not found'), ('Air Date does not match', 'Air Date does not match'), ('Air Time does not match', 'Air Time does not match'), ('Rate not found', 'Rate not found'), ('Network Deal number not found', 'Network Deal number not found'), ('No Network Deal number', 'No Network Deal number')],
        string='Error Reason',
    )
    field1 = fields.Char(string='Field 1')
    line = fields.Integer(string='Line')
    log_schedule = fields.Char(string='Log Schedule')
    material_description = fields.Char(string='Material Description')
    network_deal_number = fields.Char(string='Network Deal Number')
    network = fields.Char(string='Network')
    order_product_description = fields.Char(string='Order Product Description')
    problem = fields.Boolean(string='Problem')
    process_required = fields.Boolean(string='Process Required')
    product = fields.Char(string='Product')
    rate = fields.Monetary(string='Rate', currency_field='currency_id')
    reason_for_unmatched = fields.Char(string='Reason for Unmatched')
    removal_reason = fields.Selection(
        [('Overrun', 'Overrun'), ('Out of Rotation', 'Out of Rotation'), ('Not Booked', 'Not Booked'), ('Other', 'Other'), ('Canceled', 'Canceled'), ('Hiatused', 'Hiatused'), ('CIA', 'CIA'), ('LOG issues', 'LOG issues'), ('Rate Change', 'Rate Change'), ('Duplicate', 'Duplicate')],
        string='Removal Reason',
    )
    schedule_ad_id = fields.Char(string='Schedule Ad ID')
    schedule_length = fields.Char(string='Schedule Length')
    schedule_time = fields.Char(string='Schedule Time')
    time_period = fields.Char(string='Time Period')
    version = fields.Integer(string='Version', required=True, default=1)
    week = fields.Date(string='Week')
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id,
    )

    # ------------------------------------------------------------------ #
    # Prelog removal workflow                                            #
    #                                                                    #
    # Per SF training "prelog-removal-process":                          #
    #   - Spots are NEVER deleted from SF — they are archived            #
    #   - Removing a spot = setting Removal Reason                       #
    #   - Retrieving = clearing the Removal Reason ("None")              #
    #   - Planner must confirm the underlying error has been corrected   #
    #     before Assistant removes the spot                              #
    # ------------------------------------------------------------------ #
    is_archived = fields.Boolean(
        string='Archived', compute='_compute_is_archived', store=True,
        help='True when a Removal Reason is set; the spot then disappears '
             'from the active prelog list view.',
    )
    planner_confirmed_correction = fields.Boolean(
        string='Planner Confirmed Correction',
        help='Required before Removal Reason can be set.',
    )
    archived_date = fields.Datetime(string='Archived Date', readonly=True)
    archived_by_id = fields.Many2one(
        'res.users', string='Archived By', readonly=True,
    )

    @api.depends('removal_reason')
    def _compute_is_archived(self):
        for r in self:
            r.is_archived = bool(r.removal_reason)

    def action_remove_from_prelog(self):
        """Archive the spot (Step 3 in SF training)."""
        for r in self:
            if not r.removal_reason:
                from odoo.exceptions import UserError
                raise UserError(_(
                    'Set a Removal Reason before removing the spot from '
                    'the prelog.'
                ))
            if not r.planner_confirmed_correction:
                from odoo.exceptions import UserError
                raise UserError(_(
                    'Per training: Planner must confirm the underlying '
                    'error has been corrected before removing this spot.'
                ))
            r.write({
                'archived_date': fields.Datetime.now(),
                'archived_by_id': self.env.user.id,
            })

    def action_retrieve_from_archive(self):
        """Un-archive: change Removal Reason to None and restore."""
        self.write({
            'removal_reason': False,
            'planner_confirmed_correction': False,
            'archived_date': False,
            'archived_by_id': False,
        })

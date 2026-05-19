# -*- coding: utf-8 -*-
"""Salesforce objects: ``Spot_Data__c``, ``SpotDataMirror__c``,
``Spot_Data_PI_Junction__c``.

Spot Data records actual aired commercial spots reconciled against
scheduled inventory. The Mirror table holds raw / unprocessed records
imported from external systems before reconciliation.
"""

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class MarathonSpotData(models.Model):
    _name = 'marathon.spot.data'
    _description = 'Spot Data'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'air_date desc, air_time desc'
    _rec_name = 'unique_spot'

    unique_spot = fields.Char(string='Unique Spot ID', required=True, copy=False)
    schedule_id = fields.Many2one(
        'marathon.schedule', string='Schedule', ondelete='cascade',
    )
    deal_id = fields.Many2one(
        'marathon.deal', string='Deal',
        related='schedule_id.deal_parent_id', store=True, readonly=True,
    )
    program_id = fields.Many2one(
        'marathon.program', string='Program',
        related='schedule_id.program_id', store=True, readonly=True,
    )
    advertiser_id = fields.Many2one(
        'marathon.advertiser', string='Advertiser',
        related='schedule_id.advertiser_id', store=True, readonly=True,
    )
    brand_id = fields.Many2one(
        'marathon.brand', string='Brand',
        related='schedule_id.brand_id', store=True, readonly=True,
    )
    split_id = fields.Many2one('marathon.split', string='Split')

    air_date = fields.Date(string='Air Date', tracking=True)
    air_time = fields.Char(string='Air Time')
    duration = fields.Char(string='Duration')
    framed_duration = fields.Char(string='Framed Duration')
    isci = fields.Char(string='ISCI')
    title = fields.Char(string='Title')
    series = fields.Char(string='Series')
    pod = fields.Char(string='Pod')
    segment = fields.Integer(string='Segment')

    rate = fields.Monetary(string='Rate', currency_field='currency_id')
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id,
    )

    type = fields.Selection(
        [
            ('paid', 'Paid'),
            ('bonus', 'Bonus'),
            ('test', 'Test'),
            ('makegood', 'Makegood'),
            ('promo', 'Promo'),
        ],
        string='Type',
    )
    locked = fields.Boolean(string='Locked')
    main_network = fields.Boolean(string='Main Network')
    snowflake_transferred = fields.Boolean(string='Snowflake Transferred')
    removed = fields.Boolean(string='Removed')

    week = fields.Date(string='Schedule Week', compute='_compute_week', store=True)
    estimated_000_primary_demo = fields.Float(string='Estimated 000 (Primary Demo)')
    actual_000_primary_demo = fields.Float(string='Actual 000 (Primary Demo)')
    total_000_primary_demo = fields.Float(string='Total 000 (Primary Demo)')

    # =================================================================== #
    # === SF parity fields (auto-generated, full Salesforce field set) === #
    # =================================================================== #
    am_pm = fields.Char(string="AM/PM")
    agency_commission = fields.Monetary(string="Agency Commission", currency_field='currency_id')
    air_date_time = fields.Char(string="Air Date/Time")
    air_date_yyyy = fields.Char(string="Air Date YYYYMMDD")
    availability = fields.Boolean(string="Availability", default=False)
    broadcast_network = fields.Char(string="Broadcast Network")
    bundle_avail_30 = fields.Float(string="Bundle Avail :30")
    bundle_spot_30 = fields.Float(string="Bundle Spot :30")
    bundle_spot_rate = fields.Monetary(string="Bundle Spot Rate", currency_field='currency_id')
    bundle = fields.Monetary(string="Bundle Avail Rate", currency_field='currency_id')
    commercial_title = fields.Char(string="Commercial Title")
    day_of_week = fields.Char(string="Day of Week")
    daypart = fields.Char(string="Daypart")
    error_mirror = fields.Text(string="Error (Mirror)")
    error = fields.Char(string="Error")
    hour = fields.Char(string="Hour")
    hour_of_day = fields.Char(string="Hour of Day")
    impressions = fields.Integer(string="Impressions")
    length = fields.Selection([('15', '15'), ('30', '30'), ('45', '45'), ('60', '60'), ('90', '90'), ('120', '120'), ('5', '5'), ('10', '10'), ('75', '75'), ('180', '180'), ('300', '300'), ('3510', '3510')], string="Length")
    line_number = fields.Char(string="Line Number")
    log_schedule_mismatch = fields.Boolean(string="Log Schedule Mismatch")
    long_form_match = fields.Boolean(string="Long Form Match")
    long_form_rate = fields.Monetary(string="Long Form Rate", currency_field='currency_id')
    long_form = fields.Char(string="Long Form")
    main_broadcast_program = fields.Char(string="Main Broadcast Program")
    net_total = fields.Monetary(string="Net Total", currency_field='currency_id')
    network_deal_number = fields.Char(string="Network Deal Number")
    prelog_data = fields.Many2one('marathon.prelog.data', string="Prelog Data", ondelete='set null')
    product = fields.Char(string="Product")
    rate_check = fields.Char(string="Rate Check")
    raycom_invoice_number = fields.Char(string="Invoice Number")
    raycom_order_account_brand = fields.Char(string="Order + Account + Brand")
    raycom_order_number = fields.Char(string="Order Number")
    sdm_created_by = fields.Char(string="SDM Created By")
    schedule_rate = fields.Monetary(string="Schedule Rate", currency_field='currency_id')
    spot_data_mirror_reference = fields.Char(string="SpotDataMirror Reference")
    spot_data_mirror = fields.Many2one('marathon.spot.data.mirror', string="SpotDataMirror", ondelete='set null')
    spot_data_ref_equal = fields.Boolean(string="SpotDataRefEqual")
    spot_data_ref = fields.Char(string="SpotDataRef")
    spot_30_rate = fields.Monetary(string="Spot :30 Rate", currency_field='currency_id')
    spot_equiv_30 = fields.Float(string="Spot Equiv :30")
    spot_rate = fields.Monetary(string="Spot Rate", currency_field='currency_id')
    spot_week = fields.Date(string="Spot Week")
    station_market_affiliate = fields.Char(string="Station Market Affiliate")
    station = fields.Many2one('marathon.station', string="Station", ondelete='set null')
    status = fields.Selection([('Aired', 'Aired'), ('Credited', 'Credited'), ('Credited - Partial', 'Credited - Partial')], string="Status")
    time_period = fields.Char(string="Time Period")
    x800 = fields.Char(string="800 #")
    # === END SF parity fields ===

    # --- Spot data credit adjustment workflow ----------------------------
    # Per SF training "spot-data-credit-adjustment-before-finance-completes-
    # invoicing": when a Network Error has been credited on the network
    # invoice, Spot Data in SF must be updated to mirror the network's
    # invoice — change Status from "Aired" to "Credited" and select
    # "Network" error reason. Partial credits cannot use this flow; an
    # SFCM is required instead.
    credit_error_reason = fields.Selection(
        [
            ('network_traffic', 'Network - Traffic Error'),
            ('network_daypart', 'Network - Daypart Error'),
            ('network_rate', 'Network - Rate Error'),
            ('network_overrun', 'Network - Overrun'),
            ('network_other', 'Network - Other'),
        ],
        string='Credit Error Reason',
        help='Per training: must include "Network" — only used when error '
             'is on the network side. Partial credits go through SFCM.',
    )
    finance_invoiced = fields.Boolean(
        string='Finance Invoiced',
        help='Once Finance has invoiced this Spot Data, status is locked '
             'and adjustments must use a SFCM.',
    )

    def action_credit_spot_data(self):
        """Update Status from Aired → Credited per SF training."""
        for r in self:
            if r.finance_invoiced:
                raise UserError(_(
                    'Finance has already invoiced this Spot Data. Use the '
                    'Salesforce Credit Memo (SFCM) flow instead.'
                ))
            if r.status != 'Aired':
                raise UserError(_(
                    'Only spots in "Aired" status can be credited via this '
                    'flow. Current status: %s'
                ) % (r.status or 'unset'))
            if not r.credit_error_reason:
                raise UserError(_(
                    'Please select a Credit Error Reason that includes '
                    '"Network" before crediting.'
                ))
            r.status = 'Credited'

    def action_revert_credit(self):
        """Undo a credit that was applied in error (only before invoicing)."""
        for r in self:
            if r.finance_invoiced:
                raise UserError(_(
                    'Cannot revert: Finance has already invoiced. Use SFCM.'
                ))
            r.write({'status': 'Aired', 'credit_error_reason': False})

    @api.depends('air_date')
    def _compute_week(self):
        from datetime import timedelta
        for s in self:
            if s.air_date:
                s.week = s.air_date - timedelta(days=s.air_date.weekday())
            else:
                s.week = False


class MarathonSpotDataMirror(models.Model):
    _name = 'marathon.spot.data.mirror'
    _description = 'Spot Data Mirror'
    _order = 'air_date desc'

    name = fields.Char(string='Name')
    spot_data_id = fields.Many2one('marathon.spot.data', string='Spot Data')
    schedule_id = fields.Many2one('marathon.schedule', string='Schedule')
    deal_id = fields.Many2one('marathon.deal', string='Deal')

    air_date = fields.Date(string='Air Date')
    air_time = fields.Char(string='Air Time')
    advertiser_product = fields.Char(string='Advertiser / Product')
    agency = fields.Char(string='Agency')
    network = fields.Char(string='Network')
    isci = fields.Char(string='ISCI')
    title = fields.Char(string='Title')
    series = fields.Char(string='Series')
    duration = fields.Char(string='Duration')
    rate = fields.Monetary(string='Rate', currency_field='currency_id')
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id,
    )
    raw_payload = fields.Text(string='Raw Payload (JSON)')
    processed = fields.Boolean(string='Processed')
    error_reason = fields.Selection(
        [
            ('agency_mismatch', 'Agency Mismatch'),
            ('rate_mismatch', 'Rate Mismatch'),
            ('no_match', 'No Schedule Match'),
            ('duplicate', 'Duplicate'),
            ('other', 'Other'),
        ],
        string='Error Reason',
    )

    # =================================================================== #
    # === SF parity fields (auto-generated, full Salesforce field set) === #
    # =================================================================== #
    air_date_time = fields.Char(string="Air Date/Time")
    air_date_yyyy = fields.Char(string="Air Date YYYYMMDD")
    air_time_hour = fields.Integer(string="Air Time Hour")
    broadcast_network = fields.Char(string="Broadcast Network")
    commercial_title = fields.Char(string="Commercial Title")
    hour_of_day = fields.Char(string="Hour of Day")
    length = fields.Selection([('15', '15'), ('30', '30'), ('45', '45'), ('60', '60'), ('90', '90'), ('120', '120'), ('5', '5'), ('10', '10'), ('75', '75'), ('180', '180'), ('300', '300'), ('3510', '3510')], string="Length")
    line_number = fields.Char(string="Line Number")
    log_schedule = fields.Char(string="Log Schedule")
    network_deal_number = fields.Char(string="Network Deal Number")
    pp = fields.Boolean(string="PP")
    product = fields.Char(string="Product")
    program_id = fields.Char(string="Program ID")
    raycom_invoice_number = fields.Char(string="[Dep]Raycom Invoice Number")
    reason_for_unmatched = fields.Char(string="Reason for Unmatched")
    schedule_week = fields.Date(string="Schedule Week")
    schedule_start_end = fields.Text(string="Schedule Start/End")
    spot_equiv_30 = fields.Float(string="Spot Equiv :30")
    spot_rate = fields.Monetary(string="Spot Rate", currency_field='currency_id')
    status = fields.Selection([('Aired', 'Aired'), ('Discrepancy', 'Discrepancy'), ('Credited', 'Credited'), ('Discrepancy - Paid', 'Discrepancy - Paid')], string="Status")
    time_period = fields.Char(string="Time Period")
    week = fields.Date(string="Week")
    x800 = fields.Char(string="800 #")
    sf_brand_text = fields.Char(string='Brand')
    sf_program_text = fields.Char(string='Program')
    # === END SF parity fields ===


class MarathonSpotDataPIJunction(models.Model):
    """``Spot_Data_PI_Junction__c`` is a junction object linking spot data
    records to per-inquiry deals (Many-to-Many bridge)."""

    _name = 'marathon.spot.data.pi.junction'
    _description = 'Spot Data PI Junction'

    spot_data_id = fields.Many2one(
        'marathon.spot.data', string='Spot Data', required=True,
        ondelete='cascade',
    )
    deal_id = fields.Many2one(
        'marathon.deal', string='PI Deal', required=True, ondelete='cascade',
    )
    notes = fields.Char(string='Notes')

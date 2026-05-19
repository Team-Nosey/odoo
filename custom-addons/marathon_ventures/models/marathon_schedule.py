# -*- coding: utf-8 -*-
"""Salesforce object: ``Schedules__c`` — a single order line on a Deal.

The SF version has 238 fields and 23 validation rules. Most of those
fields are formulas, roll-ups, and per-network filler counts. We
implement the business-meaningful subset that drives the order-entry
workflow described in the Salesforce Orders DOC files:

    Week, Rate, Units Available, Days Allowed, Cap, Max/Day,
    Start/End Time, Daypart, Test/Special/Priority, Hiatus.
"""

from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


# Cable Daypart picklist — these are industry-standard.
DAYPART_SELECTION = [
    ('em', 'EM (Early Morning)'),
    ('da', 'DA (Daytime)'),
    ('ef', 'EF (Early Fringe)'),
    ('ne', 'NE (News)'),
    ('pa', 'PA (Prime Access)'),
    ('pr', 'PR (Prime)'),
    ('ln', 'LN (Late News)'),
    ('lf', 'LF (Late Fringe)'),
    ('on', 'ON (Overnight)'),
    ('we', 'WE (Weekend)'),
    ('sd', 'Saturday Day'),
    ('su', 'Sunday Day'),
    ('ros', 'ROS (Run of Schedule)'),
]

CAP_SELECTION = [
    ('0%', '0%'),
    ('1/2 in PR and 1/2 in OV', '1/2 in PR and 1/2 in OV'),
    ('100%', '100%'),
    ('50%', '50%'),
    ('50% 2', '50% 2'),
    ('80%', '80%'),
    ('80% - In OV', '80% - In OV'),
    ('Change Daypart to 5a-9a', 'Change Daypart to 5a-9a'),
    ('Ghost', 'Ghost'),
    ('Move to DT', 'Move to DT'),
    ('Move to ON', 'Move to ON'),
    ('Uncaped', 'Uncaped'),
    ('Uncapped', 'Uncapped'),
    ('Uncapped 2', 'Uncapped 2'),
    ('enter X1', 'enter X1'),
]


class MarathonSchedule(models.Model):
    _name = 'marathon.schedule'
    _description = 'Schedule'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'deal_parent_id, week, daypart'
    _rec_name = 'display_name'

    # --------------------------------------------------------------------- #
    # Identification
    # --------------------------------------------------------------------- #
    name = fields.Char(
        string='Schedule Number', copy=False, readonly=True,
        default=lambda self: _('New'),
    )
    display_name = fields.Char(
        string='Display Name', compute='_compute_display_name', store=True,
    )

    # --------------------------------------------------------------------- #
    # Master-Detail to Deal (cascade delete)
    # --------------------------------------------------------------------- #
    deal_parent_id = fields.Many2one(
        'marathon.deal', string='Deal Parent', required=True,
        ondelete='cascade', tracking=True, index=True,
    )

    # Convenience related fields (stored for sorting / search)
    program_id = fields.Many2one(
        'marathon.program', string='Program / Network',
        related='deal_parent_id.program_id', store=True, readonly=True,
    )
    advertiser_id = fields.Many2one(
        'marathon.advertiser', string='Advertiser',
        related='deal_parent_id.advertiser_id', store=True, readonly=True,
    )
    brand_id = fields.Many2one(
        'marathon.brand', string='Brand',
        related='deal_parent_id.brand_id', store=True, readonly=True,
    )

    # --------------------------------------------------------------------- #
    # The order line itself
    # --------------------------------------------------------------------- #
    week = fields.Date(
        string='Week (W/O Monday)', required=True, tracking=True,
        help="Week the order line begins. Always a Monday.",
    )
    rate = fields.Monetary(
        string='Rate', required=True, currency_field='currency_id',
        tracking=True,
    )
    units_available = fields.Integer(
        string='Units Available', required=True, tracking=True, default=1,
    )
    daypart = fields.Selection(
        DAYPART_SELECTION, string='Cable Daypart', tracking=True,
    )
    start_time = fields.Float(
        string='Start Time', help='24-hour float, e.g. 9.0 = 9:00 AM, 18.0 = 6:00 PM',
    )
    end_time = fields.Float(string='End Time')

    # Days allowed: store as a comma-separated string (much simpler than 7
    # bools) matching the SF MultiSelect behaviour.
    days_mon = fields.Boolean(string='Monday', default=True)
    days_tue = fields.Boolean(string='Tuesday', default=True)
    days_wed = fields.Boolean(string='Wednesday', default=True)
    days_thu = fields.Boolean(string='Thursday', default=True)
    days_fri = fields.Boolean(string='Friday', default=True)
    days_sat = fields.Boolean(string='Saturday', default=True)
    days_sun = fields.Boolean(string='Sunday', default=True)
    days_allowed_summary = fields.Char(
        string='Days Allowed', compute='_compute_days_allowed_summary', store=True,
    )

    cap = fields.Selection(
        CAP_SELECTION, string='Cap', default='100%',
        help='Internal inventory management cap (not shared with agencies).',
    )
    max_per_day = fields.Integer(
        string='Max Per Day', default=0,
        help='0 = no max/day restriction.',
    )

    # --------------------------------------------------------------------- #
    # Flags
    # --------------------------------------------------------------------- #
    is_priority = fields.Boolean(string='Priority', tracking=True)
    is_special = fields.Boolean(string='Special', tracking=True)
    is_test = fields.Boolean(string='Test', tracking=True)
    is_cancelled = fields.Boolean(string='Cancelled', tracking=True)
    cancel_date = fields.Date(string='Cancel Date (LTC)')

    # Hiatus
    hiatus_start = fields.Date(string='Hiatus Start')
    hiatus_end = fields.Date(string='Hiatus End')
    hiatus_time_before = fields.Float(string='Hiatus Time Before')
    hiatus_time_after = fields.Float(string='Hiatus Time After')

    # --------------------------------------------------------------------- #
    # Currency & money
    # --------------------------------------------------------------------- #
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        related='deal_parent_id.currency_id', store=True, readonly=True,
    )
    total_dollars = fields.Monetary(
        string='Total Dollars', currency_field='currency_id',
        compute='_compute_money', store=True,
    )
    dollars_booked = fields.Monetary(
        string='Dollars Booked', currency_field='currency_id',
        compute='_compute_money', store=True,
    )

    # --------------------------------------------------------------------- #
    # Quarter (computed from week)
    # --------------------------------------------------------------------- #
    quarter = fields.Selection(
        [('q1', 'Q1'), ('q2', 'Q2'), ('q3', 'Q3'), ('q4', 'Q4')],
        string='Quarter',
        compute='_compute_quarter', store=True,
    )

    notes = fields.Text(string='Notes')

    # =================================================================== #
    # === SF parity fields (auto-generated, full Salesforce field set) === #
    # =================================================================== #
    ad_us_estimated = fields.Integer(string="ADUs - Estimated")
    ad_us_generated = fields.Float(string="ADUs - Generated")
    access_code = fields.Char(string="DealAccess Code")
    account_advertiser_program = fields.Char(string="Account Advertiser Program")
    account_advertiser = fields.Char(string="Account Advertiser")
    account_brand_program = fields.Char(string="Account Brand Program")
    actual_total_000_primary_demo = fields.Integer(string="Actual Total (000) - Primary Demo")
    additional_intacct_si_number_comments = fields.Text(string="Additional Intacct SI Number Comments")
    additional_intacct_si_number = fields.Text(string="Additional Intacct SI Number")
    advertiser_brand_program = fields.Char(string="Advertiser/Brand/Program")
    archived_prelog_booked_dollars = fields.Monetary(string="Archived Prelog Booked Dollars", currency_field='currency_id')
    archived_prelog_count = fields.Integer(string="Archived Prelog Count")
    bg_color = fields.Char(string="BG Color")
    bpu_units = fields.Integer(string="BPU Units")
    booked_digital_total_dollars = fields.Monetary(string="Booked Digital Total Dollars", currency_field='currency_id')
    booked_dollars_live_demo = fields.Monetary(string="Booked Dollars - Live Demo", currency_field='currency_id')
    booked_increvenue = fields.Monetary(string="Booked Increvenue", currency_field='currency_id')
    booking_timeline = fields.Integer(string="Booking Timeline")
    broadcast_month = fields.Date(string="Broadcast Month")
    broadcast_spot_count = fields.Float(string="Broadcast Spot Count (Sch Roll Up)")
    broadcast_spot_data_dollars_check = fields.Char(string="Broadcast Spot Data Dollars CHECK")
    broadcast_spot_data_unit_check = fields.Char(string="Broadcast Spot Data Unit CHECK")
    broadcast_spot_total = fields.Float(string="Broadcast Spot Total $")
    broadcast_total_dollars = fields.Monetary(string="Broadcast Total Dollars", currency_field='currency_id')
    broadcast_units_aired = fields.Float(string="Broadcast Units Aired")
    broadcast_units_preempted = fields.Integer(string="Broadcast Units Preempted")
    buyline_number = fields.Integer(string="Buyline Number")
    calc_equiv_30 = fields.Float(string="CALC EQUIV :30")
    cia_status = fields.Selection([('Approved', 'Approved'), ('Pending', 'Pending'), ('Denied', 'Denied')], string="CIA Status")
    cia = fields.Char(string="CIA")
    countmenot = fields.Char(string="AIRED")
    cpm = fields.Monetary(string="CPM", currency_field='currency_id')
    cable_synd_pp = fields.Char(string="Cable/Synd/PP")
    campaign_total = fields.Monetary(string="Campaign Total", currency_field='currency_id')
    capped_30_units = fields.Float(string="Capped :30 Units")
    capped_booked = fields.Integer(string="Capped Booked $$$")
    capped_dollars = fields.Float(string="Capped Dollars")
    capped_units = fields.Integer(string="Capped Units")
    clearance = fields.Float(string="Clearance")
    comments = fields.Char(string="Comments")
    contact_account_color = fields.Char(string="Contact Account Color")
    created_date_time = fields.Datetime(string="Created Date Time")
    created_week_in_quarter = fields.Float(string="Created Week in Quarter")
    day = fields.Date(string="Day")
    day_of_air_check = fields.Boolean(string="Day of Air Check")
    day_of_week = fields.Char(string="Day of Week")
    days_allowed_formula = fields.Char(string="Days Allowed Formula")
    days_allowed = fields.Char(string="Days Allowed (SF)")
    days_of_air = fields.Char(string="Days of Air")
    deal_account = fields.Char(string="DealAccount")
    deal_advertiser = fields.Char(string="DealAdvertiser")
    deal_brand = fields.Char(string="DealBrand")
    deal_client_code = fields.Char(string="DealClientCode")
    deal_contact_id = fields.Char(string="DealContactID")
    deal_contact = fields.Char(string="DealContact")
    deal_estimate = fields.Char(string="DealEstimate")
    deal_name = fields.Char(string="DealName")
    deal_program_id = fields.Char(string="Deal Program Id")
    deal_program = fields.Char(string="DealProgram")
    demo_30_rate = fields.Monetary(string=":30 Rate - Live Demo", currency_field='currency_id')
    demo_program = fields.Char(string="Program - Live Demo")
    demo_rate = fields.Float(string="Rate - Live Demo")
    digital_total_dollars = fields.Monetary(string="Digital Total Dollars", currency_field='currency_id')
    discrepancy_bundle = fields.Boolean(string="Discrepancy Bundle", default=False)
    discrepancy_report_url = fields.Char(string="Discrepancy Report URL")
    discrepancy_total_amount = fields.Float(string="Discrepancy Total Amount")
    dollars_canceled = fields.Monetary(string="Canceled Dollars", currency_field='currency_id')
    dollars_cap = fields.Monetary(string="Dollars Cap", currency_field='currency_id')
    due_date = fields.Date(string="Due Date")
    duplicate_check_1a = fields.Char(string="Duplicate Check 1a")
    duplicate_check_digital = fields.Char(string="Duplicate Check Digital")
    duplicate_check = fields.Char(string="Duplicate Check")
    eur_filler_decile = fields.Float(string="EUR Filler Decile")
    equiv_30_booked = fields.Float(string="Equiv :30 - Booked")
    equiv_30_canceled = fields.Float(string="Equiv :30 - Canceled")
    equiv_30 = fields.Float(string="Equiv :30")
    error_reason = fields.Char(string="Error Reason")
    estimated_total_000_primary_demo = fields.Integer(string="Estimated Total (000) - Primary Demo")
    filler_rate = fields.Integer(string="Filler Rate")
    filler_test = fields.Integer(string="Filler Test")
    filler = fields.Boolean(string="[Dep]Filler", default=False)
    ghost_order = fields.Boolean(string="[Dep]Ghost Order", default=False)
    guaranteed_000_primary_demo = fields.Float(string="Guaranteed (000) - Primary Demo")
    guaranteed_total_000_primary_demo = fields.Float(string="Guaranteed Total (000) - Primary Demo")
    hh_000 = fields.Integer(string="HH (000)")
    half_units_round_up = fields.Integer(string="Half Units Round Up")
    isci2 = fields.Char(string="ISCI 2")
    isci3 = fields.Char(string="ISCI 3")
    isci_code = fields.Char(string="ISCI CODE")
    impressions_000 = fields.Integer(string="Impressions (000)")
    impressions_aired = fields.Float(string="Impressions Aired")
    impressions = fields.Integer(string="Impressions")
    increvenue = fields.Monetary(string="Increvenue", currency_field='currency_id')
    incumbency = fields.Boolean(string="Incumbency", default=False)
    intacct_cm_number = fields.Char(string="Intacct CM Number")
    intacct_si_number_date_fully_paid = fields.Char(string="Intacct SI Number Date Fully Paid")
    intacct_si_number_payment_status = fields.Char(string="Intacct SI Number Payment Status")
    intacct_si_number = fields.Char(string="Intacct SI Number")
    intg_date = fields.Date(string="Intg Date")
    invoice_date = fields.Char(string="Invoice Date")
    lf_order_line_number = fields.Char(string="LF Order Line Number")
    lf_brand = fields.Many2one('marathon.brand', string="[Dep]LF Brand", ondelete='set null')
    lf_daypart = fields.Char(string="LF Daypart")
    lf_rate_needed = fields.Monetary(string="[Dep]LF Rate Needed", currency_field='currency_id')
    lf_unique_key = fields.Char(string="LF Unique Key")
    lf_week = fields.Date(string="LF Week")
    lf_traffic = fields.Char(string="LF Traffic")
    last_modified_time = fields.Datetime(string="Last Modified Time")
    liability_000 = fields.Integer(string="Liability (000)")
    liability = fields.Monetary(string="Liability ($$$)", currency_field='currency_id')
    locked_units = fields.Float(string="Locked Units")
    long_form = fields.Selection([('A-12:00', 'A-12:00'), ('A-12:30', 'A-12:30'), ('A-1:00', 'A-1:00'), ('A-1:30', 'A-1:30'), ('A-2:00', 'A-2:00'), ('A-2:30', 'A-2:30'), ('A-3:00', 'A-3:00'), ('A-3:30', 'A-3:30'), ('A-4:00', 'A-4:00'), ('A-4:30', 'A-4:30'), ('A-5:00', 'A-5:00'), ('A-5:30', 'A-5:30'), ('A-6:00', 'A-6:00'), ('A-6:30', 'A-6:30'), ('A-7:00', 'A-7:00'), ('A-7:30', 'A-7:30'), ('A-8:00', 'A-8:00'), ('A-8:30', 'A-8:30'), ('A-9:00', 'A-9:00'), ('A-9:30', 'A-9:30'), ('A-10:00', 'A-10:00'), ('A-10:30', 'A-10:30'), ('A-11:00', 'A-11:00'), ('A-11:30', 'A-11:30'), ('P-12:00', 'P-12:00'), ('P-12:30', 'P-12:30'), ('P-1:00', 'P-1:00'), ('P-1:30', 'P-1:30'), ('P-2:00', 'P-2:00'), ('P-2:30', 'P-2:30'), ('P-3:00', 'P-3:00'), ('P-3:30', 'P-3:30'), ('P-4:00', 'P-4:00'), ('P-4:30', 'P-4:30'), ('P-5:00', 'P-5:00'), ('P-5:30', 'P-5:30')], string="Long Form")
    mgm_hd_daypart = fields.Selection([('EM - MS 4a-9a', 'EM - MS 4a-9a'), ('EM - MS 6a-10a', 'EM - MS 6a-10a'), ('EM - MS 6a-9a', 'EM - MS 6a-9a'), ('EM - MS 5a-9a', 'EM - MS 5a-9a'), ('EM - MS 5a-10a', 'EM - MS 5a-10a'), ('EM - MS 8a-12p', 'EM - MS 8a-12p'), ('DA - MS 8a-6p', 'DA - MS 8a-6p'), ('DA - MS 8a-8p', 'DA - MS 8a-8p'), ('EM - MF 6a-9a', 'EM - MF 6a-9a'), ('MF 12a-5a', 'MF 12a-5a'), ('DA - MF 9a-1p', 'DA - MF 9a-1p'), ('EM - SS 6a-9a', 'EM - SS 6a-9a'), ('FR - MF 1p-7p', 'FR - MF 1p-7p'), ('DA - SS 9a-7p', 'DA - SS 9a-7p'), ('DA  - MS - 9a-4p', 'DA  - MS - 9a-4p'), ('MF 6a-9a', 'MF 6a-9a'), ('MF 6a-6p', 'MF 6a-6p'), ('MF 6p-12a', 'MF 6p-12a'), ('SS 12a-5a', 'SS 12a-5a'), ('SS 6a-9a', 'SS 6a-9a'), ('SS 6a-6p', 'SS 6a-6p'), ('SS 6p-12a', 'SS 6p-12a'), ('MS 6a-6p', 'MS 6a-6p'), ('DA - MF 10a-3p', 'DA - MF 10a-3p'), ('EF - MF 3p-7p', 'EF - MF 3p-7p'), ('DA - MS 9a-5p', 'DA - MS 9a-5p'), ('DA - MS 6a-7p', 'DA - MS 6a-7p'), ('SS 9a-4p', 'SS 9a-4p'), ('DA - MF 9a-6p', 'DA - MF 9a-6p'), ('DA - MS 10a-5p', 'DA - MS 10a-5p'), ('FR - MF 1p-6p', 'FR - MF 1p-6p'), ('DA - SS 9a-6p', 'DA - SS 9a-6p'), ('DA - MF 9a-2p', 'DA - MF 9a-2p'), ('DA - MS 9a-7p', 'DA - MS 9a-7p'), ('DA - MS 10a-4p', 'DA - MS 10a-4p'), ('DA - MS 9a-6p', 'DA - MS 9a-6p'), ('DA - MS 12p-6p', 'DA - MS 12p-6p'), ('PR - MS 6p-12a', 'PR - MS 6p-12a'), ('MS 12a-6a', 'MS 12a-6a'), ('PR - MS 6p-1a', 'PR - MS 6p-1a'), ('5:00a-5:30a', '5:00a-5:30a'), ('5:30a-6:00a', '5:30a-6:00a'), ('6A-9A – EM', '6A-9A – EM'), ('9A-6P – Day', '9A-6P – Day'), ('6P-12A – PR', '6P-12A – PR'), ('FR - MF 2p-7p', 'FR - MF 2p-7p'), ('12A-3A -- LN', '12A-3A -- LN'), ('3A-6A -- ON', '3A-6A -- ON'), ('DA - MS 6A-4P', 'DA - MS 6A-4P'), ('DA - SS 6A-7P', 'DA - SS 6A-7P'), ('EF - MF 1p-7p', 'EF - MF 1p-7p'), ('EF - MS 5p-8p', 'EF - MS 5p-8p'), ('EF - MS 4p-7p', 'EF - MS 4p-7p'), ('PR - MS 7P-3A', 'PR - MS 7P-3A'), ('PR - MF 7p-1a', 'PR - MF 7p-1a'), ('PR - SS 7p-1a', 'PR - SS 7p-1a'), ('MF 8a-3p', 'MF 8a-3p'), ('MF 3p-7p', 'MF 3p-7p'), ('MS 7p-12a', 'MS 7p-12a'), ('MS 12a-4a', 'MS 12a-4a'), ('SS 8a-7p', 'SS 8a-7p'), ('MS 6a-11a', 'MS 6a-11a'), ('MS 3p-5p', 'MS 3p-5p'), ('MS 7p-10p', 'MS 7p-10p'), ('MF 7a-10a', 'MF 7a-10a'), ('MF 10a-4p', 'MF 10a-4p'), ('MF 4p-6p', 'MF 4p-6p'), ('MS 7p-11p', 'MS 7p-11p'), ('MF 12a-2a', 'MF 12a-2a'), ('SS 11a-6p', 'SS 11a-6p'), ('MS 2a-5a', 'MS 2a-5a'), ('MS 6a-12p', 'MS 6a-12p'), ('MS 12p-6p', 'MS 12p-6p'), ('MS 11a-6p', 'MS 11a-6p'), ('SS 6a-11a', 'SS 6a-11a'), ('SS 12a-6a', 'SS 12a-6a'), ('PR - MS 8p-12a', 'PR - MS 8p-12a'), ('PR - MS 7p-12a', 'PR - MS 7p-12a'), ('LN - MS 12a-3a', 'LN - MS 12a-3a'), ('MS 8p-2a', 'MS 8p-2a'), ('MS 12a-2a', 'MS 12a-2a'), ('MS 2a-6a', 'MS 2a-6a'), ('MS 1p-6p', 'MS 1p-6p'), ('MF 5a-9a', 'MF 5a-9a'), ('MF 9a-5p', 'MF 9a-5p'), ('MF 5p-7p', 'MF 5p-7p'), ('MF 7p-8:30p', 'MF 7p-8:30p'), ('MF 8:30p-10p', 'MF 8:30p-10p'), ('MF 10p-1a', 'MF 10p-1a'), ('MF 1a-5a', 'MF 1a-5a'), ('SS 6a-6a', 'SS 6a-6a'), ('ON - MS 12a-9a', 'ON - MS 12a-9a'), ('PR - MS 5p-12a', 'PR - MS 5p-12a'), ('ON - MS 12a-5a', 'ON - MS 12a-5a'), ('ON - MS 12a-4a', 'ON - MS 12a-4a'), ('ON - MS 12a-6a', 'ON - MS 12a-6a'), ('JC - MS 7p-12a', 'JC - MS 7p-12a'), ('JC - MS 12a-5a', 'JC - MS 12a-5a'), ('EM - MF 6a-1p', 'EM - MF 6a-1p'), ('DA - MF 1p-6p', 'DA - MF 1p-6p'), ('PR - MS 6p-2a', 'PR - MS 6p-2a'), ('PR - MF 7p-11p', 'PR - MF 7p-11p'), ('PR - SS 7p-10p', 'PR - SS 7p-10p'), ('ON - MF 12a-2a', 'ON - MF 12a-2a'), ('ON - MF 3a-5a', 'ON - MF 3a-5a'), ('ON - SS 12a-1:30a', 'ON - SS 12a-1:30a'), ('ON - SS 3a-5a', 'ON - SS 3a-5a'), ('JC - MF 11p-12a', 'JC - MF 11p-12a'), ('LF - MS 1a-3a', 'LF - MS 1a-3a'), ('JC - MF 2a-3a', 'JC - MF 2a-3a'), ('JC - SS 10p-12a', 'JC - SS 10p-12a'), ('JC - SS 1:30a-3a', 'JC - SS 1:30a-3a'), ('EM - SS 6a-1p', 'EM - SS 6a-1p'), ('EF - MF 1p-5p', 'EF - MF 1p-5p'), ('EF - SS 1p-5p', 'EF - SS 1p-5p'), ('LF - MF 5p-8p', 'LF - MF 5p-8p'), ('LF - SS 5p-8p', 'LF - SS 5p-8p'), ('PR - MF 8p-12a', 'PR - MF 8p-12a'), ('PR - SS 8p-12a', 'PR - SS 8p-12a'), ('WC - MS 12a-2a', 'WC - MS 12a-2a'), ('LN - MS 2a-6a', 'LN - MS 2a-6a'), ('PR - MF 7p-2a', 'PR - MF 7p-2a'), ('PR - SS 7p-2a', 'PR - SS 7p-2a'), ('Matinee Game MS', 'Matinee Game MS'), ('Prime Game MS', 'Prime Game MS'), ('EM - MS 5a-8a', 'EM - MS 5a-8a'), ('EM - MS 6a-12p', 'EM - MS 6a-12p'), ('DA - MF 12p-4p', 'DA - MF 12p-4p'), ('EF - MF 4P-7P', 'EF - MF 4P-7P'), ('DA - SS 12p-7p', 'DA - SS 12p-7p'), ('EM - MF 6a-12p', 'EM - MF 6a-12p'), ('EM - SS 6a-12p', 'EM - SS 6a-12p'), ('PR - MS 7p-11p', 'PR - MS 7p-11p'), ('LF - MS 11p-1a', 'LF - MS 11p-1a'), ('ON - MS 1a-4a', 'ON - MS 1a-4a'), ('DT - MF ROS 7a-4p', 'DT - MF ROS 7a-4p'), ('PT - MF ROS 4p-11:30p', 'PT - MF ROS 4p-11:30p'), ('LN - MF ROS 11:30p-5a', 'LN - MF ROS 11:30p-5a'), ('DT - SS ROS 7a-5p', 'DT - SS ROS 7a-5p'), ('PT - SS ROS 5p-11:30p', 'PT - SS ROS 5p-11:30p'), ('LN - SS ROS 11:30p-5a', 'LN - SS ROS 11:30p-5a'), ('DA - MF 9a - 6p', 'DA - MF 9a - 6p'), ('SS 9a - 6p', 'SS 9a - 6p'), ('ON - MS 2a-6a', 'ON - MS 2a-6a'), ('EM - MF 6a-10a', 'EM - MF 6a-10a'), ('LN - MF 11p-2a', 'LN - MF 11p-2a'), ('DA - SS 6a-2a', 'DA - SS 6a-2a'), ('EM - MF 7a-10a', 'EM - MF 7a-10a'), ('WKND - 2p-7p', 'WKND - 2p-7p'), ('DA - MS 10a-6p', 'DA - MS 10a-6p'), ('PR - MS 6p-11p', 'PR - MS 6p-11p'), ('DY - MF 10a-3p', 'DY - MF 10a-3p'), ('Dr Phil Primetime MF 8p-9p', 'Dr Phil Primetime MF 8p-9p'), ('PT - MS 7p-11p', 'PT - MS 7p-11p'), ('LT - MS 11p-12a', 'LT - MS 11p-12a'), ('WD - SS 10a-7p', 'WD - SS 10a-7p'), ('OV - MS 12a-6a', 'OV - MS 12a-6a'), ('LF - MS 11p-12a', 'LF - MS 11p-12a'), ('DA - MF 9a-7p', 'DA - MF 9a-7p'), ('PR - MS 7p-2a', 'PR - MS 7p-2a'), ('OV - MS 2a-6a', 'OV - MS 2a-6a'), ('W - SS 10a-7p', 'W - SS 10a-7p'), ('PR - MS 7p-1a', 'PR - MS 7p-1a'), ('LN - MS 1a-3a', 'LN - MS 1a-3a'), ('WK - SS 10a-7p', 'WK - SS 10a-7p'), ('LN - MS 1a-2a', 'LN - MS 1a-2a'), ('ROS-', 'ROS-'), ('ROS - MS 6a-6a', 'ROS - MS 6a-6a'), ('ON - MS 3a-6a', 'ON - MS 3a-6a'), ('NWSL Live Games', 'NWSL Live Games'), ('WNBA Live Games', 'WNBA Live Games'), ('ROS - NWSL', 'ROS - NWSL'), ('ROS - WNBA', 'ROS - WNBA'), ('STUDIO - NWSL', 'STUDIO - NWSL'), ('STUDIO - WNBA', 'STUDIO - WNBA'), ('NWSL 7p - 12a', 'NWSL 7p - 12a'), ('WNBA 7p - 1a', 'WNBA 7p - 1a'), ('NWSL 7p-1a', 'NWSL 7p-1a'), ('Daytime Live Game MF 12p-7p', 'Daytime Live Game MF 12p-7p'), ('Prime Live Game MS 7p-2a', 'Prime Live Game MS 7p-2a'), ('Weekend Live Game SS', 'Weekend Live Game SS')], string="Cable Dayparts")
    max_allowable_units_per_day = fields.Integer(string="Max Allowable Units by Max Per Day")
    military_time = fields.Float(string="Military Time")
    missing_traffic_current_url = fields.Char(string="Missing Traffic Current URL")
    month = fields.Integer(string="Month")
    net_suite_invoice_number = fields.Char(string="NetSuite Invoice Number")
    net_suite_invoice_url = fields.Char(string="NetSuite Invoice URL")
    net_total = fields.Monetary(string="Net Total", currency_field='currency_id')
    network_deal_number = fields.Char(string="Network Deal Number")
    networks = fields.Selection([('AccuWeather', 'AccuWeather'), ('Accuweather Local', 'Accuweather Local'), ('beIN XTRA', 'beIN XTRA'), ('beIN XTRA Espanol', 'beIN XTRA Espanol'), ('Bounce', 'Bounce'), ('BounceTV - Local', 'BounceTV - Local'), ('BUSTED', 'BUSTED'), ('CATV', 'CATV'), ('CATV - Local', 'CATV - Local'), ('CBS Sports', 'CBS Sports'), ('CBS Sports Local', 'CBS Sports Local'), ('CineLatino', 'CineLatino'), ('CineLatino - Local', 'CineLatino - Local'), ('Confess', 'Confess'), ('CourtTV', 'CourtTV'), ('DEFY', 'DEFY'), ('Defy FTV', 'Defy FTV'), ('DIGITV', 'DIGITV'), ('GritTV', 'GritTV'), ('ION Local', 'ION Local'), ('ION Mystery', 'ION Mystery'), ('ION Plus', 'ION Plus'), ('ION Political Cover', 'ION Political Cover'), ('ION Television', 'ION Television'), ('Laff', 'Laff'), ('Marquee MilB', 'Marquee MilB'), ('Merit Street Media', 'Merit Street Media'), ('MLB', 'MLB'), ('MLB Network AppleTV+', 'MLB Network AppleTV+'), ('NHL Network', 'NHL Network'), ('NHL Network - Local', 'NHL Network - Local'), ('NoseyTV', 'NoseyTV'), ('Novelisima', 'Novelisima'), ('Outlaw', 'Outlaw'), ('Pasiones', 'Pasiones'), ('Pasiones - Local', 'Pasiones - Local'), ('Quest Network', 'Quest Network'), ('Scripps News', 'Scripps News'), ('Stadium MilB', 'Stadium MilB'), ('THE365', 'THE365'), ('True Crime Network', 'True Crime Network'), ('True Real', 'True Real'), ('TV Azteca', 'TV Azteca'), ('TV Azteca - Subnetwork', 'TV Azteca - Subnetwork'), ('TVD', 'TVD'), ('TVD - Local', 'TVD - Local'), ('TWIST', 'TWIST'), ('WAPA America', 'WAPA America'), ('WAPA America - Local', 'WAPA America - Local'), ('WAPA Puerto Rico', 'WAPA Puerto Rico')], string="Networks")
    new_filler = fields.Boolean(string="New Filler")
    new_week_in_quarter = fields.Integer(string="New Week in Quarter")
    order_line_number = fields.Char(string="Order Line Number")
    order_number = fields.Char(string="OrderNumber")
    orderline_mpd = fields.Char(string="OrderlineMPD")
    orderline_number_mpd = fields.Char(string="Orderline Number + MPD")
    original_rate = fields.Monetary(string="Original Rate", currency_field='currency_id')
    original_units_preempted = fields.Integer(string="Original_Units_Preempted")
    overran_units_dynamic = fields.Integer(string="Overran Units Dynamic")
    overran_units_v2 = fields.Integer(string="Overran Units V2")
    overran_units_v3 = fields.Integer(string="Overran Units V3")
    overran_units_v4 = fields.Integer(string="Overran Units V4")
    overran_units_v5 = fields.Integer(string="Overran Units V5")
    overran_units_v6 = fields.Integer(string="Overran Units V6")
    overran_units_v1 = fields.Integer(string="Overran Units V1")
    pi_payout_test = fields.Float(string="PI Payout TEST")
    pi_payout = fields.Monetary(string="PI Payout", currency_field='currency_id')
    pi = fields.Char(string="PI")
    pp_revision_comment = fields.Selection([('ADDED', 'ADDED'), ('RATE CHANGE', 'RATE CHANGE'), ('CANCELED', 'CANCELED'), ('PRE-EMPTED', 'PRE-EMPTED'), ('CREDIT', 'CREDIT'), ('PARTIAL CREDIT', 'PARTIAL CREDIT')], string="PP Revision Comment")
    pp_revision = fields.Integer(string="PP Revision")
    performance_dollars = fields.Monetary(string="Performance Dollars", currency_field='currency_id')
    performance = fields.Float(string="Performance %")
    pod_check = fields.Boolean(string="Pod Check")
    pod = fields.Char(string="Pod")
    preempted_and_sent_to_network = fields.Boolean(string="Preempted and Sent To Network", default=False)
    prelog_count_dynamic = fields.Integer(string="Prelog Count Dynamic")
    prelog_count_version_1 = fields.Float(string="Prelog Count Version 1")
    prelog_count_version_2 = fields.Float(string="Prelog Count Version 2")
    prelog_count_version_3 = fields.Float(string="Prelog Count Version 3")
    prelog_count_version_4 = fields.Float(string="Prelog Count Version 4")
    prelog_count_version_5 = fields.Float(string="Prelog Count Version 5")
    prelog_count_version_6 = fields.Float(string="Prelog Count Version 6")
    prelog_count = fields.Float(string="Prelog Count")
    primary_demographic_cpm = fields.Monetary(string="Primary Demographic CPM", currency_field='currency_id')
    priority_rank = fields.Selection([('1', '1'), ('2', '2'), ('100', '100'), ('0', '0')], string="Priority Rank")
    priority_weight_multiplier = fields.Float(string="Priority Weight Multiplier")
    product = fields.Many2one('res.partner', string="Program Product", ondelete='set null')
    program_specific = fields.Selection([('A Taste of Tuscany', 'A Taste of Tuscany'), ('Centuries Collide', 'Centuries Collide'), ('Crime Stories With Nancy Grace', 'Crime Stories With Nancy Grace'), ('Dr. Phil Primetime', 'Dr. Phil Primetime'), ('Dr. Phil True Crime', 'Dr. Phil True Crime'), ('Dr. Phil Wake Up', 'Dr. Phil Wake Up'), ('Happily Ever Emma', 'Happily Ever Emma'), ('Morning On Merit Street', 'Morning On Merit Street'), ('PBR Camping World Team Series', 'PBR Camping World Team Series'), ('PBR Now', 'PBR Now'), ('Scents and Sensibility', 'Scents and Sensibility'), ('Small Town Big Deal', 'Small Town Big Deal'), ("Somebody's Gotta Do It With Mike Rowe", "Somebody's Gotta Do It With Mike Rowe"), ('Steve', 'Steve'), ('Swing Into Romance', 'Swing Into Romance'), ('TCL Boxing', 'TCL Boxing'), ('The Island With Bear Grylls', 'The Island With Bear Grylls'), ('The News On Merit Street', 'The News On Merit Street'), ('The Scott Rasmussen Show', 'The Scott Rasmussen Show')], string="Program Specific")
    quarter_change = fields.Char(string="Quarter Change")
    rating_check = fields.Boolean(string="Rating Check")
    ratings_recieved = fields.Boolean(string="Ratings Recieved")
    ratings = fields.Many2one('res.partner', string="Ratings", ondelete='set null')
    recommended = fields.Boolean(string="[Dep]Recommended", default=False)
    reconciled = fields.Char(string="Reconciled")
    related_schedule = fields.Many2one('marathon.schedule', string="Related Schedule", ondelete='set null')
    request_missing_traffic_url = fields.Char(string="Request Missing Traffic URL")
    revision_comments = fields.Char(string="Revision Comments")
    send_as_new = fields.Boolean(string="[Dep]Send as NEW", default=False)
    spot_count = fields.Float(string="Spot Count (Sch Roll Up)")
    spot_data_dollars_check = fields.Char(string="Spot Data Dollars CHECK")
    spot_data_unit_check = fields.Char(string="Spot Data Unit CHECK")
    spot_total = fields.Float(string="Spot Total $")
    start_end_time = fields.Char(string="Start End Time")
    status = fields.Selection([('Sold', 'Sold'), ('Canceled', 'Canceled'), ('Sold - Unflighted', 'Sold - Unflighted')], string="Status")
    sum_spot_equiv_30 = fields.Float(string="Sum of Spot Equiv 30")
    sum_of_check_payments = fields.Float(string="Sum of Check Payments")
    total_000_primary_demo = fields.Integer(string="Total (000) - Primary Demo")
    total_dollars_earned = fields.Monetary(string="Total Dollars - Earned", currency_field='currency_id')
    total_dollars_live_demo = fields.Monetary(string="Total Dollars - Live Demo", currency_field='currency_id')
    total_historical_dollars = fields.Monetary(string="Total Historical Dollars", currency_field='currency_id')
    total_schedules = fields.Selection([('0', '0'), ('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5'), ('6', '6'), ('7', '7'), ('8', '8'), ('9', '9'), ('10', '10'), ('11', '11'), ('12', '12'), ('13', '13')], string="Additional Schedules")
    total_time = fields.Integer(string="Total Time")
    traffic_contact = fields.Char(string="Traffic Contact")
    traffic_days_allowed = fields.Char(string="Traffic Days Allowed")
    traffic = fields.Many2one('res.partner', string="Traffic", ondelete='set null')
    uncalculated_check_details = fields.Boolean(string="Uncalculated Check Details", default=False)
    uneq_total_000_primary_demo = fields.Integer(string="Uneq Total (000) - Primary Demo")
    unit_length = fields.Integer(string="UnitLength")
    unit_sep_check = fields.Boolean(string="Unit Sep Check")
    units_aired = fields.Float(string="Units Aired")
    units_cap = fields.Integer(string="Units Cap")
    units_preempted = fields.Float(string="Units Preempted")
    units_remaining = fields.Integer(string="Units Remaining")
    units_by_separation = fields.Float(string="Max Units With Valid Separation")
    video_file = fields.Many2one('marathon.video.file', string="Video File", ondelete='set null')
    wo_30_units = fields.Float(string="WO :30 Units")
    wo_booked = fields.Monetary(string="WO Booked $$$", currency_field='currency_id')
    wo_dollars = fields.Monetary(string="WO Dollars", currency_field='currency_id')
    wo_units = fields.Integer(string="WO Units")
    week_number = fields.Integer(string="Week Number")
    week_in_month = fields.Integer(string="Week in Month")
    week_in_quarter = fields.Integer(string="Week in Quarter")
    week_in_year = fields.Integer(string="Week in Year")
    weighted_30_rate = fields.Monetary(string="Weighted :30 Rate", currency_field='currency_id')
    weighted_priority = fields.Selection([('Priority 1', 'Priority 1'), ('Priority 2', 'Priority 2'), ('Priority 3', 'Priority 3'), ('Priority 4', 'Priority 4'), ('Priority 5', 'Priority 5'), ('Priority 6', 'Priority 6'), ('Low', 'Low'), ('Medium', 'Medium'), ('High', 'High'), ('Must Clear', 'Must Clear'), (':120 Must Clear (Bonus)', ':120 Must Clear (Bonus)'), (':60 Must Clear (Bonus)', ':60 Must Clear (Bonus)'), (':30 Must Clear (Bonus)', ':30 Must Clear (Bonus)'), (':15 Must Clear (Bonus)', ':15 Must Clear (Bonus)')], string="Weighted Priority")
    weighted_rate = fields.Monetary(string="Weighted Rate", currency_field='currency_id')
    working_log_count = fields.Float(string="Working Log Count")
    working_log_double_check = fields.Boolean(string="Working Log Double Check")
    working_log_version = fields.Float(string="Working Log Version")
    x120s = fields.Integer(string=":120s")
    x15s = fields.Integer(string=":15s")
    x2_calculated_time_period = fields.Char(string="LF Time Period - Full")
    x30_rate_round = fields.Monetary(string=":30 Rate Round", currency_field='currency_id')
    x30_rate = fields.Monetary(string=":30 Rate", currency_field='currency_id')
    x30s = fields.Integer(string=":30s")
    x800_number = fields.Char(string="800 Number")
    xml_sent = fields.Boolean(string="XML Sent", default=False)
    year = fields.Integer(string="Year")
    temp_working_log_check = fields.Float(string="temp working log check")
    priority = fields.Boolean(string='Priority (SF)', default=False)
    special = fields.Selection([('In-Game', 'In-Game'), ('Tonight-Live', 'Tonight-Live'), ('Big Inning', 'Big Inning')], string='Special (SF)')
    sf_test = fields.Boolean(string='TEST', default=False)
    # === END SF parity fields ===

    # --------------------------------------------------------------------- #
    # Computed methods
    # --------------------------------------------------------------------- #
    @api.depends('rate', 'units_available', 'cap', 'is_cancelled')
    def _compute_money(self):
        for s in self:
            if s.is_cancelled:
                s.total_dollars = 0.0
                s.dollars_booked = 0.0
                continue
            s.total_dollars = (s.rate or 0.0) * (s.units_available or 0)
            # cap may be a SF-style picklist value like '100%', '50%', '0%',
            # 'Uncapped', 'Ghost' etc. Parse the numeric part if present;
            # treat non-numeric or "Uncapped" as 100% and 'Ghost'/'enter X1' as 0.
            cap_raw = (s.cap or '100%').strip()
            cap_lower = cap_raw.lower()
            if cap_lower.startswith('uncap'):
                cap_pct = 1.0
            elif cap_lower in ('ghost', 'enter x1'):
                cap_pct = 0.0
            else:
                # Take the leading numeric part, ignoring '%' and trailing text
                import re as _re
                m = _re.match(r'\s*(\d+(?:\.\d+)?)', cap_raw)
                cap_pct = (float(m.group(1)) / 100.0) if m else 1.0
            s.dollars_booked = s.total_dollars * cap_pct

    @api.depends('week')
    def _compute_quarter(self):
        for s in self:
            if not s.week:
                s.quarter = False
                continue
            m = s.week.month
            if m <= 3:
                s.quarter = 'q1'
            elif m <= 6:
                s.quarter = 'q2'
            elif m <= 9:
                s.quarter = 'q3'
            else:
                s.quarter = 'q4'

    @api.depends('days_mon', 'days_tue', 'days_wed', 'days_thu',
                 'days_fri', 'days_sat', 'days_sun')
    def _compute_days_allowed_summary(self):
        for s in self:
            d = []
            if s.days_mon:
                d.append('M')
            if s.days_tue:
                d.append('Tu')
            if s.days_wed:
                d.append('W')
            if s.days_thu:
                d.append('Th')
            if s.days_fri:
                d.append('F')
            if s.days_sat:
                d.append('Sa')
            if s.days_sun:
                d.append('Su')
            s.days_allowed_summary = '/'.join(d) if d else 'None'

    @api.depends('week', 'daypart', 'rate', 'units_available')
    def _compute_display_name(self):
        for s in self:
            s.display_name = '%s %s @ $%s x %s' % (
                s.week and s.week.strftime('%m/%d') or 'TBD',
                dict(DAYPART_SELECTION).get(s.daypart, ''),
                s.rate or 0,
                s.units_available or 0,
            )

    # --------------------------------------------------------------------- #
    # Validation
    # --------------------------------------------------------------------- #
    @api.constrains('week')
    def _check_week_is_monday(self):
        for s in self:
            if s.week and s.week.weekday() != 0:
                raise ValidationError(_(
                    "Week must always start on a Monday "
                    "(received %s, which is a %s).",
                    s.week,
                    s.week.strftime('%A'),
                ))

    @api.constrains('start_time', 'end_time')
    def _check_times(self):
        for s in self:
            if s.start_time and (s.start_time < 0 or s.start_time >= 24):
                raise ValidationError(_(
                    "Start Time must be between 0 and 24 (got %s).", s.start_time
                ))
            if s.end_time and (s.end_time < 0 or s.end_time > 24):
                raise ValidationError(_(
                    "End Time must be between 0 and 24 (got %s).", s.end_time
                ))

    @api.constrains('rate', 'units_available')
    def _check_positive(self):
        for s in self:
            if s.rate is not None and s.rate < 0:
                raise ValidationError(_("Rate cannot be negative."))
            if s.units_available is not None and s.units_available < 0:
                raise ValidationError(_("Units Available cannot be negative."))

    # --------------------------------------------------------------------- #
    # CRUD
    # --------------------------------------------------------------------- #
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'marathon.schedule'
                ) or _('New')
        return super().create(vals_list)

    # --------------------------------------------------------------------- #
    # Helper: clone schedule for additional weeks (the "Save & New" /
    # "Additional Schedules" pattern from the SF flow doc).
    # --------------------------------------------------------------------- #
    def action_create_additional_schedules(self):
        """Open a wizard to clone this schedule N times for upcoming weeks."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Add Additional Schedules'),
            'res_model': 'marathon.schedule.bulk.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_template_schedule_id': self.id,
                'default_deal_id': self.deal_parent_id.id,
            },
        }

    def action_cancel_schedule(self):
        for s in self:
            s.is_cancelled = True
            s.cancel_date = fields.Date.today()
            s.message_post(body=_("Schedule cancelled (LTC=%s).", s.cancel_date))

    def action_uncancel_schedule(self):
        for s in self:
            s.is_cancelled = False
            s.cancel_date = False
            s.message_post(body=_("Schedule un-cancelled."))

    # --------------------------------------------------------------------- #
    # Helpers used by the Deal Revisions wizard
    # --------------------------------------------------------------------- #
    def _is_in_or_after(self, monday):
        self.ensure_one()
        return self.week and monday and self.week >= monday

    def _within_range(self, start, end):
        self.ensure_one()
        if not (start and end):
            return False
        return self.week and start <= self.week <= end

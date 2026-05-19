# -*- coding: utf-8 -*-
"""Salesforce object: ``Programs__c`` — represents a TV Network in Marathon's domain."""

from odoo import api, fields, models


class MarathonProgram(models.Model):
    _name = 'marathon.program'
    _description = 'Program / TV Network'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Program Name', required=True, tracking=True)
    program_number = fields.Char(
        string='Program Number', copy=False, readonly=True,
        help='Auto-generated identifier (was AutoNumber in Salesforce).',
    )
    client_code = fields.Char(string='Client Code', required=True, tracking=True)
    digital_id = fields.Char(string='Digital ID')
    station_call_letter = fields.Char(string='Station Call Letter')

    # Sales / Operations team
    lead_id = fields.Many2one('res.users', string='Lead', tracking=True)
    lead_backup_id = fields.Many2one('res.users', string='Lead Backup')
    assistant_id = fields.Many2one('res.users', string='Assistant')
    assistant_backup_id = fields.Many2one('res.users', string='Assistant Backup')
    account_exec_1_id = fields.Many2one('res.users', string='Account Exec 1')
    account_exec_2_id = fields.Many2one('res.users', string='Account Exec 2')
    post_log_id = fields.Many2one('res.users', string='Post Log User')
    logs_contact_id = fields.Many2one(
        'res.partner', string='Logs Contact',
        domain=[('contact_role', '=', 'logs')],
    )
    logs_cc = fields.Char(string='Logs CC (Email Addresses)')
    vendor_account_id = fields.Many2one(
        'res.partner', string='Vendor Account',
        domain=[('is_vendor_account', '=', True)],
    )

    # Network classification / setup
    cable_synd = fields.Selection(
        [('Cable', 'Cable'), ('Syndication', 'Syndication'), ('PP', 'PP'), ('Bundle', 'Bundle'), ('Digital', 'Digital'), ('GM', 'GM')],
        string='Cable / Synd',
    )
    network_owner = fields.Selection(
        [('ABC/Disney', 'ABC/Disney'), ('AccuWeather', 'AccuWeather'), ('BeIN Sports', 'BeIN Sports'), ('Bloodline Detectives', 'Bloodline Detectives'), ('CBS/FOX', 'CBS/FOX'), ('DigiTV', 'DigiTV'), ('FreeTV', 'FreeTV'), ('GrayTV', 'GrayTV'), ('Heartland', 'Heartland'), ('Hearst', 'Hearst'), ('Hemisphere', 'Hemisphere'), ('Merit Street Media', 'Merit Street Media'), ('MLB Network', 'MLB Network'), ('NBC', 'NBC'), ('NHL Network', 'NHL Network'), ('Novelisima', 'Novelisima'), ('Power Nation', 'Power Nation'), ('Scripps', 'Scripps'), ('Tegna', 'Tegna'), ('TV Azteca', 'TV Azteca'), ('Univision', 'Univision'), ('Law & Crime', 'Law & Crime')],
        string='Network Owner',
    )
    network_system = fields.Selection(
        [
            ('wide_orbit', 'Wide Orbit'),
            ('vci', 'VCI'),
            ('myers', 'Myers'),
            ('other', 'Other'),
        ],
        string='Network System',
    )
    deal_entity = fields.Selection(
        [('Marathon Ventures LLC', 'Marathon Ventures LLC')],
        string='Deal Entity',
    )
    ratings_quarter = fields.Selection(
        [('1', '1'), ('2', '2'), ('3', '3'), ('4', '4')],
        string='Ratings Quarter',
    )

    barter = fields.Boolean(string='Barter')
    rated = fields.Boolean(string='Rated')
    inactive = fields.Boolean(string='Inactive', tracking=True)
    detailed_invoices = fields.Boolean(string='Detailed Invoices')
    invoice_run = fields.Boolean(string='Invoice Run')
    spot_data_sync = fields.Boolean(string='Spot Data Sync')

    invoice_month = fields.Selection(
        [('Dec 2025', 'Dec 2025'), ('Jan 2026', 'Jan 2026'), ('Feb 2026', 'Feb 2026'), ('Mar 2026', 'Mar 2026'), ('Apr 2026', 'Apr 2026'), ('May 2026', 'May 2026'), ('Jun 2026', 'Jun 2026'), ('Jul 2026', 'Jul 2026'), ('Aug 2026', 'Aug 2026'), ('Sep 2026', 'Sep 2026'), ('Oct 2026', 'Oct 2026'), ('Nov 2026', 'Nov 2026'), ('Dec 2026', 'Dec 2026')],
        string='Invoice Month',
    )
    finance_invoice_template = fields.Selection(
        [('00 - Non Specific', '00 - Non Specific'), ('Long Form', 'Long Form'), ('Short Form', 'Short Form'), ('Syndicated/Bundle', 'Syndicated/Bundle')],
        string='Finance Invoice Template',
    )

    # Filler counts (numeric fields that count filler units per daypart)
    da_filler = fields.Integer(string='Daytime Filler')
    ef_filler = fields.Integer(string='Early Fringe Filler')
    em_filler = fields.Integer(string='Early Morning Filler')
    fr_filler = fields.Integer(string='Fringe Filler')
    lf_filler = fields.Integer(string='Late Fringe Filler')
    ln_filler = fields.Integer(string='Late Night Filler')
    on_filler = fields.Integer(string='Overnight Filler')
    pr_filler = fields.Integer(string='Prime Filler')
    ros_filler = fields.Integer(string='ROS Filler')
    syndication_filler = fields.Integer(string='Syndication Filler')
    filler_em = fields.Integer(string='Filler EM')

    # Log / Prelog scheduling
    clock_start_time = fields.Selection(
        [('5AM', '5AM'), ('6AM', '6AM'), ('4AM', '4AM')],
        string='Clock Start Time',
    )
    log_week = fields.Integer(string='Log Week')
    prelog_date = fields.Date(string='Prelog Date')
    prelog_date_time = fields.Datetime(string='Prelog Date/Time')
    prelog_version = fields.Integer(string='Prelog Version')
    pp_revision = fields.Integer(string='PP Revision')
    pp_revision_cycle = fields.Integer(string='PP Revision Cycle')
    pp_log_check_nw_history = fields.Text(string='PP Log Check NW History')
    pp_log_check_tw_history = fields.Text(string='PP Log Check TW History')
    rc_reconciled_lf_week = fields.Date(string='RCReconciled LF Week')
    rc_reconciled_week = fields.Date(string='RCreconciled Week')
    reconciled_week = fields.Date(string='Reconciled Week')
    template = fields.Integer(string='Template')
    version_time_stamp = fields.Datetime(string='Version Time Stamp')

    deal_ids = fields.One2many('marathon.deal', 'program_id', string='Deals')
    deal_count = fields.Integer(string='# Deals', compute='_compute_deal_count')
    program_count = fields.Integer(string='Program Count', default=1)

    # =================================================================== #
    # === SF parity fields (auto-generated, full Salesforce field set) === #
    # =================================================================== #
    bundle_name = fields.Char(string="Bundle Name")
    bundle_rate = fields.Float(string="Bundle Rate")
    conga_log_template = fields.Char(string="Conga Log Template")
    launch_week_del = fields.Date(string="Launch Week")
    merit_street_media_url_2025 = fields.Char(string="Merit Street Media URL 2025")
    r_creconciled_week = fields.Date(string="RCreconciled Week (SF)")
    team = fields.Char(string="Team")
    wc_filler = fields.Integer(string="WC Filler")
    wknd_da_filler = fields.Integer(string="WKND DA Filler")
    wknd_on_filler = fields.Integer(string="WKND ON Filler")
    wknd_pr_filler = fields.Integer(string="WKND PR Filler")
    week_pending = fields.Date(string="Week Pending")
    working_log_version = fields.Integer(string="Working Log Version")
    # === END SF parity fields ===
    _program_number_unique = models.Constraint(
        'UNIQUE(program_number)',
        'Program Number must be unique.',
    )

    @api.depends('deal_ids')
    def _compute_deal_count(self):
        for rec in self:
            rec.deal_count = len(rec.deal_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('program_number'):
                vals['program_number'] = self.env['ir.sequence'].next_by_code(
                    'marathon.program'
                ) or '/'
        return super().create(vals_list)

    def action_toggle_inactive(self):
        """Toggle the ``inactive`` flag (acts as Archive / Unarchive)."""
        for rec in self:
            rec.inactive = not rec.inactive

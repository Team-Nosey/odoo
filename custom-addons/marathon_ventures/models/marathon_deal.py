# -*- coding: utf-8 -*-
"""Salesforce object: ``Deal__c``.

In Marathon's domain a Deal represents a purchase order from an Agency on
behalf of an Advertiser. Schedule lines under a deal represent individual
order lines (week, daypart, units, rate, etc.).

This is the most-used object in the system; the SF version has 80 fields
including a large number of formula and roll-up summary fields. Here we
implement the business-meaningful subset and reproduce the roll-ups with
``@api.depends``.
"""

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class MarathonDeal(models.Model):
    _name = 'marathon.deal'
    _description = 'Deal'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'name'

    # --------------------------------------------------------------------- #
    # Identification
    # --------------------------------------------------------------------- #
    name = fields.Char(
        string='Deal Number', copy=False, readonly=True,
        default=lambda self: _('New'),
        help='Internal deal number (was AutoNumber in Salesforce).',
    )
    network_deal_number = fields.Char(
        string='Network Deal Number', tracking=True,
        help="Wide Orbit / network-side reference. Provided by the Planner.",
    )
    agency_deal_number = fields.Char(string='Agency Deal Number', tracking=True)
    sf_deal_id = fields.Char(string='SF Deal ID', copy=False)
    record_type = fields.Selection(
        [
            ('short_form', 'Short Form'),
            ('long_form', 'Long Form (Paid Programming)'),
        ],
        string='Record Type',
        default='short_form',
        required=True,
        tracking=True,
    )

    # --------------------------------------------------------------------- #
    # Core relationships
    # --------------------------------------------------------------------- #
    program_id = fields.Many2one(
        'marathon.program', string='Program / Network',
        required=True, ondelete='restrict', tracking=True,
    )
    brand_id = fields.Many2one(
        'marathon.brand', string='Brand ID',
        ondelete='restrict', tracking=True,
    )
    advertiser_id = fields.Many2one(
        'marathon.advertiser', string='Advertiser',
        related='brand_id.advertiser_id', store=True, readonly=True,
    )
    client_account_id = fields.Many2one(
        'res.partner', string='Client Account / Agency',
        domain=[('is_company', '=', True)], tracking=True,
    )
    contact_id = fields.Many2one(
        'res.partner', string='Buyer Contact',
        tracking=True,
        help="Buyer at the Agency. The Account on this contact must match the "
             "Client Account on the deal.",
    )
    sales_plan_id = fields.Many2one(
        'marathon.sales.plan', string='Sales Plan',
    )

    # --------------------------------------------------------------------- #
    # Order-line meta — the campaign string, codes, length etc.
    # --------------------------------------------------------------------- #
    campaign = fields.Char(
        string='Campaign', tracking=True,
        help="Quarter, year & length, e.g. \"1Q'21 :30\". Include any access / "
             "estimate / title codes from the agency paperwork.",
    )
    estimate = fields.Char(string='Estimate Code')
    access_code = fields.Char(string='Access Code')
    client_code = fields.Char(string='Client Code')
    product_code = fields.Char(string='Product Code')
    digital_id = fields.Char(string='Digital ID')

    length = fields.Selection(
        [('30', '30'), ('40', '40'), ('60', '60'), ('120', '120'), ('300', '300'), ('15', '15'), ('1710', '1710'), ('90', '90'), ('180', '180'), ('240', '240'), ('45', '45'), ('75', '75'), ('05', '05'), ('10', '10'), ('150', '150'), ('20', '20'), ('105', '105'), ('5', '5'), ('35', '35'), ('1714', '1714'), ('25', '25'), ('7', '7'), ('3510', '3510'), ('1650', '1650')],
        string='Length', required=True, tracking=True,
    )
    min_sep = fields.Selection(
        [('15', '15'), ('20', '20'), ('5', '5'), ('25', '25'), ('30', '30'), ('60', '60'), ('10', '10'), ('45', '45')],
        string='Min Sep', default='15', tracking=True,
        help="Minimum separation between this advertiser's units.",
    )
    max_sep = fields.Integer(
        string='Max Sep (mins)',
        help="Optional upper bound on separation.",
    )

    # --------------------------------------------------------------------- #
    # Classification & pricing
    # --------------------------------------------------------------------- #
    rate = fields.Monetary(
        string='Default Rate', currency_field='currency_id', tracking=True,
    )
    budget_30 = fields.Monetary(
        string='Budget (:30 equiv.)', currency_field='currency_id',
    )
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id, required=True,
    )
    deal_class = fields.Selection(
        [
            ('standard', 'Standard'),
            ('premium', 'Premium'),
            ('sponsorship', 'Sponsorship'),
            ('secured', 'Secured'),
            ('secured_healthcare', 'Secured - Health Care'),
        ],
        string='Class', default='standard', required=True, tracking=True,
        help='Standard = default. Premium = clearance watch. Sponsorship = added '
             'value. Secured = guaranteed 100% clearance.',
    )
    tier = fields.Selection(
        [('1', '1'), ('2', '2'), ('3', '3'), ('4', '4')],
        string='Tier',
    )
    quarter = fields.Selection(
        [('Q1', 'Q1'), ('Q2', 'Q2'), ('Q3', 'Q3'), ('Q4', 'Q4')],
        string='Quarter', tracking=True,
    )
    year = fields.Integer(string='Year', tracking=True)
    demographics = fields.Selection(
        [('F18-24', 'F18-24'), ('F18-25', 'F18-25'), ('F18-34', 'F18-34'), ('F18-49', 'F18-49'), ('F18-99', 'F18-99'), ('F25-34', 'F25-34'), ('F25-49', 'F25-49'), ('F25-54', 'F25-54'), ('F25-64', 'F25-64'), ('F25-99', 'F25-99'), ('F2-99', 'F2-99'), ('F35-49', 'F35-49'), ('F35-54', 'F35-54'), ('F35-64', 'F35-64'), ('F35-99', 'F35-99'), ('F45-54', 'F45-54'), ('F50-64', 'F50-64'), ('F50-99', 'F50-99'), ('F55-64', 'F55-64'), ('F55-99', 'F55-99'), ('F65-99', 'F65-99'), ('HH', 'HH'), ('M18-24', 'M18-24'), ('M18-34', 'M18-34'), ('M18-49', 'M18-49'), ('M18-99', 'M18-99'), ('M25-34', 'M25-34'), ('M25-49', 'M25-49'), ('M25-54', 'M25-54'), ('M25-64', 'M25-64'), ('M25-99', 'M25-99'), ('M2-99', 'M2-99'), ('M35-49', 'M35-49'), ('M35-54', 'M35-54'), ('M35-64', 'M35-64'), ('M35-99', 'M35-99'), ('M50-64', 'M50-64'), ('M50-99', 'M50-99'), ('M55-64', 'M55-64'), ('M55-99', 'M55-99'), ('M65-99', 'M65-99'), ('P12-17', 'P12-17'), ('P18-24', 'P18-24'), ('P18-34', 'P18-34'), ('P18-49', 'P18-49'), ('P18-99', 'P18-99'), ('P2-11', 'P2-11'), ('P2-17', 'P2-17'), ('P25-34', 'P25-34'), ('P25-49', 'P25-49'), ('P25-54', 'P25-54'), ('P25-64', 'P25-64'), ('P25-99', 'P25-99'), ('P2-99', 'P2-99'), ('P35-49', 'P35-49'), ('P35-54', 'P35-54'), ('P35-64', 'P35-64'), ('P35-99', 'P35-99'), ('P45-54', 'P45-54'), ('P50-64', 'P50-64'), ('P50-99', 'P50-99'), ('P55-64', 'P55-64'), ('P55-99', 'P55-99'), ('P6-11', 'P6-11'), ('P65-99', 'P65-99'), ('W18-34', 'W18-34'), ('W18-49', 'W18-49'), ('W18-99', 'W18-99'), ('W25-54', 'W25-54'), ('W2-99', 'W2-99'), ('W35-99', 'W35-99'), ('W50-99', 'W50-99'), ('F55+', 'F55+'), ('Fs25-54', 'Fs25-54'), ('Fs35-99', 'Fs35-99'), ('HHLD', 'HHLD'), ('M55+', 'M55+'), ('P2+', 'P2+'), ('P35+', 'P35+'), ('P55+', 'P55+'), ('P65+', 'P65+')],
        string='Demographics',
    )
    client_dr_gm_hybrid = fields.Selection(
        [('DR', 'DR'), ('GM', 'GM'), ('Hybrid', 'Hybrid'), ('END', 'END'), ('--', '--')],
        string='Client / DR / GM / Hybrid',
    )

    # --------------------------------------------------------------------- #
    # Restricted programming (multi-select)
    # --------------------------------------------------------------------- #
    restricted_programming_dna = fields.Char(
        string='Restricted Programming DNA',
        help='Comma-separated tags: news, sports, kids, religious, etc.',
    )

    # --------------------------------------------------------------------- #
    # Bundle handling
    # --------------------------------------------------------------------- #
    bundle_action = fields.Selection(
        [('NEW BUY', 'NEW BUY'), ('ADD TO SCHEDULE', 'ADD TO SCHEDULE'), ('CANCELED', 'CANCELED'), ('FREQUENCY REVISION', 'FREQUENCY REVISION'), ('TRAFFIC REVISION ONLY', 'TRAFFIC REVISION ONLY'), ('CANCEL BEFORE START', 'CANCEL BEFORE START'), ('FREQUENCY ADJUSTMENT/CANCEL', 'FREQUENCY ADJUSTMENT/CANCEL'), ('FREQUENCY REVISION/TRAFFIC CHANGE', 'FREQUENCY REVISION/TRAFFIC CHANGE')],
        string='Bundle Action',
    )
    bundle_start_week = fields.Date(string='Bundle Start Week')
    bundle_version = fields.Integer(string='Bundle Version')

    # --------------------------------------------------------------------- #
    # Booleans / flags
    # --------------------------------------------------------------------- #
    pi = fields.Boolean(string='PI', help='Per-Inquiry deal.')
    priority = fields.Boolean(string='Priority')
    e_i_friendly = fields.Boolean(string='E/I Friendly')
    revised = fields.Boolean(string='Revised', tracking=True)
    test_pp = fields.Boolean(string='Test PP')

    # --------------------------------------------------------------------- #
    # Important dates
    # --------------------------------------------------------------------- #
    log_exp_date = fields.Date(string='LOG Exp Date')
    ltc_date = fields.Date(
        string='LTC Date',
        help='Last To Clear / Last Telecast Date. The last day the campaign '
             'will air. Used by the cancellation flow.',
        tracking=True,
    )
    week_pending = fields.Date(
        string='Week Pending', compute='_compute_dates', store=True,
    )
    related_advertiser_log_exp_date = fields.Date(
        string='[DEP]Advertiser LOG Exp. Date',
        related='advertiser_id.adv_log_with_expiration_date', store=True, readonly=True,
    )

    # --------------------------------------------------------------------- #
    # Free-text
    # --------------------------------------------------------------------- #
    hiatus_dates = fields.Char(string='Hiatus Dates')
    raycom_comments = fields.Text(string='Raycom Comments')

    # --------------------------------------------------------------------- #
    # Status workflow (the lifecycle)
    # --------------------------------------------------------------------- #
    status = fields.Selection(
        [('Sold', 'Sold'), ('Canceled', 'Canceled'), ('Budget', 'Budget'), ('Historical', 'Historical')],
        string='Status', default='Budget', required=True, tracking=True,
    )

    # --------------------------------------------------------------------- #
    # One2many — the schedule lines
    # --------------------------------------------------------------------- #
    schedule_ids = fields.One2many(
        'marathon.schedule', 'deal_parent_id', string='Schedules',
    )

    # --------------------------------------------------------------------- #
    # Computed / roll-up summary fields
    # --------------------------------------------------------------------- #
    count_of_schedules = fields.Integer(
        string='Count of Schedules', compute='_compute_rollups', store=True,
    )
    count_of_weeks = fields.Integer(
        string='Count of Weeks', compute='_compute_rollups', store=True,
    )
    sum_of_total_dollars = fields.Monetary(
        string='Sum of Total Dollars', currency_field='currency_id',
        compute='_compute_rollups', store=True,
    )
    sum_of_units_available = fields.Integer(
        string='Sum of Units Available', compute='_compute_rollups', store=True,
    )
    week_min = fields.Date(
        string='Week (Min)', compute='_compute_rollups', store=True,
    )
    week_max = fields.Date(
        string='Week (Max)', compute='_compute_rollups', store=True,
    )
    ratings_quarter = fields.Selection(
        [('q1', 'Q1'), ('q2', 'Q2'), ('q3', 'Q3'), ('q4', 'Q4')],
        string='Ratings Quarter (Max)',
        compute='_compute_rollups', store=True,
    )
    deal_count = fields.Integer(
        string='Deal Count', default=1,
        help='Always 1 — preserved for SF formula compatibility.',
    )

    # --------------------------------------------------------------------- #
    # Salesforce formula passthroughs (computed)
    # --------------------------------------------------------------------- #
    advertiser_display = fields.Char(
        string='Advertiser Name (Display)',
        compute='_compute_display_strings', store=True,
        help='Salesforce formula passthrough — flat string of the '
             'advertiser name for use in reports and formulas.',
    )
    account_advertiser = fields.Char(
        string='Account / Advertiser', compute='_compute_display_strings', store=True,
    )
    account_advertiser_brand = fields.Char(
        string='Account+Advertiser+Brand',
        compute='_compute_display_strings', store=True,
    )
    program_account_advertiser_brand = fields.Char(
        string='Program / Account / Advertiser / Brand',
        compute='_compute_display_strings', store=True,
    )
    contact_email = fields.Char(
        string='Contact Email',
        related='contact_id.email', store=True, readonly=True,
    )

    # =================================================================== #
    # === SF parity fields (auto-generated, full Salesforce field set) === #
    # =================================================================== #
    account_advertiser_program = fields.Char(string="Account+Advertiser+Program")
    account_brand_program = fields.Char(string="Account+Brand+Program")
    account_brand = fields.Char(string="Account+Brand")
    actual_rating_year = fields.Integer(string="Actual Rating Year")
    brands = fields.Many2one('marathon.brand', string="Brands", ondelete='set null')
    cable_synd_pp_del = fields.Char(string="Cable/Synd/PP")
    class_field = fields.Selection([('None', 'None'), ('Premium', 'Premium'), ('Sponsorship', 'Sponsorship'), ('Secured', 'Secured'), ('Secured - Health Care', 'Secured - Health Care'), ('Sports Specific Buy', 'Sports Specific Buy')], string="Class (SF)")
    commercial_type = fields.Char(string="Commercial Type")
    conga_invoice_wapa = fields.Char(string="Conga Invoice WAPA")
    contact_account = fields.Char(string="ContactAccount")
    dis_fox_conga_invoice_url = fields.Char(string="DisFox Conga Invoice URL")
    entity_name = fields.Char(string="Entity Name")
    ff_invoice_month = fields.Float(string="FF Invoice Month")
    ff_long_form_invoice_month = fields.Float(string="FF Long Form Invoice Month")
    max_day = fields.Char(string="Max/Day")
    merit_street_media_2025 = fields.Char(string="Merit Street Media 2025")
    program_team_del_del = fields.Char(string="Program Team")
    ratings_year = fields.Integer(string="Ratings Year")
    sf_conga_invoice_formula = fields.Char(string="SF Conga Invoice Formula")
    sf_conga_invoice_new_synd = fields.Char(string="SF Conga Invoice New Synd")
    sf_conga_invoice_nosey = fields.Char(string="SF Conga Invoice Nosey")
    vendor_account = fields.Char(string="Vendor Account")
    vendor_commission = fields.Float(string="Vendor Commission")
    wapa_cinco_unwired_pi_url = fields.Char(string="WAPA Cinco Unwired PI URL")
    wapa_cinco_unwired_url = fields.Char(string="WAPA Cinco Unwired URL")
    week_min_field = fields.Float(string="Week MIN Field")
    sf_advertiser_text = fields.Char(string='Advertiser (SF Text)')
    # === END SF parity fields ===
    _name_unique = models.Constraint(
        'UNIQUE(name)',
        'Deal Number must be unique.',
    )

    # --------------------------------------------------------------------- #
    # Compute methods
    # --------------------------------------------------------------------- #
    @api.depends('schedule_ids', 'schedule_ids.total_dollars',
                 'schedule_ids.units_available', 'schedule_ids.week',
                 'schedule_ids.quarter', 'schedule_ids.is_cancelled')
    def _compute_rollups(self):
        for deal in self:
            active = deal.schedule_ids.filtered(lambda s: not s.is_cancelled)
            deal.count_of_schedules = len(active)
            weeks = active.mapped('week')
            deal.count_of_weeks = len(set(weeks))
            deal.sum_of_total_dollars = sum(active.mapped('total_dollars') or [0.0])
            deal.sum_of_units_available = sum(active.mapped('units_available') or [0])
            deal.week_min = min(weeks) if weeks else False
            deal.week_max = max(weeks) if weeks else False
            qs = active.mapped('quarter')
            # SF used MAX on quarter (text-sorted); we just take the highest seen.
            deal.ratings_quarter = max(qs) if qs else False

    @api.depends('schedule_ids.week', 'status')
    def _compute_dates(self):
        from datetime import date
        for deal in self:
            today = date.today()
            future_weeks = deal.schedule_ids.filtered(
                lambda s: not s.is_cancelled and s.week and s.week >= today
            ).mapped('week')
            deal.week_pending = min(future_weeks) if future_weeks else False

    @api.depends('client_account_id.name', 'advertiser_id.name',
                 'brand_id.name', 'program_id.name')
    def _compute_display_strings(self):
        for d in self:
            acct = d.client_account_id.name or ''
            adv = d.advertiser_id.name or ''
            brand = d.brand_id.name or ''
            prog = d.program_id.name or ''
            d.advertiser_display = adv
            d.account_advertiser = (
                '%s / %s' % (acct, adv) if acct and adv else (acct or adv)
            )
            d.account_advertiser_brand = ' / '.join(
                p for p in (acct, adv, brand) if p
            )
            d.program_account_advertiser_brand = ' / '.join(
                p for p in (prog, acct, adv, brand) if p
            )

    # --------------------------------------------------------------------- #
    # Validation rules (subset of the 13 SF rules — those most likely to bite)
    # --------------------------------------------------------------------- #
    @api.constrains('contact_id', 'client_account_id')
    def _check_contact_matches_account(self):
        for deal in self:
            if (deal.contact_id and deal.client_account_id
                    and deal.contact_id.parent_id
                    and deal.contact_id.parent_id != deal.client_account_id):
                raise ValidationError(_(
                    "Contact's Account (%s) must match the Deal's Client "
                    "Account (%s). The contact and agency must agree.",
                    deal.contact_id.parent_id.name,
                    deal.client_account_id.name,
                ))

    @api.constrains('brand_id')
    def _check_brand_approved(self):
        for deal in self:
            if (deal.brand_id and deal.brand_id.approval_status not in
                    ('approved',)):
                # Don't raise — just warn via chatter & activity
                deal.message_post(
                    body=_(
                        "Brand %s is not Approved (current status: %s). "
                        "Please contact your Planner or Ops Manager.",
                        deal.brand_id.name,
                        deal.brand_id.approval_status or 'Unknown',
                    )
                )

    # --------------------------------------------------------------------- #
    # CRUD / lifecycle
    # --------------------------------------------------------------------- #
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'marathon.deal'
                ) or _('New')
        return super().create(vals_list)

    # --------------------------------------------------------------------- #
    # Status transitions
    # --------------------------------------------------------------------- #
    # --- Workflow methods (mapped to SF Status picklist) ---------------- #
    # SF Status values: Budget (draft/pending) -> Sold (booked/on_air) ->
    # Historical (completed); Canceled at any time.
    def action_submit_for_approval(self):
        for d in self:
            if d.status != 'Budget':
                raise ValidationError(_("Only Budget deals can be submitted."))
            d.message_post(body=_("Deal submitted for approval."))

    def action_book(self):
        for d in self:
            if not d.schedule_ids:
                raise ValidationError(_(
                    "Cannot book a deal with no schedules. Create at least one "
                    "schedule first."
                ))
            d.status = 'Sold'
            d.message_post(body=_("Deal booked / Sold."))

    def action_set_on_air(self):
        # On-air maps to Sold per SF; method retained for backwards UX
        for d in self:
            d.status = 'Sold'

    def action_complete(self):
        for d in self:
            d.status = 'Historical'

    def action_cancel(self):
        for d in self:
            d.status = 'Canceled'
            d.schedule_ids.write({'is_cancelled': True})
            d.message_post(body=_("Deal cancelled — all schedules marked cancelled."))

    def action_reset_to_draft(self):
        for d in self:
            d.status = 'Budget'

    # --------------------------------------------------------------------- #
    # Open the Deal Revisions wizard (LTC, Rate, Extend, etc.)
    # --------------------------------------------------------------------- #
    def action_open_deal_revisions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Deal Revisions: %s') % (self.name,),
            'res_model': 'marathon.deal.revision.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_deal_id': self.id,
            },
        }


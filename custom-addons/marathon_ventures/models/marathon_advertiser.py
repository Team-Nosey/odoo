# -*- coding: utf-8 -*-
"""Salesforce object: ``Advertiser__c``.

In the SF org an Advertiser is a separate object linked to an Account
(usually the Agency that books on its behalf). We keep the same model
shape in Odoo, with a Many2one to ``res.partner`` for the Account.
"""

from odoo import api, fields, models


# Picklist of network-specific advertiser separation requirements.
# In Salesforce these were many ``*_Adv_Sep__c`` picklists with the same
# value set; we collapse them to a single Selection reused everywhere.
SEP_SELECTION = [
    ('0', '0'),
    ('5', '5'),
    ('10', '10'),
    ('15', '15'),
    ('20', '20'),
    ('30', '30'),
    ('45', '45'),
    ('60', '60'),
]


class MarathonAdvertiser(models.Model):
    _name = 'marathon.advertiser'
    _description = 'Advertiser'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'
    _rec_name = 'name'

    name = fields.Char(string='Advertiser Name', required=True, tracking=True)
    advertiser_number = fields.Char(
        string='Advertiser Number', copy=False, readonly=True,
    )
    account_id = fields.Many2one(
        'res.partner', string='Account', tracking=True,
        domain=[('is_company', '=', True)],
        help='Salesforce ``Account__c`` lookup.',
    )
    umbrella_account_id = fields.Many2one(
        'res.partner', string='Umbrella Account',
        domain=[('is_company', '=', True)],
    )
    umbrella_account_2_id = fields.Many2one(
        'res.partner', string='Umbrella Account 2',
        domain=[('is_company', '=', True)],
    )

    advertiser_credit_limit = fields.Monetary(
        string='Advertiser Credit Limit',
        currency_field='currency_id',
    )
    intacct_adv_balance = fields.Monetary(
        string='Intacct Adv Balance',
        currency_field='currency_id',
    )
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id,
    )

    advertiser_approved_to_book = fields.Boolean(string='Advertiser Approved to Book')
    advertiser_cia = fields.Boolean(string='Advertiser CIA')
    hold_placed_on_advertiser_account = fields.Boolean(
        string='Hold Placed on Advertiser Account', tracking=True,
    )
    monitoring = fields.Boolean(string='Monitoring')
    new_advertiser = fields.Boolean(string='New Advertiser', default=True)

    duplicate_approval = fields.Selection(
        [('Approved', 'Approved'), ('Not Approved', 'Not Approved')],
        string='Duplicate Approval',
        tracking=True,
    )
    duplicate_name_check = fields.Char(string='Duplicate Name Check')
    # Salesforce label: "SF Commercial Type"
    # END - Endemic, PSA - Public Service Announcement
    commercial = fields.Selection(
        [('DR', 'DR'), ('GM', 'GM'), ('HYBRID', 'HYBRID'), ('PSA', 'PSA'), ('END', 'END'), ('PROMO', 'PROMO'), ('POLITICAL', 'POLITICAL'), ('TUNE IN', 'TUNE IN'), ('--', '--')],
        string='SF Commercial Type',
        tracking=True,
    )

    adv_log_with_expiration_date = fields.Date(
        string='ADV LOG with Expiration Date',
    )
    log_exp_test = fields.Date(string='LOG Exp Test')

    comments = fields.Text(string='Comments')

    # Network-specific advertiser separation (Salesforce had a column per
    # network; we model them as a single tab of fields)
    accuweather_adv_sep = fields.Selection(SEP_SELECTION, string='AccuWeather Sep')
    bouncetv_adv_sep = fields.Selection(SEP_SELECTION, string='BounceTV Sep')
    courttv_adv_sep = fields.Selection(SEP_SELECTION, string='CourtTV Sep')
    defy_adv_sep = fields.Selection(SEP_SELECTION, string='DEFY Adv Sep')
    grittv_adv_sep = fields.Selection(SEP_SELECTION, string='GritTV Sep')
    ion_mys_adv_sep = fields.Selection(SEP_SELECTION, string='ION Mys Adv Sep')
    ion_tv_adv_sep = fields.Selection(SEP_SELECTION, string='ION TV Adv Sep')
    laff_adv_sep = fields.Selection(SEP_SELECTION, string='Laff Adv Sep')
    mlb_adv_sep = fields.Selection(SEP_SELECTION, string='MLB Adv Sep')
    merit_street_adv_sep = fields.Selection(SEP_SELECTION, string='Merit Street Adv Sep')
    nhl_adv_sep = fields.Selection(SEP_SELECTION, string='NHL Adv Sep')
    nosey_adv_sep = fields.Selection(SEP_SELECTION, string='NoseyTV Sep')
    quest_adv_sep = fields.Selection(SEP_SELECTION, string='Quest Adv Sep')
    scripps_news_adv_sep = fields.Selection(SEP_SELECTION, string='Scripps News Adv Sep')
    true_crime_adv_sep = fields.Selection(SEP_SELECTION, string='True Crime Adv Sep')
    twist_adv_sep = fields.Selection(SEP_SELECTION, string='Twist Adv Sep')

    # Reverse relations
    brand_ids = fields.One2many('marathon.brand', 'advertiser_id', string='Brands')
    deal_ids = fields.One2many(
        'marathon.deal', 'advertiser_id', string='Deals'
    )

    advertiser_count = fields.Integer(
        string='Advertiser Count', compute='_compute_counts',
    )
    brand_count = fields.Integer(
        string='# Brands', compute='_compute_counts',
    )
    deal_count = fields.Integer(
        string='# Deals', compute='_compute_counts',
    )

    # =================================================================== #
    # === SF parity fields (auto-generated, full Salesforce field set) === #
    # =================================================================== #
    accu_weather_adv_sep = fields.Selection([('0', '0'), ('5', '5'), ('10', '10'), ('15', '15'), ('20', '20'), ('30', '30'), ('45', '45'), ('60', '60')], string="AccuWeather Adv Sep")
    bounce_tv_adv_sep = fields.Selection([('0', '0'), ('5', '5'), ('10', '10'), ('15', '15'), ('20', '20'), ('30', '30'), ('45', '45'), ('60', '60')], string="BounceTV Adv Sep")
    court_tv_adv_sep = fields.Selection([('0', '0'), ('5', '5'), ('10', '10'), ('15', '15'), ('20', '20'), ('30', '30'), ('45', '45'), ('60', '60')], string="CourtTV Adv Sep")
    grit_tv_adv_sep = fields.Selection([('0', '0'), ('5', '5'), ('10', '10'), ('15', '15'), ('20', '20'), ('30', '30'), ('45', '45'), ('60', '60')], string="GritTV Adv Sep")
    nosey_tv_adv_sep = fields.Selection([('0', '0'), ('5', '5'), ('10', '10'), ('15', '15'), ('20', '20'), ('30', '30'), ('45', '45'), ('60', '60')], string="NoseyTV Adv Sep", default='15')
    # === END SF parity fields ===
    @api.depends('brand_ids', 'deal_ids')
    def _compute_counts(self):
        for rec in self:
            rec.brand_count = len(rec.brand_ids)
            rec.deal_count = len(rec.deal_ids)
            rec.advertiser_count = 1

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('advertiser_number'):
                vals['advertiser_number'] = self.env['ir.sequence'].next_by_code(
                    'marathon.advertiser'
                ) or '/'
        return super().create(vals_list)

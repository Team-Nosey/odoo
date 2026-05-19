# -*- coding: utf-8 -*-
"""Salesforce object: ``Brands__c``."""

from odoo import api, fields, models


class MarathonBrand(models.Model):
    _name = 'marathon.brand'
    _description = 'Brand'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'
    _rec_name = 'display_name'

    name = fields.Char(string='Brand Name', required=True, tracking=True)
    brand_number = fields.Char(
        string='Brand Number', copy=False, readonly=True,
    )
    display_name = fields.Char(
        string='Display Name', compute='_compute_display_name', store=True,
    )

    advertiser_id = fields.Many2one(
        'marathon.advertiser', string='Advertiser', required=True,
        ondelete='restrict', tracking=True,
    )
    account_id = fields.Many2one(
        'res.partner', string='Account',
        related='advertiser_id.account_id', store=True, readonly=True,
    )
    alternate_brand_names = fields.Text(string='Alternate Brand Names')
    digital_id = fields.Char(string='Digital ID')
    unique_brand_identifier = fields.Char(string='Unique Brand Identifier')

    approval_status = fields.Selection(
        [('Pending', 'Pending'), ('Approved', 'Approved'), ('Rejected', 'Rejected')],
        string='Approval Status',
        default='Pending',
        tracking=True,
        required=True,
    )
    approved_duplicate = fields.Selection(
        [('Approved', 'Approved'), ('Not Approved', 'Not Approved')],
        string='Duplicate Approval',
    )

    category = fields.Selection(
        [('.Com/E-Commerce', '.Com/E-Commerce'), ('Apparel/Accessories', 'Apparel/Accessories'), ('Appliances/Home Gadgets', 'Appliances/Home Gadgets'), ('Auto Accessories', 'Auto Accessories'), ('Auto Care', 'Auto Care'), ('Auto Insurance', 'Auto Insurance'), ('Auto - Other', 'Auto - Other'), ('Auto Warranty', 'Auto Warranty'), ('Baby', 'Baby'), ('Banking Services', 'Banking Services'), ('Beauty Product', 'Beauty Product'), ('Bedding/Mattress', 'Bedding/Mattress'), ('Business/Professional Services', 'Business/Professional Services'), ('Charity', 'Charity'), ('Cleaning Supplies', 'Cleaning Supplies'), ('Credit Monitoring', 'Credit Monitoring'), ('Digital', 'Digital'), ('Education', 'Education'), ('Electronics/Accessories', 'Electronics/Accessories'), ('Entertainment/Gaming', 'Entertainment/Gaming'), ('Exercise Equipment', 'Exercise Equipment'), ('Financial-Other', 'Financial-Other'), ('Fitness - Other', 'Fitness - Other'), ('Food and Beverages', 'Food and Beverages'), ('Hair Care Product', 'Hair Care Product'), ('Health', 'Health'), ('Health and Dental Insurance', 'Health and Dental Insurance'), ('Home Decor/Accessories', 'Home Decor/Accessories'), ('Home Gadgets', 'Home Gadgets'), ('Home Improvement', 'Home Improvement'), ('Home Insurance', 'Home Insurance'), ('Household - Other', 'Household - Other'), ('Insurance - Other', 'Insurance - Other'), ('Insurance Provider', 'Insurance Provider'), ('Investment Services', 'Investment Services'), ('Kitchen Supplies', 'Kitchen Supplies'), ('Legal - Medical Equipment', 'Legal - Medical Equipment'), ('Legal - Medical Services', 'Legal - Medical Services'), ('Legal - Pharmaceuticals', 'Legal - Pharmaceuticals'), ('Legal Services', 'Legal Services'), ('Life Insurance', 'Life Insurance'), ('Loan/Debt Services', 'Loan/Debt Services'), ('Media/Telecom', 'Media/Telecom'), ('Medical Devices and Equipment', 'Medical Devices and Equipment'), ('Medical Facilities/Clinics', 'Medical Facilities/Clinics'), ('Medical Services-Other', 'Medical Services-Other'), ('Medicare Advantage', 'Medicare Advantage'), ('Medicare Supplement', 'Medicare Supplement'), ('Mental Health', 'Mental Health'), ('Mobile Apps', 'Mobile Apps'), ('Office Supplies', 'Office Supplies'), ('Oral Hygiene', 'Oral Hygiene'), ('Outdoor', 'Outdoor'), ('Paid Programming', 'Paid Programming'), ('Pets', 'Pets'), ('Pharmaceutical - Other', 'Pharmaceutical - Other'), ('Pharmaceutical - Over the Counter', 'Pharmaceutical - Over the Counter'), ('Pharmaceutical - Prescription', 'Pharmaceutical - Prescription'), ('Political', 'Political'), ('Real Estate Services', 'Real Estate Services'), ('Skin Care Product', 'Skin Care Product'), ('Social Networking/Dating', 'Social Networking/Dating'), ('Software', 'Software'), ('Sporting Goods', 'Sporting Goods'), ('Supplements/Vitamins', 'Supplements/Vitamins'), ('Tax Services', 'Tax Services'), ('Toiletry', 'Toiletry'), ('Toys and Hobbies', 'Toys and Hobbies'), ('Travel', 'Travel'), ('Weight Loss - Program', 'Weight Loss - Program'), ('Weight Loss - Supplement', 'Weight Loss - Supplement')],
        string='Category',
    )
    primary_demographic = fields.Selection(
        [('A18+', 'A18+'), ('A18-34', 'A18-34'), ('A18-49', 'A18-49'), ('A2+', 'A2+'), ('A25+', 'A25+'), ('A25-34', 'A25-34'), ('A25-49', 'A25-49'), ('A25-54', 'A25-54'), ('A25-64', 'A25-64'), ('A35+', 'A35+'), ('A35-54', 'A35-54'), ('A35-64', 'A35-64'), ('A45+', 'A45+'), ('A45-64', 'A45-64'), ('A50+', 'A50+'), ('A55+', 'A55+'), ('A65+', 'A65+'), ('HH', 'HH'), ('M18+', 'M18+'), ('M18-34', 'M18-34'), ('M18-49', 'M18-49'), ('M2+', 'M2+'), ('M25+', 'M25+'), ('M25-34', 'M25-34'), ('M25-49', 'M25-49'), ('M25-54', 'M25-54'), ('M25-64', 'M25-64'), ('M35+', 'M35+'), ('M35-54', 'M35-54'), ('M35-64', 'M35-64'), ('M45+', 'M45+'), ('M45-64', 'M45-64'), ('M50+', 'M50+'), ('M55+', 'M55+'), ('M65+', 'M65+'), ('W18+', 'W18+'), ('W18-34', 'W18-34'), ('W18-49', 'W18-49'), ('W2+', 'W2+'), ('W25+', 'W25+'), ('W25-34', 'W25-34'), ('W25-49', 'W25-49'), ('W25-54', 'W25-54'), ('W25-64', 'W25-64'), ('W35+', 'W35+'), ('W35-54', 'W35-54'), ('W35-64', 'W35-64'), ('W45+', 'W45+'), ('W45-64', 'W45-64'), ('W50+', 'W50+'), ('W55+', 'W55+'), ('W65+', 'W65+')],
        string='Primary Demographic',
    )

    e_i_friendly = fields.Boolean(string='E/I Friendly')

    deal_ids = fields.One2many('marathon.deal', 'brand_id', string='Deals')
    deal_count = fields.Integer(string='# Deals', compute='_compute_deal_count')

    # =================================================================== #
    # === SF parity fields (auto-generated, full Salesforce field set) === #
    # =================================================================== #
    unique_brand_identifer = fields.Char(string="Unique Brand Identifer")
    # === END SF parity fields ===
    @api.depends('deal_ids')
    def _compute_deal_count(self):
        for rec in self:
            rec.deal_count = len(rec.deal_ids)

    @api.depends('name', 'advertiser_id.name')
    def _compute_display_name(self):
        for rec in self:
            if rec.advertiser_id:
                rec.display_name = '%s - %s' % (rec.name or '', rec.advertiser_id.name)
            else:
                rec.display_name = rec.name or ''

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('brand_number'):
                vals['brand_number'] = self.env['ir.sequence'].next_by_code(
                    'marathon.brand'
                ) or '/'
        return super().create(vals_list)

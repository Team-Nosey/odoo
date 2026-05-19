# -*- coding: utf-8 -*-
"""Salesforce objects: ``Sales_Quote__c``, ``Sales_Quote_Item__c``,
``Sales_Quote_Total__c``.

Marathon Ventures uses a quote → order → invoice flow with custom
Salesforce objects. Although Odoo has a native ``sale.order`` model, the
SF objects carry domain-specific fields (deal/schedule reference, SF IDs,
etc.) that make a 1-to-1 wrap awkward. We therefore implement matching
``marathon.sales.quote`` models and link them to ``sale.order`` for
finance integration.
"""

from odoo import api, fields, models, _


class MarathonSalesQuote(models.Model):
    _name = 'marathon.sales.quote'
    _description = 'Sales Quote'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='Quote Number', copy=False, readonly=True,
        default=lambda self: _('New'),
    )
    deal_id = fields.Many2one('marathon.deal', string='Deal', tracking=True)
    advertiser_id = fields.Many2one(
        'marathon.advertiser', string='Advertiser', tracking=True,
    )
    brand_id = fields.Many2one('marathon.brand', string='Brand')
    program_id = fields.Many2one('marathon.program', string='Program')
    client_account_id = fields.Many2one(
        'res.partner', string='Client Account',
        domain=[('is_company', '=', True)],
    )
    contact_id = fields.Many2one('res.partner', string='Contact')

    quote_date = fields.Date(
        string='Quote Date', default=fields.Date.context_today, tracking=True,
    )
    valid_until = fields.Date(string='Valid Until')
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id,
    )

    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('sent', 'Sent'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
            ('converted', 'Converted to Order'),
        ],
        string='State',
        default='draft',
        tracking=True,
    )

    item_ids = fields.One2many(
        'marathon.sales.quote.item', 'quote_id', string='Items',
    )
    total_id = fields.One2many(
        'marathon.sales.quote.total', 'quote_id', string='Totals',
    )

    sale_order_id = fields.Many2one(
        'sale.order', string='Linked Sale Order',
        help='Set when this quote is converted to a finance Sale Order.',
    )

    notes = fields.Text(string='Notes')

    total_amount = fields.Monetary(
        string='Total Amount', currency_field='currency_id',
        compute='_compute_total', store=True,
    )

    # =================================================================== #
    # === SF parity fields (auto-generated, full Salesforce field set) === #
    # =================================================================== #
    account = fields.Many2one('res.partner', string="Account", ondelete='set null')
    bill_to_address_1 = fields.Char(string="Bill to Address 1")
    bill_to_address_2 = fields.Char(string="Bill to Address 2")
    bill_to_city = fields.Char(string="Bill to City")
    bill_to_company_name = fields.Char(string="Bill to Company Name")
    bill_to_country = fields.Char(string="Bill to Country")
    bill_to_name = fields.Char(string="Bill to Name")
    bill_to_state = fields.Char(string="Bill to State")
    bill_to_zip_code = fields.Char(string="Bill to Zip Code")
    document_number = fields.Char(string="Document Number")
    document_type = fields.Char(string="Document Type")
    message = fields.Text(string="Message")
    opportunity = fields.Many2one('res.partner', string="Opportunity", ondelete='set null')
    reference_number = fields.Char(string="Reference Number")
    ship_date = fields.Date(string="Ship Date")
    ship_to_address_1 = fields.Char(string="Ship to Address 1")
    ship_to_address_2 = fields.Char(string="Ship to Address 2")
    ship_to_city = fields.Char(string="Ship to City")
    ship_to_company_name = fields.Char(string="Ship to Company Name")
    ship_to_country = fields.Char(string="Ship to Country")
    ship_to_name = fields.Char(string="Ship to Name")
    ship_to_state = fields.Char(string="Ship to State")
    ship_to_zip_code = fields.Char(string="Ship to Zip Code")
    subtotal = fields.Monetary(string="Subtotal", currency_field='currency_id')
    terms = fields.Char(string="Terms")
    # === END SF parity fields ===
    @api.depends('item_ids.line_total')
    def _compute_total(self):
        for q in self:
            q.total_amount = sum(q.item_ids.mapped('line_total') or [0.0])

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'marathon.sales.quote'
                ) or _('New')
        return super().create(vals_list)

    def action_send(self):
        for q in self:
            q.state = 'sent'

    def action_approve(self):
        for q in self:
            q.state = 'approved'

    def action_reject(self):
        for q in self:
            q.state = 'rejected'

    def action_convert_to_order(self):
        SO = self.env['marathon.sales.order']
        for q in self:
            order = SO.create({
                'quote_id': q.id,
                'deal_id': q.deal_id.id,
                'advertiser_id': q.advertiser_id.id,
                'brand_id': q.brand_id.id,
                'program_id': q.program_id.id,
                'client_account_id': q.client_account_id.id,
                'contact_id': q.contact_id.id,
                'order_date': fields.Date.context_today(self),
                'currency_id': q.currency_id.id,
            })
            for it in q.item_ids:
                self.env['marathon.sales.order.item'].create({
                    'order_id': order.id,
                    'name': it.name,
                    'description': it.description,
                    'quantity': it.quantity,
                    'unit_price': it.unit_price,
                    'line_number': it.line_number,
                    'schedule_id': it.schedule_id.id,
                })
            q.state = 'converted'


class MarathonSalesQuoteItem(models.Model):
    _name = 'marathon.sales.quote.item'
    _description = 'Sales Quote Item'
    _order = 'quote_id, line_number'

    quote_id = fields.Many2one(
        'marathon.sales.quote', string='Quote', required=True,
        ondelete='cascade',
    )
    line_number = fields.Integer(string='Line Number')
    name = fields.Char(string='Item Name', required=True)
    description = fields.Text(string='Description')
    schedule_id = fields.Many2one('marathon.schedule', string='Schedule')
    quantity = fields.Float(string='Quantity', default=1.0)
    unit_price = fields.Monetary(string='Unit Price', currency_field='currency_id')
    line_total = fields.Monetary(
        string='Line Total', currency_field='currency_id',
        compute='_compute_total', store=True,
    )
    currency_id = fields.Many2one(
        'res.currency', related='quote_id.currency_id', store=True, readonly=True,
    )

    # =================================================================== #
    # === SF parity fields (auto-generated, full Salesforce field set) === #
    # =================================================================== #
    department = fields.Char(string="Department")
    extended_price = fields.Monetary(string="Extended Price", currency_field='currency_id')
    item = fields.Char(string="Item")
    location = fields.Char(string="Location")
    memo = fields.Char(string="Memo")
    opportunity = fields.Many2one('res.partner', string="Opportunity", ondelete='set null')
    price = fields.Monetary(string="Price", currency_field='currency_id')
    sales_quote = fields.Many2one('marathon.sales.quote', string="Sales Quote", ondelete='cascade')
    site = fields.Char(string="Site")
    unit = fields.Char(string="Unit")
    # === END SF parity fields ===

    @api.depends('quantity', 'unit_price')
    def _compute_total(self):
        for it in self:
            it.line_total = (it.quantity or 0.0) * (it.unit_price or 0.0)


class MarathonSalesQuoteTotal(models.Model):
    _name = 'marathon.sales.quote.total'
    _description = 'Sales Quote Total'

    quote_id = fields.Many2one(
        'marathon.sales.quote', string='Quote', required=True,
        ondelete='cascade',
    )
    name = fields.Char(string='Total Type', default='Subtotal')
    amount = fields.Monetary(string='Amount', currency_field='currency_id')
    currency_id = fields.Many2one(
        'res.currency', related='quote_id.currency_id', store=True, readonly=True,
    )
    sequence = fields.Integer(string='Sequence', default=10)

    # =================================================================== #
    # === SF parity fields (auto-generated, full Salesforce field set) === #
    # =================================================================== #
    absolute_value = fields.Monetary(string="Absolute Value", currency_field='currency_id')
    percent_value = fields.Float(string="Percent Value")
    sales_quote = fields.Many2one('marathon.sales.quote', string="Sales Quote", ondelete='cascade')
    subtotal = fields.Monetary(string="Subtotal", currency_field='currency_id')
    total = fields.Monetary(string="Total", currency_field='currency_id')
    sf_date = fields.Date(string='Date')
    # === END SF parity fields ===

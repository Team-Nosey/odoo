# -*- coding: utf-8 -*-
"""Salesforce objects: ``Sales_Invoice__c``, ``Sales_Invoice_Item__c``,
``Sales_Invoice_Total__c``, ``Sales_Invoice_Payment__c``."""

from odoo import api, fields, models, _


class MarathonSalesInvoice(models.Model):
    _name = 'marathon.sales.invoice'
    _description = 'Sales Invoice'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'invoice_date desc, name desc'

    name = fields.Char(
        string='Invoice Number', copy=False, readonly=True,
        default=lambda self: _('New'),
    )
    order_id = fields.Many2one(
        'marathon.sales.order', string='Sales Order', tracking=True,
    )
    deal_id = fields.Many2one('marathon.deal', string='Deal', tracking=True)
    advertiser_id = fields.Many2one(
        'marathon.advertiser', string='Advertiser', tracking=True,
    )
    client_account_id = fields.Many2one(
        'res.partner', string='Client Account',
        domain=[('is_company', '=', True)],
    )
    program_id = fields.Many2one(
        'marathon.program', string='Program',
        related='deal_id.program_id', store=True, readonly=True,
    )

    invoice_date = fields.Date(
        string='Invoice Date', default=fields.Date.context_today, tracking=True,
    )
    due_date = fields.Date(string='Due Date')
    invoice_month = fields.Char(
        string='Invoice Month', compute='_compute_invoice_month', store=True,
    )

    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id,
    )

    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('issued', 'Issued'),
            ('partial', 'Partially Paid'),
            ('paid', 'Paid'),
            ('overdue', 'Overdue'),
            ('cancelled', 'Cancelled'),
        ],
        string='State',
        default='draft',
        tracking=True,
    )

    item_ids = fields.One2many(
        'marathon.sales.invoice.item', 'invoice_id', string='Items',
    )
    payment_ids = fields.One2many(
        'marathon.sales.invoice.payment', 'invoice_id', string='Payments',
    )
    total_id = fields.One2many(
        'marathon.sales.invoice.total', 'invoice_id', string='Totals',
    )

    total_amount = fields.Monetary(
        string='Total Amount', currency_field='currency_id',
        compute='_compute_amounts', store=True,
    )
    paid_amount = fields.Monetary(
        string='Paid Amount', currency_field='currency_id',
        compute='_compute_amounts', store=True,
    )
    balance_due = fields.Monetary(
        string='Balance Due', currency_field='currency_id',
        compute='_compute_amounts', store=True,
    )

    notes = fields.Text(string='Notes')

    # =================================================================== #
    # === SF parity fields (auto-generated, full Salesforce field set) === #
    # =================================================================== #
    account = fields.Many2one('res.partner', string="Account", ondelete='set null')
    amount_due = fields.Monetary(string="Amount Due", currency_field='currency_id')
    amount_paid = fields.Monetary(string="Amount Paid", currency_field='currency_id')
    avg_dtp = fields.Integer(string="Avg DTP")
    bill_to_address_1 = fields.Char(string="[Dep]Bill to Address 1")
    bill_to_address_2 = fields.Char(string="[Dep]Bill to Address 2")
    bill_to_city = fields.Char(string="[Dep]Bill to City")
    bill_to_company_name = fields.Char(string="[Dep]Bill to Company Name")
    bill_to_country = fields.Char(string="[Dep]Bill to Country")
    bill_to_name = fields.Char(string="[Dep]Bill to Name")
    bill_to_state = fields.Char(string="[Dep]Bill to State")
    bill_to_zip_code = fields.Char(string="[Dep]Bill to Zip Code")
    dso = fields.Integer(string="DSO")
    document_number = fields.Char(string="Document Number")
    document_type = fields.Char(string="Document Type")
    intacct_entity = fields.Char(string="Intacct Entity")
    intacct_sales_invoice_inv = fields.Char(string="Intacct Sales Invoice-INV")
    invoice_amount = fields.Monetary(string="Invoice Amount", currency_field='currency_id')
    message = fields.Text(string="Message")
    opportunity = fields.Many2one('res.partner', string="[Dep]Opportunity", ondelete='set null')
    parent_entity = fields.Char(string="Parent Entity")
    payment_status = fields.Char(string="Payment Status")
    reference_number = fields.Char(string="Reference Number")
    sales_invoice_payment_date = fields.Date(string="Sales Invoice Payment Date")
    ship_date = fields.Date(string="Ship Date")
    ship_to_address_1 = fields.Char(string="[Dep]Ship to Address 1")
    ship_to_address_2 = fields.Char(string="[Dep]Ship to Address 2")
    ship_to_city = fields.Char(string="[Dep]Ship to City")
    ship_to_company_name = fields.Char(string="[Dep]Ship to Company Name")
    ship_to_country = fields.Char(string="[Dep]Ship to Country")
    ship_to_name = fields.Char(string="[Dep]Ship to Name")
    ship_to_state = fields.Char(string="[Dep]Ship to State")
    ship_to_zip_code = fields.Char(string="[Dep]Ship to Zip Code")
    subtotal = fields.Monetary(string="Subtotal", currency_field='currency_id')
    terms = fields.Char(string="Terms")
    # === END SF parity fields ===
    @api.depends('invoice_date')
    def _compute_invoice_month(self):
        for inv in self:
            if inv.invoice_date:
                inv.invoice_month = inv.invoice_date.strftime('%b %Y')
            else:
                inv.invoice_month = False

    @api.depends('item_ids.line_total', 'payment_ids.amount')
    def _compute_amounts(self):
        for inv in self:
            inv.total_amount = sum(inv.item_ids.mapped('line_total') or [0.0])
            inv.paid_amount = sum(inv.payment_ids.mapped('amount') or [0.0])
            inv.balance_due = inv.total_amount - inv.paid_amount

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'marathon.sales.invoice'
                ) or _('New')
        return super().create(vals_list)

    def action_issue(self):
        for inv in self:
            inv.state = 'issued'

    def action_mark_paid(self):
        for inv in self:
            inv.state = 'paid'

    def action_cancel(self):
        for inv in self:
            inv.state = 'cancelled'


class MarathonSalesInvoiceItem(models.Model):
    _name = 'marathon.sales.invoice.item'
    _description = 'Sales Invoice Item'
    _order = 'invoice_id, line_number'

    invoice_id = fields.Many2one(
        'marathon.sales.invoice', string='Invoice', required=True,
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
        'res.currency', related='invoice_id.currency_id', store=True, readonly=True,
    )

    # =================================================================== #
    # === SF parity fields (auto-generated, full Salesforce field set) === #
    # =================================================================== #
    department = fields.Char(string="[Dep]Department")
    extended_price = fields.Monetary(string="Extended Price", currency_field='currency_id')
    item = fields.Char(string="Item")
    location = fields.Char(string="Location")
    memo = fields.Char(string="[Dep]Memo")
    opportunity = fields.Many2one('res.partner', string="[Dep]Opportunity", ondelete='set null')
    price = fields.Monetary(string="Price", currency_field='currency_id')
    sales_invoice = fields.Many2one('marathon.sales.invoice', string="Sales Invoice", ondelete='cascade')
    site = fields.Char(string="[Dep]Site")
    unit = fields.Char(string="Unit")
    # === END SF parity fields ===

    @api.depends('quantity', 'unit_price')
    def _compute_total(self):
        for it in self:
            it.line_total = (it.quantity or 0.0) * (it.unit_price or 0.0)


class MarathonSalesInvoiceTotal(models.Model):
    _name = 'marathon.sales.invoice.total'
    _description = 'Sales Invoice Total'

    invoice_id = fields.Many2one(
        'marathon.sales.invoice', string='Invoice', required=True,
        ondelete='cascade',
    )
    name = fields.Char(string='Total Type', default='Subtotal')
    amount = fields.Monetary(string='Amount', currency_field='currency_id')
    currency_id = fields.Many2one(
        'res.currency', related='invoice_id.currency_id', store=True, readonly=True,
    )
    sequence = fields.Integer(string='Sequence', default=10)

    # =================================================================== #
    # === SF parity fields (auto-generated, full Salesforce field set) === #
    # =================================================================== #
    absolute_value = fields.Monetary(string="Absolute Value", currency_field='currency_id')
    percent_value = fields.Float(string="Percent Value")
    sales_invoice = fields.Many2one('marathon.sales.invoice', string="Sales Invoice", ondelete='cascade')
    subtotal = fields.Monetary(string="[Dep]Subtotal", currency_field='currency_id')
    total = fields.Monetary(string="Total", currency_field='currency_id')
    # === END SF parity fields ===


class MarathonSalesInvoicePayment(models.Model):
    _name = 'marathon.sales.invoice.payment'
    _description = 'Sales Invoice Payment'
    _order = 'payment_date desc'

    invoice_id = fields.Many2one(
        'marathon.sales.invoice', string='Invoice', required=True,
        ondelete='cascade',
    )
    name = fields.Char(string='Reference', default=lambda self: _('Payment'))
    payment_date = fields.Date(
        string='Payment Date', default=fields.Date.context_today, required=True,
    )
    amount = fields.Monetary(
        string='Amount', currency_field='currency_id', required=True,
    )
    currency_id = fields.Many2one(
        'res.currency', related='invoice_id.currency_id', store=True, readonly=True,
    )
    payment_method = fields.Selection(
        [
            ('check', 'Check'),
            ('wire', 'Wire'),
            ('ach', 'ACH'),
            ('credit_card', 'Credit Card'),
            ('other', 'Other'),
        ],
        string='Method', default='check',
    )
    check_id = fields.Many2one('marathon.check', string='Check')
    notes = fields.Text(string='Notes')

    # =================================================================== #
    # === SF parity fields (auto-generated, full Salesforce field set) === #
    # =================================================================== #
    document_number = fields.Char(string="Document Number")
    payment_recordkey = fields.Char(string="Payment Recordkey")
    payment_type = fields.Char(string="Payment Type")
    posting_date = fields.Date(string="Posting Date")
    receipt_date = fields.Date(string="Receipt Date")
    sales_invoice = fields.Many2one('marathon.sales.invoice', string="Sales Invoice", ondelete='cascade')
    sf_date = fields.Date(string='Date')
    # === END SF parity fields ===

# -*- coding: utf-8 -*-
"""Salesforce Credit Memo (SFCM).

Created when a discrepancy is found on units that have already aired.
Per the SF training "salesforce-credit-memo": SFCMs help Finance and Ops
analyse why an error occurred and prevent recurrence. Required after
monthly invoicing has been reconciled.
"""

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class MarathonCreditMemo(models.Model):
    _name = 'marathon.credit.memo'
    _description = 'Salesforce Credit Memo'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='SFCM Number', required=True, copy=False, readonly=True,
        default=lambda self: _('New'), tracking=True,
    )

    # ---- Relationships ----
    deal_id = fields.Many2one(
        'marathon.deal', string='Deal', required=True, tracking=True,
        ondelete='restrict',
    )
    schedule_id = fields.Many2one(
        'marathon.schedule', string='Schedule', tracking=True,
        domain="[('deal_parent_id', '=', deal_id)]",
    )
    spot_data_id = fields.Many2one(
        'marathon.spot.data', string='Spot Data', tracking=True,
    )
    invoice_id = fields.Many2one(
        'marathon.sales.invoice', string='Invoice', tracking=True,
    )
    advertiser_id = fields.Many2one(
        'marathon.advertiser', string='Advertiser',
        related='deal_id.advertiser_id', store=True, readonly=True,
    )
    brand_id = fields.Many2one(
        'marathon.brand', string='Brand',
        related='deal_id.brand_id', store=True, readonly=True,
    )
    program_id = fields.Many2one(
        'marathon.program', string='Network',
        related='deal_id.program_id', store=True, readonly=True,
    )

    # ---- Type & reasoning ----
    credit_type = fields.Selection(
        [
            ('credit', 'Credit'),
            ('network_error', 'Network Error'),
            ('agency_discount', 'Agency Discount'),
            ('agency_discount_approved_by_network',
             'Agency Discount - Approved by Network'),
            ('network_performance', 'Network Performance'),
            ('bundles_credit', 'Bundles Credit'),
            ('bundles_performance', 'Bundles Performance'),
        ],
        string='Credit Type', required=True, tracking=True,
        help='Per SF training: Credit = Marathon entry error; Network '
             'Error = network discrepancy; Agency Discount = network paid '
             'favor (needs network approval email if network-approved); '
             'Network Performance = under-performance credit.',
    )
    requires_network_approval = fields.Boolean(
        string='Requires Network Approval',
        compute='_compute_requires_network_approval', store=True,
    )
    approval_email_attachment = fields.Binary(string='Approval Email')
    approval_email_filename = fields.Char(string='Approval Email Filename')

    # ---- Discrepancy details ----
    reason_text = fields.Text(
        string='Reason / Description', required=True, tracking=True,
        help='As detailed as possible: what error happened, when, why.',
    )
    discrepancy_date = fields.Date(string='Discrepancy Date')
    aired_date = fields.Date(string='Aired Date')
    units_count = fields.Integer(string='# Units', default=1)
    amount = fields.Monetary(
        string='Credit Amount', tracking=True, currency_field='currency_id',
    )
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id,
    )

    # ---- Workflow ----
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('submitted', 'Submitted'),
            ('approved', 'Approved'),
            ('applied', 'Applied'),
            ('rejected', 'Rejected'),
        ],
        string='Status', default='draft', tracking=True, copy=False,
    )
    requested_by_id = fields.Many2one(
        'res.users', string='Requested By',
        default=lambda self: self.env.user,
    )
    approver_id = fields.Many2one('res.users', string='Approver')
    approval_date = fields.Date(string='Approval Date')
    rejection_reason = fields.Text(string='Rejection Reason')

    # ---- Linked agency-discrepancy task ----
    agency_discrepancy_task_id = fields.Many2one(
        'marathon.agency.discrepancy.task', string='Agency Discrepancy Task',
    )

    @api.depends('credit_type')
    def _compute_requires_network_approval(self):
        for r in self:
            r.requires_network_approval = r.credit_type in (
                'agency_discount', 'agency_discount_approved_by_network',
            )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'marathon.credit.memo'
                ) or _('New')
        return super().create(vals_list)

    def action_submit(self):
        for r in self:
            if r.requires_network_approval and not r.approval_email_attachment:
                raise UserError(_(
                    'Credit type "%s" requires a network approval email '
                    'attached before submission.'
                ) % r.credit_type)
            if not r.reason_text or len(r.reason_text.strip()) < 20:
                raise UserError(_(
                    'Please provide a detailed reason (at least 20 chars).'
                ))
            r.state = 'submitted'

    def action_approve(self):
        for r in self:
            r.write({
                'state': 'approved',
                'approver_id': self.env.user.id,
                'approval_date': fields.Date.context_today(self),
            })

    def action_reject(self, reason=None):
        for r in self:
            r.write({
                'state': 'rejected',
                'rejection_reason': reason or r.rejection_reason,
            })

    def action_apply(self):
        for r in self:
            if r.state != 'approved':
                raise UserError(_('Credit memo must be approved before applying.'))
            r.state = 'applied'

    def action_reset_to_draft(self):
        self.write({'state': 'draft'})

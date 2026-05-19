# -*- coding: utf-8 -*-
"""Agency / Advertiser Credit Application workflow.

Per the SF training "credit-approval-process":
  1. Agency or AE submits signed application.
  2. Finance verifies signature, reviews lawyer markings.
  3. References (>=3, prefer Network > Media > Trade) are emailed.
  4. D&B and CreditSafe reports are pulled and attached.
  5. Credit limit is set & monitored monthly.
  6. If references aren't met or markings rejected by lawyer → CIA
     (Cash In Advance).
"""

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class MarathonCreditApplication(models.Model):
    _name = 'marathon.credit.application'
    _description = 'Credit Application'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='Reference', required=True, copy=False, readonly=True,
        default=lambda self: _('New'), tracking=True,
    )
    applicant_type = fields.Selection(
        [('agency', 'Agency'), ('advertiser', 'Advertiser')],
        string='Applicant Type', required=True, default='agency', tracking=True,
    )
    agency_id = fields.Many2one(
        'res.partner', string='Agency / Advertiser', required=True, tracking=True,
        ondelete='restrict',
    )
    ae_id = fields.Many2one('res.users', string='Account Executive', tracking=True)

    # ---- Application receipt ----
    application_received_date = fields.Date(
        string='Application Received', tracking=True,
    )
    is_signed = fields.Boolean(
        string='Last Page Signed', tracking=True,
        help='Per SF training: only signed applications are processed.',
    )
    has_markings = fields.Boolean(
        string='Has Markings / Edits',
        help='If true, in-house lawyer review is required before processing.',
    )
    lawyer_review_required = fields.Boolean(
        string='Lawyer Review Required',
        compute='_compute_lawyer_review_required', store=True,
    )
    lawyer_response = fields.Selection(
        [('pending', 'Pending'),
         ('approved', 'Approved'),
         ('rejected', 'Rejected')],
        string='Lawyer Response', default='pending', tracking=True,
    )
    application_attachment = fields.Binary(string='Signed Application')
    application_filename = fields.Char(string='Application Filename')

    # ---- References ----
    reference_ids = fields.One2many(
        'marathon.credit.application.reference', 'application_id',
        string='References',
    )
    reference_count = fields.Integer(
        string='# References', compute='_compute_reference_count',
    )
    references_responded = fields.Integer(
        string='# Responded', compute='_compute_reference_count',
    )

    # ---- Reports ----
    dnb_report = fields.Binary(string='D&B Report')
    dnb_report_filename = fields.Char(string='D&B Filename')
    credit_safe_report = fields.Binary(string='Credit Safe Report')
    credit_safe_report_filename = fields.Char(string='Credit Safe Filename')

    # ---- Outcome ----
    credit_limit_requested = fields.Monetary(
        string='Credit Limit Requested', currency_field='currency_id',
    )
    credit_limit_approved = fields.Monetary(
        string='Credit Limit Approved', currency_field='currency_id',
        tracking=True,
    )
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id,
    )

    # ---- Workflow ----
    state = fields.Selection(
        [
            ('new', 'New'),
            ('received', 'Received'),
            ('lawyer_review', 'Lawyer Review'),
            ('references_pending', 'References Pending'),
            ('reports_pending', 'Reports Pending'),
            ('approved', 'Approved'),
            ('cia', 'Cash In Advance'),
            ('declined', 'Declined'),
        ],
        string='Status', default='new', tracking=True, copy=False,
    )
    decision_notes = fields.Text(string='Decision Notes')
    decision_date = fields.Date(string='Decision Date')

    @api.depends('reference_ids', 'reference_ids.responded')
    def _compute_reference_count(self):
        for r in self:
            r.reference_count = len(r.reference_ids)
            r.references_responded = sum(1 for x in r.reference_ids if x.responded)

    @api.depends('has_markings')
    def _compute_lawyer_review_required(self):
        for r in self:
            r.lawyer_review_required = r.has_markings

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'marathon.credit.application'
                ) or _('New')
        return super().create(vals_list)

    # ---- Workflow actions ----
    def action_mark_received(self):
        for r in self:
            if not r.is_signed:
                raise UserError(_(
                    'Per SF training, the application must be signed on '
                    'the last page before processing.'
                ))
            r.state = 'lawyer_review' if r.lawyer_review_required else 'references_pending'
            r.application_received_date = fields.Date.context_today(self)

    def action_lawyer_approved(self):
        for r in self:
            r.lawyer_response = 'approved'
            r.state = 'references_pending'

    def action_lawyer_rejected(self):
        """Lawyer rejected the markings; Agency must sign as-is or be CIA."""
        for r in self:
            r.lawyer_response = 'rejected'
            # Pause workflow waiting for AE to talk to agency
            r.message_post(body=_(
                'Lawyer rejected markings. Communicate with AE/Agency. '
                'If Agency does not agree to sign as-is, mark as CIA.'
            ))

    def action_references_complete(self):
        for r in self:
            if r.references_responded < 3:
                raise UserError(_(
                    'Per SF training, MV requires at least 3 reference '
                    'responses before continuing. Currently: %d'
                ) % r.references_responded)
            r.state = 'reports_pending'

    def action_reports_complete(self):
        # D&B + Credit Safe optional per training but recommended
        self.write({'state': 'reports_pending'})

    def action_approve(self):
        for r in self:
            r.write({
                'state': 'approved',
                'decision_date': fields.Date.context_today(self),
            })
            # Push approved limit to the agency
            if r.agency_id and r.credit_limit_approved:
                r.agency_id.write({
                    'advertiser_credit_limit': r.credit_limit_approved,
                })

    def action_set_cia(self):
        for r in self:
            r.write({
                'state': 'cia',
                'decision_date': fields.Date.context_today(self),
            })
            if r.agency_id:
                r.agency_id.write({'cia_required': True})

    def action_decline(self):
        self.write({
            'state': 'declined',
            'decision_date': fields.Date.context_today(self),
        })


class MarathonCreditApplicationReference(models.Model):
    _name = 'marathon.credit.application.reference'
    _description = 'Credit Application Reference'
    _order = 'application_id, sequence'

    application_id = fields.Many2one(
        'marathon.credit.application', required=True, ondelete='cascade',
    )
    sequence = fields.Integer(default=10)
    contact_name = fields.Char(string='Contact Name', required=True)
    company_name = fields.Char(string='Company')
    email = fields.Char(string='Email')
    phone = fields.Char(string='Phone')
    reference_type = fields.Selection(
        [
            ('network', 'Network (Preferred)'),
            ('media', 'Media'),
            ('trade', 'Trade'),
        ],
        string='Type', default='network', required=True,
        help='MV prefers Network > Media > Trade. MV never uses bank refs.',
    )
    contacted_date = fields.Date(string='Contacted')
    responded = fields.Boolean(string='Responded')
    response_date = fields.Date(string='Response Date')
    response_notes = fields.Text(string='Response Notes')

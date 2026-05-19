# -*- coding: utf-8 -*-
"""New Advertiser / Brand Requests.

Per SF training "new-advertiser-brand-requests": when an AE wants to
add a new advertiser or brand, the request must be approved in
Salesforce and the New Advertiser Questionnaire sent to Finance.
"""

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class MarathonAdvertiserRequest(models.Model):
    _name = 'marathon.advertiser.request'
    _description = 'New Advertiser / Brand Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='Request #', required=True, copy=False, readonly=True,
        default=lambda self: _('New'),
    )
    request_kind = fields.Selection(
        [('advertiser', 'New Advertiser'), ('brand', 'New Brand')],
        string='Request Kind', required=True, default='advertiser', tracking=True,
    )
    requested_advertiser_name = fields.Char(
        string='Advertiser Name', required=True, tracking=True,
    )
    requested_brand_name = fields.Char(string='Brand Name', tracking=True)
    parent_advertiser_id = fields.Many2one(
        'marathon.advertiser', string='Parent Advertiser',
        help='If this is a Brand request, the parent Advertiser.',
    )
    similar_advertisers_checked = fields.Boolean(
        string='Confirmed No Duplicates',
        help='Per training: search SF first to ensure the advertiser does '
             'not already exist.',
    )
    similar_advertiser_notes = fields.Text(string='Similar Advertisers Found')

    # ---- Questionnaire ----
    ae_id = fields.Many2one('res.users', string='Marathon AE', required=True)
    agency_id = fields.Many2one('res.partner', string='Agency Representing', required=True)
    network_id = fields.Many2one('marathon.program', string='Network for Booking', required=True)
    questionnaire_html = fields.Html(string='Advertiser Questionnaire')
    questionnaire_attachment = fields.Binary(string='Questionnaire Attachment')
    questionnaire_filename = fields.Char(string='Questionnaire Filename')
    sent_to_finance_date = fields.Date(string='Sent to Finance')

    # ---- Workflow ----
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('pending_approval', 'Pending Approval'),
            ('finance_review', 'Finance Review'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ],
        string='Status', default='draft', tracking=True, copy=False,
    )
    approver_id = fields.Many2one('res.users', string='Approver')
    approval_date = fields.Date(string='Approval Date')
    rejection_reason = fields.Text(string='Rejection Reason')

    # ---- Outcome ----
    advertiser_id = fields.Many2one(
        'marathon.advertiser', string='Created Advertiser',
        help='Populated after approval when the actual record is created.',
    )
    brand_id = fields.Many2one(
        'marathon.brand', string='Created Brand',
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'marathon.advertiser.request'
                ) or _('New')
        return super().create(vals_list)

    def action_submit(self):
        for r in self:
            if not r.similar_advertisers_checked:
                raise UserError(_(
                    'Please confirm you searched for similar advertisers '
                    'before submitting (per SF training).'
                ))
            r.state = 'pending_approval'

    def action_send_to_finance(self):
        for r in self:
            if not r.questionnaire_attachment and not r.questionnaire_html:
                raise UserError(_(
                    'Please complete the New Advertiser Questionnaire '
                    'before sending to Finance.'
                ))
            r.write({
                'state': 'finance_review',
                'sent_to_finance_date': fields.Date.context_today(self),
            })

    def action_approve(self):
        for r in self:
            # Auto-create the actual records
            if r.request_kind == 'advertiser' and not r.advertiser_id:
                adv = self.env['marathon.advertiser'].create({
                    'name': r.requested_advertiser_name,
                })
                r.advertiser_id = adv.id
            if r.request_kind == 'brand' and not r.brand_id:
                if not r.parent_advertiser_id:
                    raise UserError(_(
                        'Brand requests need a parent advertiser.'
                    ))
                br = self.env['marathon.brand'].create({
                    'name': r.requested_brand_name or r.requested_advertiser_name,
                    'advertiser_id': r.parent_advertiser_id.id,
                })
                r.brand_id = br.id
            r.write({
                'state': 'approved',
                'approver_id': self.env.user.id,
                'approval_date': fields.Date.context_today(self),
            })

    def action_reject(self):
        self.write({'state': 'rejected'})

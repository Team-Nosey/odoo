# -*- coding: utf-8 -*-
"""Agency Discrepancy Task workflow.

Per SF training "agency-discrepancy-tasks":
  - Created by Finance when an invoice is underpaid
  - Assigned to the Planner
  - 48h SLA, weekly status updates expected
  - Resolves either by (a) Agency paying the remainder OR (b) a
    Salesforce Credit Memo being created
  - >30 days open → Finance escalates to Ops Management
"""

from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class MarathonAgencyDiscrepancyTask(models.Model):
    _name = 'marathon.agency.discrepancy.task'
    _description = 'Agency Discrepancy Task'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'due_date asc, create_date desc'

    name = fields.Char(
        string='Task Number', required=True, copy=False, readonly=True,
        default=lambda self: _('New'), tracking=True,
    )
    deal_id = fields.Many2one(
        'marathon.deal', string='Related Deal', required=True, tracking=True,
        ondelete='restrict',
    )
    invoice_id = fields.Many2one(
        'marathon.sales.invoice', string='Invoice', tracking=True,
    )
    agency_id = fields.Many2one(
        'res.partner', string='Agency',
        related='deal_id.client_account_id', store=True, readonly=True,
    )
    advertiser_id = fields.Many2one(
        'marathon.advertiser', string='Advertiser',
        related='deal_id.advertiser_id', store=True, readonly=True,
    )
    brand_id = fields.Many2one(
        'marathon.brand', string='Brand',
        related='deal_id.brand_id', store=True, readonly=True,
    )

    finance_creator_id = fields.Many2one(
        'res.users', string='Created By Finance',
        default=lambda self: self.env.user, tracking=True,
    )
    planner_id = fields.Many2one(
        'res.users', string='Assigned Planner', required=True, tracking=True,
    )
    associated_planner_id = fields.Many2one(
        'res.users', string='Re-assign To',
        help='Per SF training: if assigned to wrong Planner, fill this and '
             'notify the creator within 48h.',
    )

    # ---- Amount details ----
    invoice_total = fields.Monetary(
        string='Invoice Total', currency_field='currency_id',
    )
    paid_amount = fields.Monetary(
        string='Paid Amount', currency_field='currency_id',
    )
    short_paid_amount = fields.Monetary(
        string='Short Paid', currency_field='currency_id',
        compute='_compute_short_paid', store=True,
    )
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id,
    )

    # ---- Dates ----
    due_date = fields.Date(
        string='Due Date', tracking=True,
        default=lambda self: fields.Date.context_today(self) + timedelta(days=2),
        help='Default 48h SLA from creation per training.',
    )
    days_open = fields.Integer(
        string='Days Open', compute='_compute_days_open',
    )
    overdue = fields.Boolean(
        string='Overdue', compute='_compute_days_open',
    )
    escalated = fields.Boolean(
        string='Escalated', tracking=True,
        help='Auto-set when task has been open >30 days.',
    )

    # ---- Workflow ----
    state = fields.Selection(
        [
            ('new', 'New'),
            ('acknowledged', 'Acknowledged'),
            ('researching', 'Researching'),
            ('credit_memo_pending', 'SFCM Pending'),
            ('completed_paid', 'Completed - Paid by Agency'),
            ('completed_credited', 'Completed - SFCM Created'),
            ('cancelled', 'Cancelled'),
        ],
        string='Status', default='new', tracking=True, copy=False,
    )

    # ---- Resolution ----
    sfcm_id = fields.Many2one(
        'marathon.credit.memo', string='Salesforce Credit Memo',
    )
    finance_notified = fields.Boolean(string='Finance Notified', tracking=True)
    weekly_update_due = fields.Date(
        string='Next Update Due', compute='_compute_weekly_update_due',
        store=True,
    )

    finance_attachment = fields.Binary(string='Supporting Document')
    finance_attachment_filename = fields.Char(string='Attachment Filename')
    discrepancy_notes = fields.Text(
        string='Discrepancy Notes',
        help='Use the chatter for periodic updates; this captures the '
             'initial summary.',
    )

    @api.depends('invoice_total', 'paid_amount')
    def _compute_short_paid(self):
        for r in self:
            r.short_paid_amount = max(0.0, (r.invoice_total or 0.0) - (r.paid_amount or 0.0))

    @api.depends('create_date', 'state')
    def _compute_days_open(self):
        today = fields.Date.context_today(self)
        for r in self:
            if r.create_date and r.state not in (
                    'completed_paid', 'completed_credited', 'cancelled'):
                r.days_open = (today - r.create_date.date()).days
                r.overdue = bool(r.due_date and today > r.due_date)
            else:
                r.days_open = 0
                r.overdue = False

    @api.depends('create_date', 'state')
    def _compute_weekly_update_due(self):
        """Next-update-due = 7 days after the most recent activity.

        Per training: Finance reads chatter periodically and expects a
        weekly update. We anchor off the latest mail.message date if any,
        falling back to the record's create_date.
        """
        Message = self.env['mail.message']
        for r in self:
            if r.state in ('completed_paid', 'completed_credited', 'cancelled'):
                r.weekly_update_due = False
                continue
            base = r.create_date
            if r.id and isinstance(r.id, int):
                last = Message.search(
                    [('model', '=', r._name), ('res_id', '=', r.id)],
                    order='date desc', limit=1,
                )
                if last and last.date:
                    base = last.date
            r.weekly_update_due = (base + timedelta(days=7)).date() if base else False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'marathon.agency.discrepancy.task'
                ) or _('New')
        return super().create(vals_list)

    # ---- Workflow actions ----
    def action_acknowledge(self):
        self.write({'state': 'acknowledged'})
        for r in self:
            r.message_post(body=_('Task acknowledged. Beginning research.'))

    def action_start_research(self):
        self.write({'state': 'researching'})

    def action_pending_sfcm(self):
        self.write({'state': 'credit_memo_pending'})

    def action_complete_paid(self):
        for r in self:
            r.write({'state': 'completed_paid', 'finance_notified': True})
            r.message_post(body=_(
                'Agency agreed to pay remaining short pay. Finance notified.'
            ))

    def action_complete_credited(self):
        for r in self:
            if not r.sfcm_id:
                raise UserError(_(
                    'Attach the Salesforce Credit Memo before closing this '
                    'task as Credited.'
                ))
            r.write({'state': 'completed_credited', 'finance_notified': True})
            r.message_post(body=_(
                'SFCM %s attached. Finance notified.'
            ) % r.sfcm_id.name)

    def action_reassign(self):
        """Per training: re-assign to correct planner; notify task creator."""
        for r in self:
            if not r.associated_planner_id:
                raise UserError(_(
                    'Set "Re-assign To" first.'
                ))
            old = r.planner_id
            r.write({'planner_id': r.associated_planner_id.id,
                     'associated_planner_id': False})
            r.message_post(body=_(
                'Re-assigned from %s to %s. Notify Finance creator %s.'
            ) % (old.name, r.planner_id.name, r.finance_creator_id.name))

    @api.model
    def cron_escalate_old_tasks(self):
        """>30 days open → mark escalated and post note for Ops mgmt."""
        old = self.search([
            ('state', 'not in', (
                'completed_paid', 'completed_credited', 'cancelled')),
            ('escalated', '=', False),
        ])
        for r in old:
            if r.days_open and r.days_open > 30:
                r.write({'escalated': True})
                r.message_post(body=_(
                    'Task auto-escalated: open %d days. Ops Management '
                    'notified.'
                ) % r.days_open)

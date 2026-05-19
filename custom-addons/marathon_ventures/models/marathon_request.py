# -*- coding: utf-8 -*-
"""Marathon Request - the in-app equivalent of the Salesforce
'Requests' tab.

Per SF training "salesforce-requests": a generic ticket model used to
escalate help requests to Ops, Product, Finance, or Sales.
"""

from odoo import _, api, fields, models


class MarathonRequest(models.Model):
    _name = 'marathon.request'
    _description = 'Marathon Internal Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='Request Number', required=True, copy=False, readonly=True,
        default=lambda self: _('New'),
    )
    subject = fields.Char(string='Subject', required=True, tracking=True)
    description = fields.Html(string='Description', required=True)

    request_type = fields.Selection(
        [
            ('order_entry_help', 'Order Entry: Additional Help'),
            ('feature_request', 'New Feature Request'),
            ('training_request', 'Training Request'),
            ('deletion_by_product', 'Deletion by Product Team'),
            ('problem', 'Problem'),
            ('finance_inquiry', 'Finance Inquiry'),
            ('access_request', 'Access Request'),
            ('laptop_signout', 'Laptop Sign-Out'),
            ('other', 'Other'),
        ],
        string='Request Type', required=True, default='problem', tracking=True,
    )
    department = fields.Selection(
        [
            ('operations', 'Operations'),
            ('product', 'Product'),
            ('finance', 'Finance'),
            ('sales', 'Sales'),
        ],
        string='Department', required=True, default='operations', tracking=True,
        help='Per SF training: pick Operations if unsure; Ops will route '
             'to the correct team.',
    )
    laptop_number = fields.Char(
        string='Laptop Number',
        help='Required for laptop sign-out requests only.',
    )

    requester_id = fields.Many2one(
        'res.users', string='Requester',
        default=lambda self: self.env.user, tracking=True,
    )
    assignee_id = fields.Many2one('res.users', string='Assignee', tracking=True)
    state = fields.Selection(
        [
            ('new', 'New'),
            ('in_progress', 'In Progress'),
            ('blocked', 'Blocked'),
            ('resolved', 'Resolved'),
            ('cancelled', 'Cancelled'),
        ],
        string='Status', default='new', tracking=True, copy=False,
    )
    priority = fields.Selection(
        [('0', 'Normal'), ('1', 'High'), ('2', 'Urgent')],
        string='Priority', default='0', tracking=True,
    )
    due_date = fields.Date(string='Due Date')
    resolution_notes = fields.Text(string='Resolution Notes')
    resolved_date = fields.Datetime(string='Resolved Date')

    # Optional cross-references
    deal_id = fields.Many2one('marathon.deal', string='Related Deal')
    schedule_id = fields.Many2one('marathon.schedule', string='Related Schedule')
    program_id = fields.Many2one('marathon.program', string='Related Network')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'marathon.request'
                ) or _('New')
        return super().create(vals_list)

    def action_start(self):
        self.write({'state': 'in_progress', 'assignee_id': self.env.user.id})

    def action_block(self):
        self.write({'state': 'blocked'})

    def action_resolve(self):
        self.write({
            'state': 'resolved',
            'resolved_date': fields.Datetime.now(),
        })

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_reopen(self):
        self.write({'state': 'new', 'resolved_date': False})

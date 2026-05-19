# -*- coding: utf-8 -*-
"""Salesforce objects: ``Check__c`` and ``CheckDetail__c``.

A Check is the payment instrument; CheckDetail records the per-spot
breakdown of how a check applies against scheduled aired commercials.
"""

from odoo import api, fields, models, _


class MarathonCheck(models.Model):
    _name = 'marathon.check'
    _description = 'Check'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'check_date desc, check_number'
    _rec_name = 'check_number'

    check_number = fields.Char(string='Check Number', required=True, tracking=True)
    check_date = fields.Date(string='Check Date', tracking=True)
    program_id = fields.Many2one('marathon.program', string='Program', tracking=True)
    detail_ids = fields.One2many(
        'marathon.check.detail', 'check_id', string='Check Details',
    )
    total_dollars = fields.Monetary(
        string='Total Dollars', currency_field='currency_id',
        compute='_compute_totals', store=True,
    )
    matched_dollars = fields.Monetary(
        string='Matched Dollars', currency_field='currency_id',
        compute='_compute_totals', store=True,
    )
    unmatched_dollars = fields.Monetary(
        string='Unmatched Dollars', currency_field='currency_id',
        compute='_compute_totals', store=True,
    )
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id,
    )
    _check_number_unique = models.Constraint(
        'UNIQUE(check_number)',
        'Check Number must be unique.',
    )

    @api.depends('detail_ids.net_amount', 'detail_ids.unmatched')
    def _compute_totals(self):
        for c in self:
            c.total_dollars = sum(c.detail_ids.mapped('net_amount') or [0.0])
            matched = c.detail_ids.filtered(lambda d: not d.unmatched)
            unmatched = c.detail_ids.filtered(lambda d: d.unmatched)
            c.matched_dollars = sum(matched.mapped('net_amount') or [0.0])
            c.unmatched_dollars = sum(unmatched.mapped('net_amount') or [0.0])


class MarathonCheckDetail(models.Model):
    _name = 'marathon.check.detail'
    _description = 'Check Detail'
    _order = 'check_id, air_date'

    check_id = fields.Many2one(
        'marathon.check', string='Check', required=True, ondelete='cascade',
    )
    schedule_id = fields.Many2one('marathon.schedule', string='Schedule')
    air_date = fields.Date(string='Air Date')
    air_time = fields.Char(string='Air Time')
    item_ad_id = fields.Char(string='Item Ad ID')
    check_amount = fields.Monetary(
        string='Check Amount', currency_field='currency_id',
    )
    debit_check = fields.Char(string='Debit Check')
    debit_date = fields.Date(string='Debit Date')
    net_amount = fields.Monetary(
        string='Net Amount', currency_field='currency_id',
        compute='_compute_net_amount', store=True,
    )
    unmatched = fields.Boolean(string='Unmatched')
    unmatched_reason = fields.Selection(
        [('No matching week/long form Schedule', 'No matching week/long form Schedule'), ('Mismatched rate on Schedule', 'Mismatched rate on Schedule'), ('Mismatched traffic on Schedule', 'Mismatched traffic on Schedule'), ('Duplicate Schedules', 'Duplicate Schedules'), ('Schedule only exists for Non-Havas DealAccount.', 'Schedule only exists for Non-Havas DealAccount.')],
        string='Unmatched Reason',
    )
    currency_id = fields.Many2one(
        'res.currency', related='check_id.currency_id', store=True, readonly=True,
    )

    @api.depends('check_amount', 'unmatched')
    def _compute_net_amount(self):
        for d in self:
            d.net_amount = (d.check_amount or 0.0) if not d.unmatched else 0.0

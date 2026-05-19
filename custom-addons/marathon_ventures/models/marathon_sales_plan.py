# -*- coding: utf-8 -*-
"""Salesforce object: ``Sales_Plan__c``."""

from odoo import fields, models


class MarathonSalesPlan(models.Model):
    _name = 'marathon.sales.plan'
    _description = 'Sales Plan'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Sales Plan Name', required=True, tracking=True)
    description = fields.Text(string='Description')
    advertiser_id = fields.Many2one(
        'marathon.advertiser', string='Advertiser', tracking=True,
    )
    brand_id = fields.Many2one(
        'marathon.brand', string='Brand', tracking=True, required=True)
    program_id = fields.Many2one(
        'marathon.program', string='Program', tracking=True,
    )
    quarter = fields.Selection(
        [('q1', 'Q1'), ('q2', 'Q2'), ('q3', 'Q3'), ('q4', 'Q4')],
        string='Quarter',
    )
    year = fields.Integer(string='Year')
    total_budget = fields.Monetary(
        string='Total Budget', currency_field='currency_id',
    )
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id,
    )
    status = fields.Selection(
        [('In Process', 'In Process'), ('Sold', 'Sold')],
        string='Status',
        default='In Process',
        tracking=True,
    )

    # =================================================================== #
    # === SF parity fields (auto-generated, full Salesforce field set) === #
    # =================================================================== #
    contact = fields.Many2one('res.partner', string="Contact", ondelete='set null')
    measurement_type = fields.Selection([('Nielsen + Big Data', 'Nielsen + Big Data'), ('Nielsen + Panel', 'Nielsen + Panel'), ('Video Amp', 'Video Amp'), ('Other', 'Other')], string="Measurement Type")
    primary_demographic = fields.Selection([('A18+', 'A18+'), ('A18-34', 'A18-34'), ('A18-49', 'A18-49'), ('A18-54', 'A18-54'), ('A2+', 'A2+'), ('A25+', 'A25+'), ('A25-34', 'A25-34'), ('A25-49', 'A25-49'), ('A25-54', 'A25-54'), ('A25-64', 'A25-64'), ('A35+', 'A35+'), ('A35-54', 'A35-54'), ('A35-64', 'A35-64'), ('A45+', 'A45+'), ('A45-64', 'A45-64'), ('A50+', 'A50+'), ('A55+', 'A55+'), ('A65+', 'A65+'), ('HH', 'HH'), ('M18+', 'M18+'), ('M18-34', 'M18-34'), ('M18-49', 'M18-49'), ('M2+', 'M2+'), ('M25+', 'M25+'), ('M25-34', 'M25-34'), ('M25-49', 'M25-49'), ('M25-54', 'M25-54'), ('M25-64', 'M25-64'), ('M35+', 'M35+'), ('M35-54', 'M35-54'), ('M35-64', 'M35-64'), ('M45+', 'M45+'), ('M45-64', 'M45-64'), ('M50+', 'M50+'), ('M55+', 'M55+'), ('M65+', 'M65+'), ('W18+', 'W18+'), ('W18-34', 'W18-34'), ('W18-49', 'W18-49'), ('W2+', 'W2+'), ('W25+', 'W25+'), ('W25-34', 'W25-34'), ('W25-49', 'W25-49'), ('W25-54', 'W25-54'), ('W25-64', 'W25-64'), ('W35+', 'W35+'), ('W35-54', 'W35-54'), ('W35-64', 'W35-64'), ('W45+', 'W45+'), ('W45-64', 'W45-64'), ('W50+', 'W50+'), ('W55+', 'W55+'), ('W65+', 'W65+'), ('W18-64', 'W18-64')], string="Primary Demographic")
    season = fields.Selection([('22/23', '22/23'), ('23/24', '23/24'), ('24/25', '24/25'), ('25/26', '25/26')], string="Season", required=True)
    upfront_scatter = fields.Selection([('Upfront', 'Upfront'), ('Scatter', 'Scatter')], string="Upfront/Scatter", required=True)
    # === END SF parity fields ===

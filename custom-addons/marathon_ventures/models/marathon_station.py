# -*- coding: utf-8 -*-
"""Salesforce object: ``Station__c`` — a TV broadcast station."""

from odoo import fields, models


class MarathonStation(models.Model):
    _name = 'marathon.station'
    _description = 'Station'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(
        string='Station Name', required=True, tracking=True,
        help='Standard SF Name field.',
    )
    call_letters = fields.Char(string='Call Letters', tracking=True, required=True)
    network_id = fields.Many2one(
        'marathon.program', string='Network / Program', tracking=True,
    )
    market = fields.Char(string='Market')
    timezone = fields.Selection(
        [
            ('ET', 'Eastern'),
            ('CT', 'Central'),
            ('MT', 'Mountain'),
            ('PT', 'Pacific'),
            ('AKT', 'Alaska'),
            ('HT', 'Hawaii'),
        ],
        string='Time Zone',
    )
    active = fields.Boolean(string='Active', default=True)
    notes = fields.Text(string='Notes')

    # =================================================================== #
    # === SF parity fields (auto-generated, full Salesforce field set) === #
    # =================================================================== #
    active_station = fields.Boolean(string="Active Station", default=False)
    affiliate_owner = fields.Selection([('Gray', 'Gray'), ('Gannett', 'Gannett'), ('PMCM TV, LLC', 'PMCM TV, LLC'), ('Tribune', 'Tribune'), ('Raycom', 'Raycom'), ('Media General', 'Media General'), ('Hearst', 'Hearst'), ('Tegna', 'Tegna'), ('American Spirit', 'American Spirit'), ('Univision', 'Univision'), ('Scripps', 'Scripps')], string="Affiliate Owner")
    affiliate = fields.Char(string="Affiliate")
    group_owner = fields.Many2one('res.partner', string="Group Owner", ondelete='set null')
    nielsen = fields.Char(string="Nielsen Call Letters")
    owner_call_letters = fields.Char(string="Owner Call Letters")
    rank = fields.Integer(string="Market Rank")
    station_affiliate = fields.Many2one('marathon.program', string="Station Affiliate", ondelete='set null')
    station_count = fields.Integer(string="Station Count")
    # === END SF parity fields ===

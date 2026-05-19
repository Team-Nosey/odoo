# -*- coding: utf-8 -*-
"""Salesforce objects: ``Traffic__c`` and ``Traffic_Video_Asset__c``."""

from odoo import fields, models


class MarathonTraffic(models.Model):
    _name = 'marathon.traffic'
    _description = 'Traffic'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Traffic Name', required=True, tracking=True)
    deal_id = fields.Many2one('marathon.deal', string='Deal', tracking=True)
    schedule_id = fields.Many2one('marathon.schedule', string='Schedule')
    advertiser_id = fields.Many2one(
        'marathon.advertiser', string='Advertiser',
        related='deal_id.advertiser_id', store=True, readonly=True,
    )
    brand_id = fields.Many2one(
        'marathon.brand', string='Brand',
        related='deal_id.brand_id', store=True, readonly=True,
    )

    isci = fields.Char(string='ISCI')
    rotation = fields.Char(string='Rotation')
    creative_title = fields.Char(string='Creative Title')
    length = fields.Selection(
        [('15', '15'), ('20', '20'), ('30', '30'), ('45', '45'), ('60', '60'), ('90', '90'), ('120', '120'), ('150', '150'), ('180', '180'), ('240', '240'), ('300', '300'), ('1710', '1710')],
        string='Length',
    )

    received_date = fields.Date(string='Received Date')
    delivery_date = fields.Date(string='Delivery Date')
    state = fields.Selection(
        [
            ('pending', 'Pending'),
            ('received', 'Received'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
            ('delivered', 'Delivered to Network'),
        ],
        string='State', default='pending', tracking=True,
    )

    video_asset_ids = fields.One2many(
        'marathon.traffic.video.asset', 'traffic_id', string='Video Assets',
    )
    video_file_id = fields.Many2one('marathon.video.file', string='Primary Video File')
    notes = fields.Text(string='Notes')

    # =================================================================== #
    # === SF parity fields (auto-generated, full Salesforce field set) === #
    # =================================================================== #
    access_code = fields.Char(string="Access Code")
    agency = fields.Many2one('res.partner', string="Agency", required=True, ondelete='restrict')
    brands = fields.Many2one('marathon.brand', string="Brands", required=True, ondelete='restrict')
    campaign = fields.Char(string="Campaign")
    client_code = fields.Char(string="Client Code")
    end_date = fields.Float(string="End Date")
    estimate = fields.Char(string="Estimate")
    hiatused_dates = fields.Char(string="Hiatused Dates")
    product_code = fields.Char(string="Product Code")
    product_description = fields.Char(string="Product Description")
    program = fields.Many2one('marathon.program', string="Program", ondelete='set null')
    quarter = fields.Integer(string="Quarter")
    start_date = fields.Float(string="Start Date")
    traffic_contact = fields.Many2one('res.partner', string="Traffic Contact", ondelete='set null')
    year = fields.Char(string="Year")
    # === END SF parity fields ===


class MarathonTrafficVideoAsset(models.Model):
    """``Traffic_Video_Asset__c`` is a junction object linking a Traffic
    record with one or more Video Files (Many-to-Many relationship)."""

    _name = 'marathon.traffic.video.asset'
    _description = 'Traffic Video Asset'
    _order = 'traffic_id, sequence'

    traffic_id = fields.Many2one(
        'marathon.traffic', string='Traffic', required=True, ondelete='cascade',
    )
    video_file_id = fields.Many2one(
        'marathon.video.file', string='Video File', required=True,
        ondelete='restrict',
    )
    sequence = fields.Integer(string='Sequence', default=10)
    is_primary = fields.Boolean(string='Primary Asset')
    notes = fields.Char(string='Notes')

    # =================================================================== #
    # === SF parity fields (auto-generated, full Salesforce field set) === #
    # =================================================================== #
    deal = fields.Many2one('marathon.deal', string="Deal", ondelete='set null')
    video_asset = fields.Many2one('marathon.video.file', string="Video Asset", ondelete='set null')
    advertiser = fields.Char(string='Advertiser')
    # === END SF parity fields ===

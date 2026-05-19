# -*- coding: utf-8 -*-
"""Salesforce object: ``Video_File__c``."""

from odoo import fields, models


class MarathonVideoFile(models.Model):
    _name = 'marathon.video.file'
    _description = 'Video File'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='File Name', required=True, tracking=True)
    isci = fields.Char(string='ISCI', tracking=True, required=True)
    title = fields.Char(string='Title')
    length = fields.Selection(
        [('15', '15'), ('20', '20'), ('30', '30'), ('45', '45'), ('60', '60'), ('90', '90'), ('120', '120'), ('150', '150'), ('180', '180'), ('240', '240'), ('300', '300'), ('1710', '1710')],
        string='Length',
    )
    file_url = fields.Char(string='File URL')
    file_attachment = fields.Binary(string='Video File')
    file_size_mb = fields.Float(string='File Size (MB)')
    advertiser_id = fields.Many2one('marathon.advertiser', string='Advertiser')
    brand_id = fields.Many2one('marathon.brand', string='Brand')
    upload_date = fields.Datetime(string='Upload Date')
    is_active = fields.Boolean(string='Active', default=True)
    notes = fields.Text(string='Notes')

    # =================================================================== #
    # === SF parity fields (auto-generated, full Salesforce field set) === #
    # =================================================================== #
    account = fields.Char(string="Account")
    file_name = fields.Char(string="File Name (SF)")
    file_path = fields.Char(string="File Path")
    isci_no_char = fields.Char(string="ISCI No Char")
    unique_ref_id = fields.Char(string="Unique Ref-ID")
    x800_number = fields.Char(string="800 Number")
    sf_advertiser_text = fields.Char(string='Advertiser (SF Text)')
    sf_brand_text = fields.Char(string='Brand (SF Text)')
    # === END SF parity fields ===

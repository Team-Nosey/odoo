# -*- coding: utf-8 -*-
"""Phase 9 - Schedule UI helpers.

Mirrors the Deal redesign: related read-only fields for the Key Schedule
Facts ribbon (account / advertiser / brand / length / order number pulled
through deal_parent) plus the stored related Program used by the
Targeting row and dashboards.
"""
from odoo import models, fields


class MvScheduleUiPhase9(models.Model):
    _name = 'mv.schedules'
    _inherit = 'mv.schedules'

    # Program - related Many2one through deal_parent.program. Lets the
    # Targeting section show Network / Daypart / Program in one row
    # without forcing the planner to open the Deal record to see which
    # program the schedule belongs to.
    program = fields.Many2one(
        related='deal_parent.program',
        string='Program',
        store=True,
        readonly=True,
    )

    # Key Schedule Facts ribbon - read-only mirrors pulled through the
    # parent Deal, matching the Deal form's Key Deal Facts ribbon.
    kf_account = fields.Char(
        related='deal_parent.contactaccount', string='Account', readonly=True)
    kf_advertiser = fields.Char(
        related='deal_parent.advertiser', string='Advertiser', readonly=True)
    kf_brands = fields.Many2one(
        related='deal_parent.brands', string='Brands', readonly=True)
    kf_length = fields.Selection(
        related='deal_parent.length', string='Length', readonly=True)
    kf_order_number = fields.Char(
        related='deal_parent.network_deal_number', string='Order Number',
        readonly=True)

    # NOTE: action_cancel_schedule was previously overridden here to
    # redirect to the schedules list view. That override completely
    # masked phase1_schedule.action_cancel_schedule which actually
    # flips status -> 'canceled'. Removing the override so clicking
    # the "Cancel Schedule" button cancels the record in place; the
    # user stays on the form and sees the status change to Canceled.

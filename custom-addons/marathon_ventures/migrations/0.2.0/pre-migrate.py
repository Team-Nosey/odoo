# -*- coding: utf-8 -*-
"""Pre-migration: map legacy lowercase status values to SF-aligned ones.

The marathon.deal.status field used to use Odoo-style lowercase keys
(draft / pending / booked / on_air / completed / cancelled). It now uses
the exact Salesforce picklist values (Budget / Sold / Historical /
Canceled) per the SF parity work.

Existing rows still hold the old values, which Odoo refuses to load
because they are no longer in the Selection list. This script rewrites
them in-place before the Selection is re-validated.
"""

DEAL_STATUS_MAP = {
    'draft':     'Budget',
    'pending':   'Budget',
    'booked':    'Sold',
    'on_air':    'Sold',
    'completed': 'Historical',
    'cancelled': 'Canceled',
}

SALES_PLAN_STATUS_MAP = {
    'draft':  'In Process',
    'active': 'In Process',
    'closed': 'Sold',
}

SALES_PLAN_SEASON_MAP = {
    '22_23': '22/23',
    '23_24': '23/24',
    '24_25': '24/25',
    '25_26': '25/26',
}

SALES_PLAN_UPFRONT_MAP = {
    'scatter': 'Scatter',
    'upfront': 'Upfront',
}

BRAND_APPROVAL_MAP = {
    'approved':     'Approved',
    'pending':      'Pending',
    'on_hold':      'Pending',
    'not_approved': 'Rejected',
}

DEAL_QUARTER_MAP = {'q1': 'Q1', 'q2': 'Q2', 'q3': 'Q3', 'q4': 'Q4'}
DEAL_TIER_MAP = {'a': '1', 'b': '2', 'c': '3'}


def _remap(cr, table, column, mapping):
    """Run a series of UPDATEs to remap values in a column."""
    for old, new in mapping.items():
        try:
            cr.execute(
                f'UPDATE "{table}" SET "{column}" = %s WHERE "{column}" = %s',
                (new, old),
            )
        except Exception:
            cr.rollback()
            # Column may not exist on this DB — ignore.


def migrate(cr, version):
    if not version:
        return

    # marathon.deal — status, quarter, tier
    _remap(cr, 'marathon_deal', 'status',  DEAL_STATUS_MAP)
    _remap(cr, 'marathon_deal', 'quarter', DEAL_QUARTER_MAP)
    _remap(cr, 'marathon_deal', 'tier',    DEAL_TIER_MAP)

    # marathon.sales.plan — status, season, upfront_scatter
    _remap(cr, 'marathon_sales_plan', 'status',          SALES_PLAN_STATUS_MAP)
    _remap(cr, 'marathon_sales_plan', 'season',          SALES_PLAN_SEASON_MAP)
    _remap(cr, 'marathon_sales_plan', 'upfront_scatter', SALES_PLAN_UPFRONT_MAP)

    # marathon.brand — approval_status, approved_duplicate
    _remap(cr, 'marathon_brand', 'approval_status',    BRAND_APPROVAL_MAP)
    _remap(cr, 'marathon_brand', 'approved_duplicate', BRAND_APPROVAL_MAP)

    # res.partner — account_type, agency_status, duplicate_approval, lead_type, call_cycle
    cr.execute("""
        UPDATE res_partner SET account_type = INITCAP(account_type)
         WHERE account_type IN ('agency','employee','network','vendor')
    """)
    cr.execute("""
        UPDATE res_partner SET agency_status = INITCAP(agency_status)
         WHERE agency_status IN ('active','hold','inactive')
    """)
    cr.execute("""
        UPDATE res_partner
           SET duplicate_approval = CASE duplicate_approval
                 WHEN 'approved'     THEN 'Approved'
                 WHEN 'not_approved' THEN 'Not Approved'
                 ELSE duplicate_approval END
         WHERE duplicate_approval IN ('approved','not_approved')
    """)
    cr.execute("""
        UPDATE res_partner
           SET lead_type = CASE lead_type
                 WHEN 'active'     THEN 'Active'
                 WHEN 'fallow'     THEN 'Fallow'
                 WHEN 'not_target' THEN 'Not Target'
                 WHEN 'target'     THEN 'Target'
                 ELSE lead_type END
         WHERE lead_type IN ('active','fallow','not_target','target')
    """)
    cr.execute("""
        UPDATE res_partner SET call_cycle = 'Fallow'
         WHERE call_cycle = 'fallow'
    """)

    # marathon.spot.data + .mirror — status was re-cased
    _remap(cr, 'marathon_spot_data', 'status', {
        'aired': 'Aired', 'credited': 'Credited',
        'credited_partial': 'Credited - Partial',
    })
    _remap(cr, 'marathon_spot_data_mirror', 'status', {
        'aired': 'Aired', 'discrepancy': 'Discrepancy',
        'credited': 'Credited', 'discrepancy_paid': 'Discrepancy - Paid',
    })

    # marathon.station — affiliate_owner re-cased
    _remap(cr, 'marathon_station', 'affiliate_owner', {
        'gray': 'Gray', 'gannett': 'Gannett', 'pmcm_tv_llc': 'PMCM TV, LLC',
        'tribune': 'Tribune', 'raycom': 'Raycom', 'media_general': 'Media General',
        'hearst': 'Hearst', 'tegna': 'Tegna', 'american_spirit': 'American Spirit',
        'univision': 'Univision', 'scripps': 'Scripps',
    })

    # marathon.advertiser — commercial / duplicate_approval re-cased
    _remap(cr, 'marathon_advertiser', 'commercial', {
        'dr':'DR','gm':'GM','hybrid':'HYBRID','psa':'PSA','end':'END',
        'promo':'PROMO','political':'POLITICAL','tune_in':'TUNE IN','na':'--',
    })
    _remap(cr, 'marathon_advertiser', 'duplicate_approval', {
        'approved':'Approved','not_approved':'Not Approved','pending':'Approved',
    })

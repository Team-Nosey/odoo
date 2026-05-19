# -*- coding: utf-8 -*-
{
    'name': "Marathon Ventures",
    'summary': "Media & broadcast advertising sales — Salesforce parity",
    'description': """
Marathon Ventures
=================
Custom module replicating the Marathon Ventures Salesforce org for media
& broadcast advertising sales. Provides Programs (Networks), Stations,
Advertisers, Brands, Deals, Schedules, Sales Quotes/Orders/Invoices,
Spot Data, Prelog Data, Traffic, Checks, and the Deal Revisions
workflow (LTC, Rate, Extend, Frequency, Test, Cap, Daypart, Hiatus,
Max Per Day).
    """,
    'author': "Marathon Ventures",
    'website': "https://www.mvmediasales.com",
    'category': 'Sales',
    'version': '0.2.0',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'contacts',
        'sale_management',
        'crm',
        'account',
    ],
    'data': [
        'security/marathon_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/marathon_demo_data.xml',
        'views/res_partner_views.xml',
        'views/marathon_station_views.xml',
        'views/marathon_program_views.xml',
        'views/marathon_advertiser_views.xml',
        'views/marathon_brand_views.xml',
        'views/marathon_sales_plan_views.xml',
        'views/marathon_deal_views.xml',
        'views/marathon_schedule_views.xml',
        'views/marathon_split_views.xml',
        'views/marathon_sales_quote_views.xml',
        'views/marathon_sales_order_views.xml',
        'views/marathon_sales_invoice_views.xml',
        'views/marathon_check_views.xml',
        'views/marathon_spot_data_views.xml',
        'views/marathon_prelog_data_views.xml',
        'views/marathon_working_log_views.xml',
        'views/marathon_traffic_views.xml',
        'views/marathon_video_file_views.xml',
        'views/marathon_knowledge_views.xml',
        'views/marathon_credit_memo_views.xml',
        'views/marathon_credit_application_views.xml',
        'views/marathon_agency_discrepancy_task_views.xml',
        'views/marathon_request_views.xml',
        'views/marathon_advertiser_request_views.xml',
        'wizard/deal_revision_wizard_views.xml',
        'views/marathon_menus.xml',
        'data/marathon_knowledge_data.xml',
    ],
    'application': True,
    'installable': True
}

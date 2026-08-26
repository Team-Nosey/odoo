# -*- coding: utf-8 -*-
{
    "name": "Prelog Conductor",
    "summary": "Prepare contact-specific Short Form prelog workbooks and emails.",
    "version": "19.0.1.1.0",
    "license": "LGPL-3",
    "author": "Marathon Ventures",
    "category": "Operations",
    "depends": ["marathon_ventures", "mail"],
    "external_dependencies": {"python": ["openpyxl"]},
    "data": [
        "security/ir.model.access.csv",
        "data/prelog_conductor_sequence.xml",
        "data/prelog_conductor_cron.xml",
        "views/prelog_conductor_wizard_views.xml",
        "views/prelog_conductor_batch_views.xml",
        "views/prelog_conductor_menus.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}

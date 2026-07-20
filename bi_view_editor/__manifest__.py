# -*- coding: utf-8 -*-

{
    "name": "BI View Editor",
    "author": "IVIS",
    "website": "https://www.intelliVersal.com",
    "support": "info@intelliVersal.com",
    "category": "Employees",
    "summary": "Graphical BI views builder for Odoo",
    "description": """Graphical BI views builder for Odoo""",
    "version": "18.0",
    "depends": ["spreadsheet_dashboard"],
    "external_dependencies": {
        "deb": ["graphviz"],
        "python": ["pydot"],
    },
    "data": [
        "security/res_groups.xml",
        "security/ir.model.access.csv",
        "security/rules.xml",
        "views/bve_view.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "bi_view_editor/static/src/components/**/*",
        ],
    },
    "uninstall_hook": "uninstall_hook",
    "images": [],
    "price": 4000000,
    "currency": "EUR",
    "license": "OPL-1",
    "application": False,
    "auto_install": False,
    "installable": True,
}

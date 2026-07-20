# -*- coding: utf-8 -*-

{
    "name": "Base Report XLSX",
    "author": "IVIS",
    "website": "https://www.intelliVersal.com",
    "support": "info@intelliVersal.com",
    "category": "Reporting",
    "summary": "Base Module to create XLSX Report",
    "description": """Base Module to create XLSX Report""",
    "version": "18.0",
    "depends": [],
    "external_dependencies": {"python": ["xlsxwriter", "xlrd"]},
    "data": [],
    "assets": {
        "web.assets_backend": [
            "report_xlsx/static/src/js/report/action_manager_report.esm.js",
        ],
    },
    "images": [],
    "price": 4000000,
    "currency": "EUR",
    "license": "OPL-1",
    "application": False,
    "auto_install": False,
    "installable": True,
}
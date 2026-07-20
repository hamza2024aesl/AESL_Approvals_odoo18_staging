# -*- coding: utf-8 -*-

{
    "name": "IVIS PF Interest Distribution",
    "author": "IVIS",
    "website": "https://www.intelliVersal.com",
    "support": "info@intelliVersal.com",
    "category": "Employee",
    "summary": "PF Distribution",
    "description": """PF Distribution""",
    "version": "18.0",
    "depends": ['hr', 'hr_payroll'],
    "data": [
        'security/ir.model.access.csv',
        'views/hr_employee_views.xml',
        'views/interest_distribution_views.xml',
    ],
    "images": [],
    "price": 4000000,
    "currency": "EUR",
    "license": "OPL-1",
    "application": False,
    "auto_install": False,
    "installable": True,
}

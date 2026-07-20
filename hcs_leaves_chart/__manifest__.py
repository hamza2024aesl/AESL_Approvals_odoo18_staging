# -*- coding: utf-8 -*-

{
    "name": "Employees Leaves Chart",
    "author": "IVIS",
    "website": "https://www.intelliVersal.com",
    "support": "info@intelliVersal.com",
    "category": "Leaves",
    "summary": "Employees Leaves Chart",
    "description": """Employees Leaves Chart""",
    "version": "18.0",
    "depends": ['hr', 'hr_attendance', 'hr_contract', 'hr_holidays', 'hr_payroll', 'ivis_leaves_enhancement'],
    "data": [
        'security/ir.model.access.csv',
        'views/views.xml',
        # 'views/templates.xml',
        'views/hr_leave_request.xml',
    ],
    "images": [],
    "price": 4000000,
    "currency": "EUR",
    "license": "OPL-1",
    "application": False,
    "auto_install": False,
    "installable": True,
}

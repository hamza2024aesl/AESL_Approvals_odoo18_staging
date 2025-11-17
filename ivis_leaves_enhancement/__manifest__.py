# -*- coding: utf-8 -*-

{
    "name": "Leaves Enhancement",
    "author": "IVIS",
    "website": "https://www.intelliVersal.com",
    "support": "info@intelliVersal.com",
    'category': 'Employees',
    "summary": "Employee Leaves Enhancement",
    "description": """Employee Leaves Enhancement""",
    "version": "18.0",
    "depends": ['hr', 'hr_attendance', 'hr_contract', 'hr_holidays', 'hr_payroll', 'ivis_attendance', 'hr_work_entry'],
    'data': [
        'data/scheduled_actions.xml',
        'wizard/monthly_timesheet_report_views.xml',
        'report/report_timesheet_template.xml',
        'report/ir_actions_report.xml',
        'views/hr_leave_type_views.xml',
        'views/hr_leave_views.xml',
    ],
    "images": [],
    "price": 4000000,
    "currency": "EUR",
    "license": "OPL-1",
    "application": False,
    "auto_install": False,
    "installable": True,
}

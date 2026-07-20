# -*- coding: utf-8 -*-

{
    "name": "GA Attendance",
    "author": "IVIS",
    "website": "https://www.intelliVersal.com",
    "support": "info@intelliVersal.com",
    "category": "Employees",
    "summary": "Manage Employee Attendance",
    "description": """Manage Employee Attendance""",
    "version": "18.0",
    "depends": ['hr_attendance', 'hr_payroll', 'ga_payroll_functions'],
    "data": [
        'views/wizard_one_view.xml',
        'views/request_view.xml',
        'views/working_schedules_view.xml',
        'views/machine_data_view.xml',
        'views/hr_attendance_view.xml',
        'views/holiday_schedule_view.xml',
        'security/ir.model.access.csv',
        'cron_task/process_attendance.xml'
    ],
    "images": [],
    "price": 4000000,
    "currency": "EUR",
    "license": "OPL-1",
    "application": False,
    "auto_install": False,
    "installable": True,
}

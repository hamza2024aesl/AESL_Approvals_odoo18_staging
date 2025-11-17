# -*- coding: utf-8 -*-

{
    "name": "Biometric Device Integration",
    "author": "IVIS",
    "website": "https://www.intelliVersal.com",
    "support": "info@intelliVersal.com",
    "category": "Attendance",
    "summary": "",
    "description": """""",
    "version": "18.0",
    'depends': ['base_setup', 'hr_attendance'],
    "data": [
        'security/ir.model.access.csv',
        'views/zk_machine_view.xml',
        'views/zk_machine_attendance_view.xml',
        'data/download_data.xml'
    ],
    "images": [],
    "price": 4000000,
    "currency": "EUR",
    "license": "OPL-1",
    "application": False,
    "auto_install": False,
    "installable": True,
}
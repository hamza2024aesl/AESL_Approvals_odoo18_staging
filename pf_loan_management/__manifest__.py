# -*- coding: utf-8 -*-
{
    'name': 'PF Loan Management',
    'version': '18.0.1.0.0',
    'summary': 'Provident Fund Loan Management & Sequential Approval Workflow',
    'author': 'PRODO',
    'website': 'https://www.prodo.pk',
    'category': 'Human Resources',
    'depends': ['base', 'hr', 'account', 'ivis_hr_employee_loan'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'wizard/pf_loan_voucher_wizard_views.xml',
        'views/pf_loan_config_views.xml',
        'views/pf_loan_application_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'OPL-1',
}

# -*- coding: utf-8 -*-
{
    'name': 'Approval Extension',
    'version': '1.0',
    'category': 'Approvals',
    'summary': 'Extension for Approvals module',
    'description': """
        Custom configuration menus for Approvals.
    """,
    'author': 'AESL',
    'depends': ['approvals', 'hr', 'hr_holidays'],
    'data': [
        'security/ir.model.access.csv',
        'views/approval_domestic_views.xml',
        'views/approval_menus.xml',
        'views/approval_request_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}

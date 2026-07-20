# -*- coding: utf-8 -*-
{
    'name': "aesl_bonus_system",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",
    'category': 'Uncategorized',
    'version': '0.1',

    'depends': ['base', 'hr', 'aesl_appraisal_system', 'ivis_payroll_functions'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'wizards/bonus_points_md_wizard_view.xml',
    ],
    "license": "OPL-1",
}

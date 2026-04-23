# -*- coding: utf-8 -*-
{
    'name': "aesl_appraisal",

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """
Long description of module's purpose
    """,

    'author': "Muhammad Hamza",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['portal','hr', 'hr_contract'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'reports/report_employee_appraisal_letter.xml',
        'views/views.xml',
        'views/portal_templates.xml',

    ],
}


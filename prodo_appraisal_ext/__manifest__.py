# -*- coding: utf-8 -*-

{
    'name': 'Prodo X AESL Appraisal',
    'version': '18.0.0.1',
    'category': 'Hr',
    'sequence': 14,
    'price': 200,
    'currency': "PKR",
    'summary': 'Appraisall Customization',
    'description': """""",
    'author': 'A.Rafay',
    'website': '',
    'images': [],
    'depends': ['hr_appraisal','ivis_employee_details','hr'],
    'data': [
        'security/ir.model.access.csv',
        # 'data/groups.xml',
        'data/mail_data.xml',
        'data/ir_sequence_data.xml',
        'views/appraisal_batches.xml',
        'views/hr_appraisal.xml',
        'report/report.xml',
        'report/appraisal_letter.xml',
        'wizard/appraisal_group_by.xml'
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'live_test_url': "",
    'images':[],
    'license': 'LGPL-3',
}
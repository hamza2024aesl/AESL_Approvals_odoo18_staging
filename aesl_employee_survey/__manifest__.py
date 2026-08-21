# -*- coding: utf-8 -*-
{
    'name': 'AESL Employee Survey Customizations',
    'version': '18.0.1.0.0',
    'category': 'Human Resources/Surveys',
    'summary': 'Custom employee survey workflows, email login enforcement, and portal notifications.',
    'description': """
AESL Employee Survey Customization
==================================
- Email link redirecting to login page before opening survey form.
- Portal notifications and list view for pending employee surveys.
    """,
    'author': 'AESL / PRODO',
    'website': 'https://www.prodo.pk',
    'depends': [
        'survey',
        'portal',
        'mail',
        'prodo_user_portal',
    ],
    'data': [
        'data/mail_template_data.xml',
        'views/portal_survey_templates.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

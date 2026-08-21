# -*- coding: utf-8 -*-
{
    'name': 'AESL HR Employee Document Request & Signature',
    'version': '18.0.1.0.0',
    'category': 'Human Resources/Documents',
    'summary': 'HR document request workflow with portal upload, digital signature, and Documents app integration.',
    'description': """
AESL HR Employee Document Request & Digital Signature
=====================================================
- HR/Admin creates specific document upload requests for employees.
- Employees view pending requests on their Employee Portal.
- Employees can upload documents, draw digital signatures, and submit.
- Integrates automatically with Odoo Enterprise Documents App.
    """,
    'author': 'AESL / PRODO',
    'website': 'https://www.prodo.pk',
    'depends': [
        'base',
        'hr',
        'documents',
        'portal',
        'mail',
        'web',
        'prodo_user_portal',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/hr_document_request_views.xml',
        'views/portal_document_request_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'aesl_hr_document_request/static/src/js/signature_pad.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}

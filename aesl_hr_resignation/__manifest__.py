# -*- coding: utf-8 -*-
{
    'name': 'AESL Employee Resignation Workflow',
    'version': '18.0.1.0.0',
    'category': 'Human Resources/Employees',
    'summary': 'Employee resignation portal submission, manager review, notice period calculation, revocation workflow, and HR notifications.',
    'description': """
AESL Employee Resignation Workflow
==================================
Key Features:
-------------
- Employee Portal Submission:
  * Submit resignation request directly from customer portal.
  * Auto-loads employee profile details (Designation, Division, Badge ID, Station, Department, Joining Date).
  * Specifies resignation reason and proposed notice period (e.g. 1 Month, 2 Months, etc.).
- Reporting Manager Review:
  * Managers only see requests from their direct reporting team members.
  * Three actions available: Accept, Reject (with mandatory remarks), and Revoke review.
  * On Acceptance:
    - Automatically calculates notice period and relieving/exit date.
    - Updates employee status to "Serving Notice Period".
    - Dispatches official Allied CAT Resignation Acceptance Memorandum email.
    - Forwards to HR.
- Resignation Revoke Workflow:
  * Once accepted and during active notice period, employee can request to revoke resignation.
  * Reporting manager receives revoke request with Accept and Reject actions.
  * If Accepted: Resignation cancelled, notice period stopped, employment restored, HR notified.
  * If Rejected: Resignation stays active, notice period continues as scheduled.
    """,
    'author': 'AESL / PRODO',
    'website': 'https://www.prodo.pk',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'hr',
        'mail',
        'portal',
        'ivis_employee_details',
        'aesl_hr_asset_allocation',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/mail_template_data.xml',
        'views/employee_resignation_views.xml',
        'views/portal_resignation_templates.xml',
        'views/resignation_clearance_portal_templates.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}


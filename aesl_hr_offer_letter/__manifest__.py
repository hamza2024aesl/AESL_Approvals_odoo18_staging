# -*- coding: utf-8 -*-
{
    'name': 'AESL HR Offer Letter & Automated Onboarding',
    'version': '18.0.1.0.0',
    'category': 'Human Resources/Employees',
    'summary': 'Generate, email, candidate portal approval, and 1-click employee onboarding with salary breakdown.',
    'description': """
AESL HR Offer Letter & Automated Onboarding
===========================================
Key Features:
-------------
- Create and manage Offer Letters from Employees and Recruitment modules.
- Auto-populates candidate personal details from Application Form:
  * Name, Father's Name, CNIC, Present Address, Religion, Gender, Date of Birth, Marital Status, Phone, etc.
- Detailed Salary Breakdown matching AESL offer format:
  * Basic Pay, House Rent, Conveyance Allowance, Utilities Allowance, and Gross Salary.
- Generates official PDF Offer Letter report with AESL branding, Medical terms, and Terms of Employment.
- Send Offer Letter button emails the PDF to candidate with secure one-click Accept and Reject buttons.
- Candidate portal response handler:
  * Accept: Sets status to Accepted, enables "Create Employee" button for HR.
  * Reject: Sets status to Rejected, records feedback, makes form editable for salary/date revisions and re-sending.
- "Create Employee" action automatically:
  * Creates hr.employee with all personal and departmental details.
  * Creates hr.contract with the agreed salary and joining date.
  * Updates recruitment applicant stage to hired.
  * Sends automated onboarding email notification to predefined HR/Management team.
    """,
    'author': 'AESL / PRODO',
    'website': 'https://www.prodo.pk',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'hr',
        'hr_recruitment',
        'hr_contract',
        'portal',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/mail_template_data.xml',
        'report/report_offer_letter.xml',
        'views/hr_offer_letter_views.xml',
        'views/hr_applicant_views.xml',
        'views/portal_templates.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}

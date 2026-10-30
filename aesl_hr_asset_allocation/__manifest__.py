# -*- coding: utf-8 -*-
{
    'name': 'AESL Employee Asset Allocation & Departmental Approvals',
    'version': '18.0.1.0.0',
    'category': 'Human Resources/Employees',
    'summary': 'Automated onboarding asset allocation checklists for Admin, IT, and HSE department heads with portal approvals.',
    'description': """
AESL Employee Asset Allocation & Departmental Approvals
======================================================
Key Features:
-------------
- Automatically notifies department heads (Admin, IT, HSE) upon new employee creation/onboarding.
- Dedicated "Asset Allocation" menu on Department Heads' portal.
- Role-based departmental checklist isolation:
  * IT Head: Laptop/Accessories, CWS ID, Email/System Accounts.
  * Admin Head: Vehicle, Fuel card, Keys, ID Card, Mobile SIM, Stationery.
  * HSE Head: Safety helmet, Goggles, Uniform, Medical/Insurance card, Food/Transport cards.
- Heads check off allocated assets, enter serial/item numbers, provide remarks, and click "Approve".
- Consolidated view-only "Assets" tab on the Employee form for HR oversight.
- Configurable Department Heads in Settings with dynamic re-assignment of approvals and notifications.
    """,
    'author': 'AESL / PRODO',
    'website': 'https://www.prodo.pk',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'hr',
        'mail',
        'portal',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/asset_template_data.xml',
        'data/mail_template_data.xml',
        'views/res_config_settings_views.xml',
        'views/hr_asset_allocation_views.xml',
        'views/hr_employee_views.xml',
        'views/portal_asset_allocation_templates.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}

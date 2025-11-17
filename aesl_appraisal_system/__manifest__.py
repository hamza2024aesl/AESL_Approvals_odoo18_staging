# -*- coding: utf-8 -*-
{
    'name': "aesl_appraisal_system",

    'summary': """aesl_appraisal_system""",

    'description': """aesl_appraisal_system""",
    'author': "My Company",
    'website': "http://www.yourcompany.com",
    'category': 'Uncategorized',
    'version': '0.1',
    'depends': ['base','mail','hr','ivis_employee_details'],
    # always loaded
    'data': [
        'data/ir_sequence_data.xml',
        'data/groups.xml',
        'data/mail_data.xml',
        'data/action_multiple_actions_views.xml',
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/group_wise_fields_readonly.xml',
        'views/employee_appraisal_view.xml',
        'views/appraisal_system_run_view.xml',
        'report/report.xml',
        'report/template_appraisal_system_report_pdf.xml',
        'report/template_appraisal_manager_summary_report_pdf.xml',
        'report/template_appraisal_manager_all_summary_report_pdf.xml',
        'report/template_appraisal_hr_summary_report_pdf.xml',
        'report/template_appraisal_higher_management_report_pdf.xml',
        'report/template_appraisal_letter_pdf.xml',
        'wizard/wizard_revert_back_remarks_view.xml',
        'wizard/wizard_manager_summary_report.xml',
        'wizard/wizard_hr_summary_report.xml',
        'wizard/wizard_higher_management_report.xml'
    ],
    "license": "OPL-1",
}

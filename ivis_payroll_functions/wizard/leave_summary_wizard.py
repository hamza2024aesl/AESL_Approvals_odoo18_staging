from odoo import models, _


class LeaveSummaryWizard(models.TransientModel):
    _name = 'leave.summary.wizard'
    _description = 'Leave Summary Wizard'

    def generate_report(self):
        self.env.cr.execute(
            '''select distinct emp.id from hr_employee as emp inner join hr_holidays as holiday on emp.id = holiday.employee_id order by emp.id asc''')
        employee_id = self.env.cr.dictfetchall()
        self.env['leave.report'].search([]).unlink()
        for employee in employee_id:
            self.env.cr.execute('''
            select id from hr_holidays_status''')
            leave_id = self.env.cr.dictfetchall()
            for leave in leave_id:
                self.env['leave.report'].create(
                    {'employee_id': employee['id'],
                     'leave_type_id': leave['id'],
                     'total': self.total_leaves(employee['id'], leave['id'], 'add', 'validate'),
                     'used': self.total_leaves(employee['id'], leave['id'], 'remove', 'validate'),
                     'remaining': (self.total_leaves(employee['id'], leave['id'], 'add', 'validate')) - (
                         self.total_leaves(employee['id'], leave['id'], 'remove', 'validate'))}
                )

        tree_id = self.env.ref('ivis_payroll_functions.ga_leave_tree_report')
        return {
            'type': 'ir.actions.act_window',
            'name': _('Leave Summary Report'),
            'res_model': 'leave.report',
            'views': [(tree_id.id, 'tree')],
            'view_id ref="ga_leave_tree_report"': '',
            'search_view_id: ref="view_leave_summary_filter"': '',
            'context': {'search_default_group_employee': 1}
        }

    def total_leaves(self, emp_id, leave_type, type, state):
        self.env.cr.execute(
            """select sum(number_of_days_temp)as total from hr_holidays where employee_id=%s and holiday_status_id=%s and type ='%s' and state='%s'""" % (
                emp_id, leave_type, type, state))
        sum = self.env.cr.dictfetchall()
        if sum[0]['total'] == None:
            return 0.0
        else:
            return sum[0]['total']

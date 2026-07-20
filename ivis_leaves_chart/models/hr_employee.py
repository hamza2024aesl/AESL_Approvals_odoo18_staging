from odoo import models, _


class HrEmployeeInherited(models.Model):
    _inherit = 'hr.employee'

    def action_time_off_dashboard(self):
        return {
            'name': _('Time Off Dashboard'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.leave',
            'views': [
                [self.env.ref('hr_holidays.hr_leave_view_tree').id, 'list'],
                [self.env.ref('hr_holidays.hr_leave_employee_view_dashboard').id, 'calendar']
            ],
            'domain': [('employee_id', 'in', self.ids)],
            'context': {
                'employee_id': self.ids,
            },
        }

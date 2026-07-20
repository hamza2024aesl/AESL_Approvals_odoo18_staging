from odoo import models, fields


class HrEmployeeInherit(models.Model):
    _inherit = 'hr.employee'
    appraisal_history_line_ids = fields.One2many('employee.appraisal.history', 'appraisal_history_id',
                                                 string='Employee Appraisal Lines', required=True, index=True,
                                                 ondelete='cascade')

    def action_view_increment_history(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Last Appraisal',
            'view_mode': 'tree',
            'res_model': 'employee.appraisal.history',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }

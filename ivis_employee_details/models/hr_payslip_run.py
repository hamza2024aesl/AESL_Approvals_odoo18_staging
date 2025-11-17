from odoo import models, fields, _, api
from odoo.exceptions import ValidationError


class HrPayslipRunInherit(models.Model):
    _inherit = 'hr.payslip.run'

    final_settlement = fields.Boolean('Final Settlement')

    def start_wizard(self):
        view = self.env.ref('ivis_employee_details.view_hr_payslip_generate_new')
        view_id = self.env['hr.payslip.employees']

        return {
            'name': _("Generate Payslips"),
            'view_mode': 'form',
            'view_id': view.id,
            'res_id': view_id.id,
            'view_type': 'form',
            'res_model': 'hr.payslip.employees',
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    def clearance_received(self):
        for approvals in self.clearance_employee:
            if (approvals.received in 'no'):
                raise ValidationError('All items should be received')
            else:
                self.emp_name.is_resign = True
                self.state = 'approved'

    @api.model
    def action_unpaid(self):
        for record in self:
            record.write({'state': 'unpaid'})
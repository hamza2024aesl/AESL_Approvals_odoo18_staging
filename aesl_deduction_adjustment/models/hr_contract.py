from datetime import date

from odoo import models, fields


class HrContractInherit(models.Model):
    _inherit = 'hr.contract'

    registration_num = fields.Char('Registration No.', related='employee_id.registration_number', store=True)

    def process_deductions(self):
        contracts = self.env['hr.contract'].search([('state', '=', 'open')])
        for emp_reg in contracts:
            if emp_reg.deductions_line:
                deductions_to_delete = emp_reg.deductions_line.filtered(
                    lambda d: (d.code == 'OTHERDED') or (d.code == 'MEALDED') or not d.code
                )
                if deductions_to_delete:
                    deductions_to_delete.unlink()
        for emp_reg in contracts:
            if not emp_reg.deductions_line:
                emp_reg.deductions_line = [
                    (0, 0, {
                        'deduction_id': 2,
                        'amount': 0.0
                    }),
                    (0, 0, {
                        'deduction_id': 1,
                        'amount': 0.0
                    })
                ]

        for emp_reg in contracts:
            deduction_data = self.env['deduction.adjustment'].search([
                ('date', '=', date.today()),
                ('emp_no', '=', emp_reg.employee_id.registration_number)
            ])

            if deduction_data:
                deductions_to_update = {
                    2: deduction_data.other_deduction if deduction_data.other_deduction else 0.0,
                    1: deduction_data.meal_deduction if deduction_data.meal_deduction else 0.0
                }
                for line in emp_reg.deductions_line:
                    if line.deduction_id.id in deductions_to_update:
                        line.write({'amount': deductions_to_update[line.deduction_id.id]})

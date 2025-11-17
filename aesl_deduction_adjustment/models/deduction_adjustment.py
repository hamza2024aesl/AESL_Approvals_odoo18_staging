from odoo import models, fields, api, _
from datetime import date,datetime, timedelta
class DeductionAdjustment(models.Model):
    _name = 'deduction.adjustment'
    _description = 'Deduction Adjustment'

    employee_name = fields.Many2one('hr.employee', 'Employee Name', index=True)
    date = fields.Date('Date', index=True, default=fields.Datetime.now)
    emp_no = fields.Char(string='Employee Number', required=True)
    other_deduction = fields.Float(string='Other Deduction')
    meal_deduction = fields.Float(string='Meal Deduction')

    @api.model
    def create(self, vals_list):
        res = super(DeductionAdjustment, self).create(vals_list)
        if res.emp_no:
            employees = self.env['hr.employee'].search([('registration_number', '=', res.emp_no)])
            if employees:
                res.update({'employee_name': employees.id})
            else:
                res.unlink()
            return res


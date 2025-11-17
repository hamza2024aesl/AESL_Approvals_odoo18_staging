from odoo import models, fields, api


class EmployeeBonus(models.Model):
    _name = 'employee.bonus'
    _description = 'Employee Bonus'
    _inherit = ['image.mixin']
    _rec_name = 'employee_id'

    employee_code = fields.Char()
    employee_id = fields.Many2one('hr.employee')
    bonus_amount = fields.Float()
    date_effective = fields.Date()

    @api.model_create_multi
    def create(self, vals_list):
        res = super(EmployeeBonus, self).create(vals_list)
        employee = self.env['hr.employee'].search([('registration_number', '=', res.employee_code)])
        res.update({'employee_id': employee.id})
        return res

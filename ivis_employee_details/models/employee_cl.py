from odoo import models, fields


class EmployeeCL(models.Model):
    _name = 'employee.cl'
    _description = "Emp clearance"

    employee_clearance = fields.Many2one('employee.resignation', string='CheckList')
    received = fields.Selection([('yes', 'Yes'), ('no', 'No')], string='Recieved', default='yes')

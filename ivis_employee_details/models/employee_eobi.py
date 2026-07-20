from odoo import models, fields


class EmployeeEOBI(models.Model):
    _name = 'employee.eobi'
    _description = "Employee EOBI"

    employee_id = fields.Many2one('hr.employee')
    rules = fields.Char(string="Rule")
    ruleName = fields.Char(string="Name")
    code = fields.Char(string="Code")
    amount = fields.Float(string="Amount")
    total = fields.Float(string="Total")
    month = fields.Char(string="Month")

from odoo import models, fields, api


class EmployeeContribution(models.Model):
    _name = "employee.contribution"

    contribution_id = fields.Many2one('hr.employee')
    description = fields.Many2one('employee.description')
    employer_contribution = fields.Integer(string="Employer Contribution")
    employee_contributions = fields.Integer(string="Employee Contribution")

    @api.depends('employer_contribution', 'employee_contributions')
    def _get_total(self):
        for users in self:
            users.total = users.employee_contributions + users.employer_contribution

    total = fields.Integer(string="Total", compute=_get_total)

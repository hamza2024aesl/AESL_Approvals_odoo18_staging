from odoo import models, fields


class EmployeeRecords(models.Model):
    _name = 'interest.distribution.line'
    _description = 'Interest Distribution Line'

    interest_id = fields.Many2one('interest.distribution')
    employee_id = fields.Many2one('hr.employee', string="Employee")
    excluded_pf_interest = fields.Boolean(related='employee_id.exclude_pf_interest')
    previous_total = fields.Float(string="Previous PF Total")
    percent = fields.Float()
    interest = fields.Float()
    extra_amount = fields.Float()
    current_total = fields.Float(string="Current PF Total")

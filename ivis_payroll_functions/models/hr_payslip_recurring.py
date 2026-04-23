from odoo import fields, models


class HrPayslipRecurring(models.Model):
    _name = 'hr.payslip.recurring'
    _description = 'HR Payslip Recurring'

    line = fields.Many2one('hr.payslip')
    description = fields.Char(string='Description', readonly=True)
    code = fields.Char(help="The code that can be used in the salary rules", readonly=True)
    amount = fields.Float(string='Amount')

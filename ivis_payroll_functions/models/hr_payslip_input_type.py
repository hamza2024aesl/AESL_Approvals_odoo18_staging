from odoo import fields, models


class InheritPayslipInput(models.Model):
    _inherit = 'hr.payslip.input.type'

    payslip = fields.Many2one('hr.payslip')

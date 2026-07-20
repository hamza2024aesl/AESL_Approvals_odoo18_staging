from odoo import models


class InheritHrPayroll(models.Model):
    _inherit = 'hr.payslip'

    def action_payslip_done(self):
        res = super().action_payslip_done()
        self.employee_id.compute_funds_pf()
        return res

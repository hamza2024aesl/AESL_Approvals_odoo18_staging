from odoo import models, fields, api


class HrPayslipInherit(models.Model):
    _inherit = 'hr.payslip'

    settlement_payslip = fields.Boolean("Final Settlement")
    contract_id = fields.Many2one('hr.contract', string='Contract', readonly=True,
                                  domain="[('company_id', '=', company_id)]")

    @api.model_create_multi
    def create(self, vals_list):
        res = super(HrPayslipInherit, self).create(vals_list)
        for rec in res:
            if rec.employee_id.is_resign == True:
                rec.employee_id.is_final_settlement = True
        return res

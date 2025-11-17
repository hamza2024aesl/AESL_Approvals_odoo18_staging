from odoo import models, fields, api


class TaxDeductions(models.Model):
    _name = 'tax.deductions'
    _description = 'Tax Deductions'

    contract_id = fields.Many2one('hr.contract')
    deduction_id = fields.Many2one('detail.tax')

    name = fields.Char("Name")
    code = fields.Char("Code", required=True, copy=False, related='deduction_id.code')
    amount = fields.Float("Amount", compute='_computtotal', store=True)
    recurring = fields.Boolean(string="Recurring", related='deduction_id.recurring')
    no_months = fields.Integer("No Of Months")
    remaining_months = fields.Integer("Remaining Months")
    amount_per_month = fields.Float("Amount Per Months", compute='_cumputeremianing', store=True)
    remainaing_amount = fields.Float("Remaining Amount")
    mf_pf = fields.Selection([('mf', 'Mutual Funds'), ('pf', 'Pension Fund')], string="Fund Type")
    actual_amount = fields.Float("Actual Amount")
    taxable_salary = fields.Float("Taxable Salary", compute='comput_taxable', store=True)
    amount_20 = fields.Float("2M")
    total_tax = fields.Float('Total Taxes Per Month')

    @api.onchange('no_months')
    def onchange_total(self):
        self.remaining_months = self.no_months

    @api.depends('mf_pf')
    def comput_taxable(self):
        for rec in self:
            payslip = self.env['hr.payslip'].search([('contract_id', '=', rec._origin.contract_id.id)], limit=1)
            amountt = payslip.line_ids.filtered(lambda l: l.code == 'TIYB').amount
            tax_salry = (20 / 100) * amountt
            rec.taxable_salary = tax_salry

    @api.depends('mf_pf', 'actual_amount', 'amount_20', 'taxable_salary')
    def _computtotal(self):
        list_min = []
        for rec in self:
            if rec.mf_pf == 'mf':
                list_min.append(rec.taxable_salary)
                list_min.append(rec.actual_amount)
                list_min.append(rec.amount_20)
                print(list_min)
                rec.amount = min(list_min)
            else:
                list_min.append(rec.actual_amount)
                list_min.append(rec.taxable_salary)
                rec.amount = min(list_min)

    @api.depends('no_months', 'remaining_months')
    def _cumputeremianing(self):
        for rec in self:
            if rec.remaining_months > 0:
                rec.amount_per_month = rec.amount / rec.no_months
            else:
                rec.amount_per_month = 0.0

from odoo import models, fields


class AccountSalary(models.Model):
    _name = "account.salary"
    _description = "Account Salary"

    contract_id = fields.Many2one('hr.contract')
    analytic_account = fields.Many2one('account.analytic.account')
    percentage = fields.Integer('Percentage')

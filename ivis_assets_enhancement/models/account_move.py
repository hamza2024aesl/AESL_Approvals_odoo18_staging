from odoo import fields, models


class AccountMoveInherit(models.Model):
    _inherit = 'account.move'

    analytic_account_id = fields.Many2one(
        comodel_name='account.analytic.account',
        string='Analytic Account',
        readonly=True
    )

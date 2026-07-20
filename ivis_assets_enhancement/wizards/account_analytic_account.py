from odoo import fields, models


class AccountAnalyticAccountWizard(models.TransientModel):
    _name = 'account_asset_change_analytic_account'

    analytic_id = fields.Many2one('account.analytic.account', string='Analytic Account')

    def change_analytic_account(self):
        asset_id = self.env['account.asset'].browse(self._context.get('active_id'))
        asset_id.change_analytic_account(self.analytic_id)
import logging
from dateutil.relativedelta import relativedelta
from odoo import fields, models, api, _
_logger = logging.getLogger(__name__)


class AccountAssetInherit(models.Model):
    _inherit = 'account.asset'

    asset_number = fields.Char(readonly=True, copy=False, default='New')
    account_analytic_id = fields.Many2one(
        comodel_name='account.analytic.account',
        string='Analytic Account',
        readonly=True,
        states={'draft': [('readonly', False)], 'model': [('readonly', False)]},
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        tracking=True
    )

    @api.model
    def create(self, vals):
        if vals.get('asset_number', 'New') == 'New':
            vals['asset_number'] = self.env['ir.sequence'].next_by_code(
                'account.asset.seq') or '/'
        return super(AccountAssetInherit, self).create(vals)

    def compute_depreciation_board(self, date=False):
        res = super(AccountAssetInherit, self).compute_depreciation_board()
        if self.parent_id:
            self.change_analytic_distribution(self.parent_id.analytic_distribution)
        self.change_analytic_distribution(self.analytic_distribution)
        return res
        
    def custom_validate(self, date_end=fields.Date.today()):
        fields = [
            'method',
            'method_number',
            'method_period',
            'method_progress_factor',
            'salvage_value',
            'original_move_line_ids',
        ]
        ref_tracked_fields = self.fields_get(fields)
        self.write({'state': 'open'})
        tracked_fields = ref_tracked_fields.copy()
        if self.method == 'linear':
            del (tracked_fields['method_progress_factor'])
        _dummy, tracking_value_ids = self._message_track(tracked_fields, dict.fromkeys(fields))
        asset_name = {
            'purchase': (_('Asset created'), _('An asset has been created for this move:')),
            'sale': (_('Deferred revenue created'), _('A deferred revenue has been created for this move:')),
            'expense': (_('Deferred expense created'), _('A deferred expense has been created for this move:')),
        }[self.asset_type]
        msg = asset_name[1] + ' <a href=# data-oe-model=account.asset data-oe-id=%d>%s</a>' % (self.id, self.name)
        self.message_post(body=asset_name[0], tracking_value_ids=tracking_value_ids)
        for move_id in self.original_move_line_ids.mapped('move_id'):
            move_id.message_post(body=msg)
        if not self.depreciation_move_ids.filtered(
                lambda move: move.date <= date_end and move.state != 'posted'):
            self.compute_depreciation_board()
        self._check_depreciations()
        self.depreciation_move_ids.filtered(lambda move: move.date <= date_end and move.state != 'posted')._post()

    @api.onchange('account_analytic_id')
    def change_depreciation_move_ids_analytic_account(self):
        for line in self.depreciation_move_ids.filtered(lambda rec: rec.state == 'draft'):
            line.analytic_account_id = self.account_analytic_id.id

    def change_analytic_distribution(self, analytic_distribution):
        self.analytic_distribution = analytic_distribution
        for line in self.depreciation_move_ids.filtered(lambda rec: rec.state == 'draft'):
            # line.analytic_account_id = analytic_distribution
            for move_line in line.line_ids.filtered(lambda rec: rec.analytic_distribution):
                move_line.analytic_distribution = analytic_distribution
        for child in self.children_ids:
            child.change_analytic_distribution(self.analytic_distribution)

    def action_asset_compute(self):
        return {
            'name': _('Asset Compute'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'account.asset.compute',
            'context': {
                'active_model': 'account.asset',
                'active_ids': self.ids,
            },
            'target': 'new'
        }

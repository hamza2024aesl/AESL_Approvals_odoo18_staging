import logging
from dateutil.relativedelta import relativedelta
from odoo.tools import float_is_zero
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

    def _recompute_board(self, start_depreciation_date=False):
        self.ensure_one()
        # All depreciation moves that are posted
        posted_depreciation_move_ids = self.depreciation_move_ids.filtered(
            lambda mv: mv.state == 'posted' and not mv.asset_value_change
        ).sorted(key=lambda mv: (mv.date, mv.id))

        # imported_amount = self.already_depreciated_amount_import ivis
        imported_amount = 0 # ivis
        residual_amount = self.value_residual - sum(self.depreciation_move_ids.filtered(lambda mv: mv.state == 'draft').mapped('depreciation_value'))
        if not posted_depreciation_move_ids:
            residual_amount += imported_amount
        residual_declining = residual_at_compute = residual_amount
        # start_yearly_period is needed in the 'degressive' and 'degressive_then_linear' methods to compute the amount when the period is monthly
        start_recompute_date = start_depreciation_date = start_yearly_period = start_depreciation_date or self.paused_prorata_date

        last_day_asset = self._get_last_day_asset()
        final_depreciation_date = self._get_end_period_date(last_day_asset)
        total_lifetime_left = self._get_delta_days(start_depreciation_date, last_day_asset)

        depreciation_move_values = []
        if not float_is_zero(self.value_residual, precision_rounding=self.currency_id.rounding):
            while not self.currency_id.is_zero(residual_amount) and start_depreciation_date < final_depreciation_date:
                period_end_depreciation_date = self._get_end_period_date(start_depreciation_date)
                period_end_fiscalyear_date = self.company_id.compute_fiscalyear_dates(period_end_depreciation_date).get('date_to')
                lifetime_left = self._get_delta_days(start_depreciation_date, last_day_asset)

                days, amount = self._compute_board_amount(residual_amount, start_depreciation_date, period_end_depreciation_date, False, lifetime_left, residual_declining, start_yearly_period, total_lifetime_left, residual_at_compute, start_recompute_date)
                residual_amount -= amount

                if not posted_depreciation_move_ids:
                    # self.already_depreciated_amount_import management.
                    # Subtracts the imported amount from the first depreciation moves until we reach it
                    # (might skip several depreciation entries)
                    if abs(imported_amount) <= abs(amount):
                        amount -= imported_amount
                        imported_amount = 0
                    else:
                        imported_amount -= amount
                        amount = 0

                if self.method == 'degressive_then_linear' and final_depreciation_date < period_end_depreciation_date:
                    period_end_depreciation_date = final_depreciation_date

                if not float_is_zero(amount, precision_rounding=self.currency_id.rounding):
                    # For deferred revenues, we should invert the amounts.
                    depreciation_move_values.append(self.env['account.move']._prepare_move_for_asset_depreciation({
                        'amount': amount,
                        'asset_id': self,
                        'depreciation_beginning_date': start_depreciation_date,
                        'date': period_end_depreciation_date,
                        'asset_number_days': days,
                    }))

                if period_end_depreciation_date == period_end_fiscalyear_date:
                    start_yearly_period = self.company_id.compute_fiscalyear_dates(period_end_depreciation_date).get('date_from') + relativedelta(years=1)
                    residual_declining = residual_amount

                start_depreciation_date = period_end_depreciation_date + relativedelta(days=1)

        return depreciation_move_values

    def _compute_board_amount(
            self, residual_amount, depreciation_start_date, depreciation_end_date,
            ignored, lifetime_left, residual_declining, start_yearly_period,
            total_lifetime_left, residual_at_compute, start_recompute_date
    ):
        """Compute amount for a depreciation line based on method."""
        self.ensure_one()

        days = (depreciation_end_date - depreciation_start_date).days + 1
        amount = 0.0

        if self.method == 'degressive' and self.method_progress_factor:
            # Declining balance formula
            amount = residual_amount * self.method_progress_factor

        elif self.method == 'degressive_then_linear' and self.method_progress_factor:
            # Use whichever is smaller (switch to linear when linear surpasses degressive)
            linear_amount = self.original_value / self.method_number
            degressive_amount = residual_amount * self.method_progress_factor
            amount = min(degressive_amount, linear_amount)

        else:
            # Straight-line fallback
            amount = self.value_residual / self.method_number

        # If this is the last depreciation entry → take all remaining residual
        last_day_asset = self._get_last_day_asset()
        # if this depreciation_end_date >= last_day_asset (final depreciation period)
        if depreciation_end_date >= last_day_asset:
            amount = residual_amount

        # Safety: avoid rounding loss
        if amount > residual_amount:
            amount = residual_amount

        return days, self.currency_id.round(amount)

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

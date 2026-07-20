import logging
from odoo import fields, models
_logger = logging.getLogger(__name__)


class AccountAssetCompute(models.TransientModel):
    _name = "account.asset.compute"
    _description = "Compute Assets"

    date_end = fields.Date(
        string="Date",
        required=True,
        default=fields.Date.today,
        help="All depreciation lines prior to this date will be automatically"
             " posted",
    )
    note = fields.Text()

    def asset_compute(self):
        _logger.warning("Assets Computation Start")
        for asset in self.env['account.asset'].browse(self.env.context.get('active_ids')):
            if self.date_end >= asset.first_depreciation_date:
                _logger.warning(f"{asset.name} - Computation Start")
                asset.custom_validate(date_end=self.date_end)
                for child in asset.children_ids:
                    child.custom_validate(date_end=self.date_end)
                _logger.warning(f"{asset.name} - Computation End")
        _logger.warning("Assets Computation End")

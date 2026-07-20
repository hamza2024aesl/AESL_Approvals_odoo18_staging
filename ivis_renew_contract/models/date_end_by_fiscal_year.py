from odoo import models
from datetime import date

class HrContract(models.Model):
    _inherit = 'hr.contract'

    def action_process_fiscal_end_date(self):
        current_year = date.today().year
        fiscal_start_date = date(current_year, 7, 1)  # 1st July
        fiscal_end_date = date(current_year, 6, 30)  # 30th June

        for contract in self:
            if contract.state == 'open':
                end_date_previous = contract.date_end
                name_previous = contract.name

                contract.write({
                    'name': f"{name_previous} (Old)",
                    'date_end': fiscal_end_date,
                    'state': 'close',
                })

                new_contract_vals = {
                    'date_start': fiscal_start_date,
                    'state': 'open',
                    'date_end': end_date_previous or False,
                    'x_studio_old_taxable_salary': False,
                    'x_studio_old_tax_deducted': False,
                    'x_studio_tax_rebate_amount': False,
                    'x_studio_zakat': False,
                }

                new_contract = contract.copy(default=new_contract_vals)
                new_contract.write({'name': name_previous})
import calendar
import datetime
import math
from datetime import timedelta, date, datetime
import dateutil.parser
from dateutil import rrule
from dateutil.relativedelta import relativedelta
from odoo import api, models, fields


class HrContractInherit(models.Model):
    _inherit = 'hr.contract'

    tax_rebate = fields.Float(string="Tax Rebate")
    car_entitlement = fields.Boolean(string="Car Entitlement")
    car_cost = fields.Float(string="Car Cost")
    allowance_one = fields.Float()
    allowance_two = fields.Float()
    allowance_three = fields.Float()
    allowance_four = fields.Float()
    allowance_five = fields.Float()
    deduction_one = fields.Float()
    deduction_two = fields.Float()
    deduction_three = fields.Float()
    deduction_four = fields.Float()
    deduction_five = fields.Float()
    previous_salary = fields.Float(string='Previous Salary')
    previous_tax = fields.Float(string='Previous Deducted Tax')
    sessi_calculation = fields.Boolean(default=False)
    eobi = fields.Boolean(string="EOBI", default=False)
    gratuity = fields.Boolean(string='Gratuity')

    @api.model_create_multi
    def create(self, vals):
        res = super(HrContractInherit, self).create(vals)
        rc_id = self.env['ir.config_parameter'].search([('key', '=', 'minimum_wage')])
        minimum_wage = int(rc_id.value) if rc_id else 0.0

        for record, val in zip(res, vals):
            if val['wage'] <= minimum_wage:
                record.write({'sessi_calculation': True})
        return res

    def get_fiscal_date_start(self, date_from):
        fiscal_year_start_str = (str(date_from.year - 1) if date_from.month < 7 else str(date_from.year)) + '-07-01'
        return datetime.strptime(fiscal_year_start_str, '%Y-%m-%d').date()

    def get_fiscal_date_end(self, date_from):
        fiscal_year_end_str = (str(date_from.year) if date_from.month < 7 else str(date_from.year + 1)) + '-06-30'
        return datetime.strptime(fiscal_year_end_str, '%Y-%m-%d').date()
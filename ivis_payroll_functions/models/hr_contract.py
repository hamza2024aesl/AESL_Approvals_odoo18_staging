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

    def get_calculate_unpaid_leaves(self, payslip):
        employee = payslip.employee_id
        date_from = payslip.date_from
        date_to = payslip.date_to
        if not (employee and date_from and date_to):
            return 0.0

        prev_month = date_from.month - 1 or 12
        year = date_from.year if date_from.month > 1 else date_from.year - 1
        date_from = fields.Date.from_string(f"{year}-{prev_month:02d}-01")

        last_day = calendar.monthrange(date_from.year, date_from.month)[1]
        date_to = date_from.replace(day=last_day)

        unpaid_type = self.env.ref("hr_holidays.holiday_status_unpaid", raise_if_not_found=False)
        if unpaid_type:
            leave_type_domain = [("holiday_status_id", "=", unpaid_type.id)]
        else:
            leave_type_domain = [("holiday_status_id.name", "ilike", "LWP")]

        domain = [
                     ("employee_id", "=", employee.id),
                     ("state", "not in", ["cancel", "refuse"]),
                     ("request_date_from", "<=", date_to),
                     ("request_date_to", ">=", date_from),
                 ] + leave_type_domain

        leaves = self.env["hr.leave"].search(domain)
        return sum(leaves.mapped("number_of_days")) if leaves else 0.0

    def get_calculate_out_of_contract_days(self, payslip):
        employee = payslip.employee_id
        date_from = payslip.date_from
        date_to = payslip.date_to
        contract = payslip.contract_id

        out_days = 0

        if contract.date_start and contract.date_start > date_from:
            out_days += (contract.date_start - date_from).days

        if contract.date_end and contract.date_end < date_to:
            out_days += (date_to - contract.date_end).days

        return out_days
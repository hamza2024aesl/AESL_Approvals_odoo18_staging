from datetime import datetime
from odoo import models, fields


class HrEmployeeInherit(models.Model):
    _inherit = 'hr.employee'

    pf_employee = fields.Float(string="Opening Employee Contribution")
    pf_employer = fields.Float(string="Opening Employer Contribution")
    pf_interest = fields.Float(string="Opening Interest")
    exclude_pf_interest = fields.Boolean(string="Exclude Interest")
    employee_contribution = fields.Float(string="Employee Contribution")
    employer_contribution = fields.Float(string="Employer Contribution")
    interest = fields.Float(string="Interest")
    total = fields.Float(string="Total")
    x_studio_territory = fields.Char(string="Territory")
    x_pay_scale = fields.Selection([
        ('sps1', 'SPS1'), ('sps2', 'SPS2'), ('sps3', 'SPS3'), ('sps4', 'SPS4'), ('sps5', 'SPS5'), ('sps6', 'SPS6'),
        ('sps7', 'SPS7'), ('sps8', 'SPS8'), ('sps9', 'SPS9'), ('sps10', 'SPS10'), ('sps11', 'SPS11'),
        ('sps12', 'SPS12'), ('sps13', 'SPS13'), ('sps14', 'SPS14'), ('sps15', 'SPS15'),
        ('fixed_contract', 'Fixed Contract'), ('visiting', 'Visiting'), ('tts', 'TTS'),
    ], string="Pay Scale")
    eobi_number = fields.Char(string="EOBI Number")
    gratuity_allowed = fields.Boolean(string="Gratuity Allowed")

    def get_loan_balance(self, emp_id, date_from, date_to, loan_type):
        loan_type_record = self.env['loan.type'].search([('code', '=', loan_type)])
        if date_to is None:
            date_to = datetime.now().strftime('%Y-%m-%d')
        loan_details = self.env['loan.installment.details'].search(
            [('employee_id', '=', emp_id), ('state', '!=', 'paid')
                , ('date_from', '>=', date_from), ('date_from', '<=', date_to)
                , ('loan_repayment_method', '=', 'salary')
                , ('loan_type', '=', loan_type_record.id)], limit=1)
        if loan_details:
            rec = loan_details.loan_id.total_amount_due
            return rec
        return 0

    def get_principle_loan_balance(self, emp_id, date_from, date_to, loan_type):
        loan_type_record = self.env['loan.type'].search([('code', '=', loan_type)])
        if date_to is None:
            date_to = datetime.now().strftime('%Y-%m-%d')
        loan_details = self.env['loan.installment.details'].search(
            [('employee_id', '=', emp_id), ('state', '!=', 'paid')
                , ('date_from', '>=', date_from), ('date_from', '<=', date_to)
                , ('loan_repayment_method', '=', 'salary')
                , ('loan_type', '=', loan_type_record.id)], limit=1)
        if loan_details:
            rec = loan_details.loan_id.total_amount_due_principal
            return rec
        return 0
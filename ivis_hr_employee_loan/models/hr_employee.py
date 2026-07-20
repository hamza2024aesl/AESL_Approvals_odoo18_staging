from datetime import datetime
from odoo import models, fields


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    loan_policy = fields.Many2many(
        'loan.policy',
        'policy_employee_rel',
        'employee_id',
        'policy_id',
        string='Loan Policies'
    )
    allow_multiple_loan = fields.Boolean(
        string='Allow Multiple Loans'
    )
    loan_defaulter = fields.Boolean(
        string='Loan Defaulter'
    )
    loan_ids = fields.One2many(
        'employee.loan.details',
        'employee_id',
        string='Loans Details',
        readonly=True,
    )

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

    def get_installment_loan(self, emp_id, date_from, date_to, loan_type):

        loan_type_record = self.env['loan.type'].search([('code', '=', loan_type)])

        if date_to is None:
            date_to = datetime.now().strftime('%Y-%m-%d')
        # probuse added paid state and loan_repayment_method condition
        self._cr.execute(
            "SELECT sum(o.principal_amt) ,sum(o.interest_amt) from employee_loan_details as e inner join loan_installment_details as o on \
               e.id=o.loan_id  where \
               o.employee_id=%s \
               AND e.loan_type= %s\
               AND o.state != 'paid'\
               AND o.loan_repayment_method = 'salary'\
               AND o.date_from >= %s AND o.date_from <= %s ",
            (emp_id, loan_type_record.id, str(date_from), str(date_to)))
        res = self._cr.fetchone()
        if res[0]:
            rec = res[0]
            return rec
        return 0

    def get_interest_loan(self, emp_id, date_from, date_to, loan_type):
        loan_type_record = self.env['loan.type'].search([('code', '=', loan_type)])
        if date_to is None:
            date_to = datetime.now().strftime('%Y-%m-%d')
        # probuse added paid state  and loan_repayment_method condition
        self._cr.execute(
            "SELECT sum(o.principal_amt) ,sum(o.interest_amt) from employee_loan_details as e inner join loan_installment_details as o on \
               e.id=o.loan_id  where \
               o.employee_id=%s \
               AND e.loan_type= %s\
               AND o.state != 'paid'\
               AND o.loan_repayment_method = 'salary'\
               AND o.date_from >= %s AND o.date_from <= %s ",
            (emp_id, loan_type_record.id, str(date_from), str(date_to)))
        res = self._cr.fetchone()
        if res[1]:
            rec = res[1]
            return rec
        return 0

from datetime import datetime

from odoo import models, fields


class EmployeeInherit(models.Model):
    _inherit = 'hr.employee'

    apply_provident_fund = fields.Boolean(default=True)
    pf_employee = fields.Float(string="Opening Employee Contribution")
    pf_employer = fields.Float(string="Opening Employer Contribution")
    pf_interest = fields.Float(string="Opening Interest")
    exclude_pf_interest = fields.Boolean(string="Exclude Interest")
    employee_contribution = fields.Float()
    employer_contribution = fields.Float()
    interest = fields.Float()
    total = fields.Float()

    def compute_funds_pf(self):
        for rec in self:
            employee_payslip = self.env['hr.payslip'].search(
                [('employee_id', '=', rec.id), ('state', 'in', ['done', 'paid'])], order='date_from asc')
            employee_contribution = 0
            employer_contribution = 0
            payMonth = ''
            for payslips in employee_payslip.line_ids.filtered(lambda l: (l.code == 'PF_EMPLOYEE' or l.code == 'PF_EMPLOYER')):
                payMonth = datetime.strptime(str(payslips.date_from), '%Y-%m-%d').strftime('%B')
                if payslips.code == 'PF_EMPLOYEE':
                    employee_contribution += abs(payslips.total)
                elif payslips.code == 'PF_EMPLOYER':
                    employer_contribution += abs(payslips.total)
            rec.employee_contribution = employee_contribution
            rec.employer_contribution = employer_contribution
            rec.total = employer_contribution + employee_contribution + rec.interest

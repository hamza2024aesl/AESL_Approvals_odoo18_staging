from datetime import datetime
from odoo import models, fields, _
from odoo.exceptions import ValidationError


class PfInterstDistribution(models.Model):
    _name = 'interest.distribution'
    _description = 'Interest Distribution'
    _rec_name = 'date'

    date = fields.Date()
    amount = fields.Float(required=True)
    employee_ids = fields.One2many('interest.distribution.line', 'interest_id')
    state = fields.Selection([('draft', 'Draft'), ('distributed', 'Distributed')], default='draft')
    note = fields.Text()

    def compute_funds(self, employee):
        employee_contract = self.env['hr.contract'].search([('employee_id', '=', employee.id), ('state', '=', 'open')])
        for contract in employee_contract:
            employee_payslip = self.env['hr.payslip'].search(
                [('contract_id', '=', contract.id), ('state', '=', 'done')], order='date_from asc')
            employee_contribution = 0
            employer_contribution = 0
            payMonth = ''
            for payslips in employee_payslip.line_ids.filtered(lambda l: (l.code == 'PF' or l.code == 'PFEC')):
                payMonth = datetime.strptime(str(payslips.date_from), '%Y-%m-%d').strftime('%B')
                if payslips.code == 'PF':
                    employee_contribution += abs(payslips.total)
                elif payslips.code == 'PFEC':
                    employer_contribution += abs(payslips.total)
            employee.employee_contribution = employee_contribution
            employee.employer_contribution = employer_contribution
            employee.total = employer_contribution + employee_contribution + employee.interest

    def fetch_employees(self):
        employee_records = self.env['hr.employee'].search([])
        self.employee_ids.unlink()
        for emp_rec in employee_records:
            self.compute_funds(emp_rec)
            if emp_rec.total > 0:
                self.employee_ids.create({'interest_id': self.id, 'employee_id': emp_rec.id,
                                          'previous_total': emp_rec.total + emp_rec.pf_employee + emp_rec.pf_employer + emp_rec.pf_interest})
        total = sum(i.previous_total for i in self.employee_ids)
        for line in self.employee_ids:
            line.percent = (line.previous_total / total) * 100

    def distribute_profit(self):
        if self.employee_ids:
            excluded_sum_interest = 0
            for line in self.employee_ids:
                line.interest = (self.amount * line.percent) / 100
                if not line.employee_id.exclude_pf_interest:
                    line.current_total = line.previous_total + ((self.amount * line.percent) / 100)
                    line.employee_id.interest += (self.amount * line.percent) / 100
                    line.employee_id.total = line.previous_total + line.employee_id.interest
                else:
                    excluded_sum_interest += (self.amount * line.percent) / 100

            total = sum(i.previous_total for i in self.employee_ids.filtered(lambda x: x.excluded_pf_interest == False))
            for line in self.employee_ids:
                line.percent = (line.previous_total / total) * 100
                if not line.employee_id.exclude_pf_interest:
                    line.current_total += (excluded_sum_interest * line.percent) / 100
                    line.employee_id.interest += (excluded_sum_interest * line.percent) / 100
                    line.extra_amount = (excluded_sum_interest * line.percent) / 100
                    line.employee_id.total = line.previous_total + line.interest + line.extra_amount
                else:
                    line.current_total = line.previous_total
            self.state = 'distributed'
        else:
            raise ValidationError(_("No record found in below table!"))

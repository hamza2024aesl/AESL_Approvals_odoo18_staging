from odoo import fields, models


class EmployeeSalarySheet(models.TransientModel):
    _name = 'employee.salary.sheet'
    _description = 'Employee Salary Sheet'

    salary_rule_id = fields.Many2one('hr.payslip.run', string='Payslip Batch')

    def get_batch_period(self):
        return {'date_from': self.salary_rule_id.date_start, 'date_to': self.salary_rule_id.date_end}

    def get_employee_details(self, payslip_id):
        payslip_obj = self.env['hr.payslip'].search([('id', '=', payslip_id)])
        return [{'employee_name': payslip_obj.employee_id.name,
                 'cnic': payslip_obj.employee_id.identification_id,
                 'account_no': payslip_obj.employee_id.bank_account_id.acc_number,
                 'code': payslip_obj.employee_id.barcode, 'designation': payslip_obj.employee_id.job_id.name,
                 'department': payslip_obj.employee_id.department_id.name}]

    def generate_report(self):
        rule_list = []
        for rec in self.env['hr.payslip'].search([('payslip_run_id', '=', self.salary_rule_id.id)]):
            self.env.cr.execute(
                """select distinct name,amount from hr_payslip_line where slip_id = {0}""".format(
                    rec.id))
            rule_list.append({rec.id: self.env.cr.dictfetchall()})
        return {
            'type': 'ir.actions.report',
            'report_type': 'qweb-pdf',
            'data': {'form': {'rules': rule_list}},
            'report_name': 'ivis_payroll_functions.report_salarysheet',
            'report_file': 'ivis_payroll_functions.report_salarysheet',
        }

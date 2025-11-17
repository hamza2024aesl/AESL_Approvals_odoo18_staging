from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from odoo import models, fields


class PayrollWizard(models.TransientModel):
    _name = 'payroll.wizard'
    _description = 'Payroll Wizard'

    current_month = fields.Date(default=lambda self: fields.date.today())
    previous_month = fields.Date(default=lambda self: fields.date.today())
    current_user = fields.Many2one('res.users', 'Current User', default=lambda self: self.env.user)
    current_company = fields.Many2one("res.company", string="Company", default=lambda self: self.env.company.id,
                                      readonly=True)
    current_date = date.today()
    type = fields.Selection([('Payroll Reconiliation', 'Payroll Reconiliation'),
                             ('Salary Through Cheque', 'Salary Through Cheque'),
                             ('Provident Funds Report', 'Provident Funds Report'),
                             ('Certificate Of Deduction', 'Certificate Of Deduction'),
                             ('Provident Fund Deduction Certificate', 'Provident Fund Deduction Certificate'),
                             ('Performance Appraisal Form', 'Performance Appraisal Form')],
                            default='Payroll Reconiliation',
                            required=True)
    employee_ids = fields.Many2many('hr.employee', string='Employees')

    def reconciliation_report(self):
        if self.type == 'Payroll Reconiliation':
            return {
                'type': 'ir.actions.report',
                'report_name': "ivis_payroll_functions.report_reconciliation_report",
                'report_file': "ivis_payroll_functions.report_reconciliation_report",
                'report_type': 'qweb-pdf',
            }
        elif self.type == 'Salary Through Cheque':
            return {
                'type': 'ir.actions.report',
                'report_name': "ivis_payroll_functions.report_salary_through_cheque",
                'report_file': "ivis_payroll_functions.report_salary_through_cheque",
                'report_type': 'qweb-pdf',
            }
        elif self.type == 'Provident Funds Report':
            return {
                'type': 'ir.actions.report',
                'report_name': "ivis_payroll_functions.provident_funds_xl_report",
                'report_file': "ivis_payroll_functions.provident_funds_xl_report",
                'report_type': 'xlsx',
            }
        elif self.type == 'Certificate Of Deduction':
            return {
                'type': 'ir.actions.report',
                'report_name': "ivis_payroll_functions.report_certificate_deduction_report",
                'report_file': "ivis_payroll_functions.report_certificate_deduction_report",
                'report_type': 'qweb-pdf',
            }
        elif self.type == 'Provident Fund Deduction Certificate':
            return {
                'type': 'ir.actions.report',
                'report_name': "ivis_payroll_functions.report_provident_fund_deduction_certificate",
                'report_file': "ivis_payroll_functions.report_provident_fund_deduction_certificate",
                'report_type': 'qweb-pdf',
            }
        elif self.type == 'Performance Appraisal Form':
            return {
                'type': 'ir.actions.report',
                'report_name': "ivis_payroll_functions.report_performance_appraisal_form",
                'report_file': "ivis_payroll_functions.report_performance_appraisal_form",
                'report_type': 'qweb-pdf',
            }

    def get_salaries_through_cheque(self):
        month_start = self.current_month + relativedelta(day=1)
        month_end = self.current_month + relativedelta(day=0)
        self.env.cr.execute("""select hr.name,hrj.name as "designation",hr.work_location,hpsl.amount from hr_payslip as hps
                                                    inner join hr_payslip_line as hpsl on hps.id = hpsl.slip_id 
        											inner join hr_employee as hr on hps.employee_id = hr.id
													inner join hr_job as hrj on hr.job_id = hrj.id
        											where hpsl.code = 'NET' and hr.bank_account_id is null and
        											 hps.date_from between '%s' and '%s' and hps.state='done' and hps.company_id = '%s'
                                            """ % (str(month_start), str(month_end), str(self.env.company.id)))
        cheque = self.env.cr.dictfetchall()
        data_list = []
        total = 0
        for ch in cheque:
            total += abs(ch['amount'])
            data_list.append((ch['name'], ch['designation'], ch['work_location'], abs(ch['amount'])))
        result_list = []
        vals = {'data': data_list,
                'total': total}
        result_list.append(vals)
        return result_list

    def get_previous_month_gross(self, date, code="('GROSS')"):
        month_start = date + relativedelta(day=1)
        month_end = date + relativedelta(day=0)
        self.env.cr.execute(f"""
                                    select sum(hpsl.amount) from hr_payslip as hps
                                    inner join hr_payslip_line as hpsl on hps.id = hpsl.slip_id
                                    where hpsl.code in {code} and hps.date_from between '%s' and '%s' and hps.state='done' and hps.company_id = '%s'
                                            """ % (str(month_start), str(month_end), str(self.env.company.id)))
        records = self.env.cr.dictfetchall()
        if records[0]['sum']:
            return records[0]['sum']
        return 0

    def get_previous_total_employees(self, date):
        month_start = date + relativedelta(day=1)
        month_end = date + relativedelta(day=0)
        self.env.cr.execute("""
                                            select count(hpsl.amount) from hr_payslip as hps
                                            inner join hr_payslip_line as hpsl on hps.id = hpsl.slip_id
                                            where hpsl.code = 'GROSS' and hps.date_from between '%s' and '%s' and hps.state='done' and hps.company_id = '%s'
                                            """ % (str(month_start), str(month_end), str(self.env.company.id)))
        records = self.env.cr.dictfetchall()
        if records[0]['count']:
            return records[0]['count']
        return 0

    def get_current_month_gross(self, date, code="('GROSS')"):
        month_start = date + relativedelta(day=1)
        month_end = date + relativedelta(day=0)
        self.env.cr.execute(f"""
                                    select sum(hpsl.amount) from hr_payslip as hps
                                    inner join hr_payslip_line as hpsl on hps.id = hpsl.slip_id
                                    where hpsl.code in {code} and hps.date_from between '%s' and '%s' and hps.state != 'cancel' and hps.company_id = '%s'
                                            """ % (str(month_start), str(month_end), str(self.env.company.id)))
        records = self.env.cr.dictfetchall()
        if records[0]['sum']:
            return records[0]['sum']
        return 0

    def get_current_total_employees(self, date):
        month_start = date + relativedelta(day=1)
        month_end = date + relativedelta(day=0)
        self.env.cr.execute("""
                                            select count(hpsl.amount) from hr_payslip as hps
                                            inner join hr_payslip_line as hpsl on hps.id = hpsl.slip_id
                                            where hpsl.code = 'GROSS' and hps.date_from between '%s' and '%s' and hps.state!='cancel' and hps.company_id = '%s'
                                            """ % (str(month_start), str(month_end), str(self.env.company.id)))
        records = self.env.cr.dictfetchall()
        if records[0]['count']:
            return records[0]['count']
        return 0

    def get_current_month_arrears(self):
        month_start = self.current_month + relativedelta(day=1)
        month_end = self.current_month + relativedelta(day=0)
        self.env.cr.execute("""
                                            select sum(hpsl.amount),count(*) from hr_payslip as hps
                                            inner join hr_payslip_line as hpsl on hps.id = hpsl.slip_id
                                            where hpsl.code = 'ARR' and hps.date_from between '%s' and '%s' and hps.company_id = '%s'
                                            """ % (str(month_start), str(month_end), str(self.env.company.id)))
        records = self.env.cr.dictfetchall()
        records_list = []
        vals = {'arrears': records[0]['sum'] if records[0]['sum'] else 0,
                'employees_arrears': records[0]['count'] if records[0]['count'] else 0,
                }
        records_list.append(vals)
        return records_list

    def get_new_employment(self, previous, current, code="('GROSS')"):
        self.env.cr.execute(
            """select employee_id from hr_payslip where employee_id not in (select employee_id from hr_payslip where date_from <= '%s' and date_to >= '%s') and date_from <= '%s' and date_to >= '%s'"""
            % (str(previous), str(previous), str(current), str(current)))
        records = self.env.cr.dictfetchall()
        name_list = []
        for rec in records:
            employee = self.env['hr.employee'].search([('id', '=', rec['employee_id'])])
            name_list.append((employee.name, employee.id))
        self.env.cr.execute(
            f"""select * from hr_payslip_line where code in {code} and slip_id in (select id from hr_payslip where employee_id not in (select employee_id from hr_payslip where date_from <= '%s' and date_to >= '%s') and date_from <= '%s' and date_to >= '%s')"""
            % (str(previous), str(previous), str(current), str(current)))
        amount = self.env.cr.dictfetchall()
        amount_list = []
        for rec in amount:
            amount_list.append((rec['amount'], rec['employee_id']))
        data_list = []
        for name in name_list:
            for amount in amount_list:
                if name[1] == amount[1]:
                    data_list.append((name[0], amount[0]))
        if data_list:
            return data_list
        else:
            return [('', 0)]

    def get_outgoing_staff(self, previous, current, code="('GROSS')"):
        self.env.cr.execute(
            """select employee_id from hr_payslip where employee_id not in (select employee_id from hr_payslip where date_from <= '%s' and date_to >= '%s') and date_from <= '%s' and date_to >= '%s'"""
            % (str(current), str(current), str(previous), str(previous)))
        records = self.env.cr.dictfetchall()
        name_list = []
        for rec in records:
            employee = self.env['hr.employee'].search([('id', '=', rec['employee_id'])])
            name_list.append((employee.name, employee.id))
        self.env.cr.execute(
            f"""select * from hr_payslip_line where code in {code} and slip_id in (select id from hr_payslip where employee_id not in (select employee_id from hr_payslip where date_from <= '%s' and date_to >= '%s') and date_from <= '%s' and date_to >= '%s')"""
            % (str(current), str(current), str(previous), str(previous)))
        amount = self.env.cr.dictfetchall()
        amount_list = []
        for rec in amount:
            amount_list.append((rec['amount'], rec['employee_id']))
        data_list = []
        for name in name_list:
            for amount in amount_list:
                if name[1] == amount[1]:
                    data_list.append((name[0], amount[0]))
        if data_list:
            return data_list
        else:
            return [('', 0)]

    def get_leave_without_pay(self):
        month_start = self.current_month + relativedelta(day=1)
        month_end = self.current_month + relativedelta(day=0)
        self.env.cr.execute("""
                                                    select hpsl.amount,hpsl.employee_id from hr_payslip as hps
                                                    inner join hr_payslip_line as hpsl on hps.id = hpsl.slip_id
                                                    where hpsl.code = 'SPD' and hps.date_from between '%s' and '%s' and hps.company_id = '%s'
                                            """ % (str(month_start), str(month_end), str(self.env.company.id)))
        SPD = self.env.cr.dictfetchall()
        name_list = []
        for rec in SPD:
            employee = self.env['hr.employee'].search([('id', '=', rec['employee_id'])])
            name_list.append((employee.name, employee.id, rec['amount'], employee.registration_number))
        self.env.cr.execute("""
                                                            select hpsl.amount,hpsl.employee_id from hr_payslip as hps
                                                            inner join hr_payslip_line as hpsl on hps.id = hpsl.slip_id
                                                            where hpsl.code = 'LWP' and hps.date_from between '%s' and '%s' and hps.company_id = '%s'
                                            """ % (str(month_start), str(month_end), str(self.env.company.id)))
        ABS = self.env.cr.dictfetchall()
        amount_list = []
        for rec in ABS:
            amount_list.append((rec['amount'], rec['employee_id']))
        data_list = []
        for name in name_list:
            for amount in amount_list:
                if name[1] == amount[1] and amount[0] > 0:
                    data_list.append((name[0], "%0.2f" % ((amount[0] * name[2])), name[3]))
        records_list = []
        total = 0
        for s in data_list:
            total += float(s[1])
        vals = {'lwp': data_list if data_list else [('', 0, 0)],
                'total': total,
                }
        records_list.append(vals)
        return records_list

    def get_net_salary(self):
        month_start = self.current_month + relativedelta(day=1)
        month_end = self.current_month + relativedelta(day=0)
        self.env.cr.execute("""
                                            select sum(hpsl.amount) from hr_payslip as hps
                                            inner join hr_payslip_line as hpsl on hps.id = hpsl.slip_id
                                            where hpsl.code = 'NET' and hps.date_from between '%s' and '%s' and hps.company_id = '%s'
                                            """ % (str(month_start), str(month_end), str(self.env.company.id)))
        records = self.env.cr.dictfetchall()
        result_list = []
        vals = {'total': abs(records[0]['sum']) if records[0]['sum'] else 0}
        result_list.append(vals)
        return result_list

    def get_total_deductions(self):
        month_start = self.current_month + relativedelta(day=1)
        month_end = self.current_month + relativedelta(day=0)
        self.env.cr.execute("""
                                                            select sum(hpsl.amount),hpsl.name from hr_payslip as hps
                                                            inner join hr_payslip_line as hpsl on hps.id = hpsl.slip_id
                                                            where hpsl.category_id = (select id from hr_salary_rule_category where name='Deduction') and hps.date_from between '%s' and '%s' and hps.company_id = '%s' group by hpsl.name
                                            """ % (str(month_start), str(month_end), str(self.env.company.id)))
        deductions = self.env.cr.dictfetchall()
        data_list = []
        total = 0
        for data in deductions:
            if data['sum'] < 0:
                data_list.append((data['name'], "%0.2f" % (abs(data['sum']))))
            total += round(float(abs(data['sum'])))
        records_list = []
        vals = {'deduction': data_list,
                'total': total
                }
        records_list.append(vals)
        return records_list

    def get_payment_type_and_amount(self):
        month_start = self.current_month + relativedelta(day=1)
        month_end = self.current_month + relativedelta(day=0)
        self.env.cr.execute("""select sum(hpsl.amount),count(*) from hr_payslip as hps
                                            inner join hr_payslip_line as hpsl on hps.id = hpsl.slip_id 
											inner join hr_employee as hr on hps.employee_id = hr.id
											where hpsl.code = 'NET' and hr.bank_account_id is null and hps.date_from between '%s' and '%s' and hps.company_id = '%s'
                                            """ % (str(month_start), str(month_end), str(self.env.company.id)))
        cheque = self.env.cr.dictfetchall()
        self.env.cr.execute("""select sum(hpsl.amount),count(*) from hr_payslip as hps
                                                    inner join hr_payslip_line as hpsl on hps.id = hpsl.slip_id 
        											inner join hr_employee as hr on hps.employee_id = hr.id
        											where hpsl.code = 'NET' and hr.bank_account_id is not null and hps.date_from between '%s' and '%s' and hps.company_id = '%s'
                                            """ % (str(month_start), str(month_end), str(self.env.company.id)))
        bank = self.env.cr.dictfetchall()
        data_list = []
        sum_emp = 0
        amount_sum = 0
        for ba in bank:
            data_list.append(("Bank", abs(ba['sum']) if ba['sum'] else 0, ba['count']))
            sum_emp += ba['count']
            amount_sum += abs(ba['sum']) if ba['sum'] else 0
        for ch in cheque:
            data_list.append(("Cheque", abs(ch['sum']) if ch['sum'] else 0, ch['count']))
            sum_emp += ch['count']
            amount_sum += abs(ch['sum']) if ch['sum'] else 0
        records_list = []
        vals = {'payment': data_list if data_list else [('', 0, 0)],
                'sum_emp': sum_emp,
                'amount_sum': amount_sum
                }
        records_list.append(vals)
        return records_list

    def get_eobi_contributors(self):
        self.env.cr.execute("""select work_location,count(*) from hr_employee 
                            where eobi is False and company_id = '%s' and work_location is not null group by work_location"""
                            % (str(self.env.company.id)))
        eobi_contributor = self.env.cr.dictfetchall()
        data_list = []
        total = 0
        for rec in eobi_contributor:
            total += rec['count']
            data_list.append((rec['work_location'], rec['count']))
        result_list = []
        vals = {'eobi': data_list,
                'total': total}
        result_list.append(vals)
        return result_list

    def get_eobi_non_contributors(self):
        self.env.cr.execute("""select work_location,name from hr_employee 
                            where eobi is True and company_id = '%s' and work_location is not null"""
                            % (str(self.env.company.id)))
        eobi_non_contributor = self.env.cr.dictfetchall()
        data_list = []
        for rec in eobi_non_contributor:
            data_list.append((rec['work_location'], rec['name']))
        result_list = []
        vals = {'eobi': data_list,
                }
        result_list.append(vals)
        return result_list

    def total_contributors(self):
        self.env.cr.execute("""select work_location,count(*) from hr_employee 
                                    where eobi is False and company_id = '%s' and work_location is not null group by work_location"""
                            % (str(self.env.company.id)))
        eobi_contributor = self.env.cr.dictfetchall()
        data_list = []
        total = 0
        for rec in eobi_contributor:
            total += rec['count']
        data_list.append(('EOBI Contributors', total))
        self.env.cr.execute("""select count(work_location) from hr_employee 
                                    where eobi is True and company_id = '%s' and work_location is not null"""
                            % (str(self.env.company.id)))
        eobi_non_contributor = self.env.cr.dictfetchall()
        total_noneobi = 0
        for rec in eobi_non_contributor:
            total_noneobi += rec['count']
        data_list.append(('Non-EOBI Contributors', total_noneobi))
        result_list = []
        vals = {'eobi': data_list,
                'total': total + total_noneobi
                }
        result_list.append(vals)
        return result_list

    def report_Data(self):
        records_list = []
        previous_month = self.get_previous_month_gross(self.previous_month)
        previous_month_lwpa = self.get_previous_month_gross(self.previous_month, code="('LWPA')")
        previous_month_total = previous_month + previous_month_lwpa
        previous_month_total_employees = self.get_previous_total_employees(self.previous_month)
        arrears = sum(i['arrears'] for i in self.get_current_month_arrears())
        previous_month_total += arrears

        current_month = self.get_current_month_gross(self.current_month)
        current_month_lwpa = self.get_current_month_gross(self.current_month, code="('LWPA')")
        current_month_total = current_month + current_month_lwpa
        current_month_total_employees = self.get_current_total_employees(self.current_month)

        month1 = self.previous_month.strftime("%b") + '-' + str(self.previous_month)[2:4]
        month2 = self.current_month.strftime("%b") + '-' + str(self.current_month)[2:4]

        new = self.get_new_employment(self.previous_month, self.current_month)
        new_lwpa = self.get_new_employment(self.previous_month, self.current_month, code="('LWPA')")

        sum_new_lwpa = 0
        sum_new = 0
        for l in new:
            sum_new += l[1]

        for l in new_lwpa:
            sum_new_lwpa += l[1]

        sum_new_total = sum_new_lwpa + sum_new

        outgoing = self.get_outgoing_staff(self.previous_month, self.current_month)
        outgoing_lwpa = self.get_outgoing_staff(self.previous_month, self.current_month, code="('LWPA')")

        sum_old_lwpa = 0
        sum_old = 0
        for l in outgoing:
            sum_old += l[1]

        for l in outgoing_lwpa:
            sum_old_lwpa += l[1]

        outgoing_total = sum_old_lwpa + sum_old

        vals = {'month1': month1,
                'month2': month2,
                'arrears': arrears,
                'previous_gross': previous_month,
                'previous_month_lwpa': previous_month_lwpa,
                'previous_month_total': previous_month_total,
                'previous_month_total_employees': previous_month_total_employees,
                'current_gross': current_month,
                'current_month_lwpa': current_month_lwpa,
                'current_month_total': current_month_total,
                'current_month_total_employees': current_month_total_employees,
                'new_emp': new,
                'new_emp_total_gross': sum_new,
                'sum_new_lwpa': sum_new_lwpa,
                'sum_new_total': sum_new_total,
                'out_going': outgoing,
                'outgoing_emp_total_gross': sum_old,
                'sum_old_lwpa': sum_old_lwpa,
                'outgoing_total': outgoing_total,
                }
        records_list.append(vals)
        return records_list

    def get_date_name(self):
        records_list = []
        month1 = self.previous_month.strftime("%b") + '-' + str(self.previous_month)[2:4]
        month2 = self.current_month.strftime("%b") + '-' + str(self.current_month)[2:4]
        vals = {'month1': month1,
                'month2': month2}
        records_list.append(vals)
        return records_list

    def generate_tax_deduction_report(self):
        global first_day
        records_new = []
        import datetime
        if self.current_month.month in [1, 2, 3, 4, 5, 6]:
            first_day = datetime.datetime(self.current_month.year - 1, 7, 1)
        elif self.current_month.month in [7, 8, 9, 10, 11, 12]:
            first_day = datetime.datetime(self.current_month.year, 7, 1)

        if self.employee_ids:
            all_employees = self.employee_ids
        else:
            all_employees = self.env['hr.employee'].search([])

        res = self.env['hr.employee'].search([('job_id.name', '=', 'FINANCE MANAGER')], limit=1)

        for employee in all_employees:
            current_date = datetime.date.today()
            payslips_of_current_year = self.env['hr.payslip'].search(
                [('employee_id', '=', employee.id), ('state', '=', 'done'),
                 ('date_from', '>=', first_day),
                 ('date_from', '<=', self.current_month),
                 ('company_id', '=', self.env.company.id)],
                order='date_from')

            current_year_employee_contributions1 = 0
            current_year_employee_contributions2 = 0
            current_year_employee_contributions3 = 0
            current_year_employee_contributions4 = 0
            current_year_employee_contributions5 = 0
            current_year_employee_contributions6 = 0
            current_year_employee_contributions7 = 0

            for payslip in payslips_of_current_year:
                current_year_employee_contributions1 += payslip.line_ids.filtered(lambda x: x.code == 'BASIC').total
                current_year_employee_contributions2 += payslip.line_ids.filtered(lambda x: x.code == 'BONUS').total
                current_year_employee_contributions3 += payslip.line_ids.filtered(lambda x: x.code == 'HRA').total
                current_year_employee_contributions4 += payslip.line_ids.filtered(lambda x: x.code == 'COALW').total
                current_year_employee_contributions5 += payslip.line_ids.filtered(lambda x: x.code == 'UOA').total
                current_year_employee_contributions6 = payslip.line_ids.filtered(lambda x: x.code == 'TPF').total
                current_year_employee_contributions7 = payslip.line_ids.filtered(lambda x: x.code == 'TAXD').total
            car_tax = (employee.contract_id.car_cost * 5 / 100)  # 5% of car cost
            address = (str(employee.company_id.street) + ' ' if employee.company_id.street else '') + \
                      (str(employee.company_id.street2) + ' ' if employee.company_id.street2 else '') + \
                      (str(employee.company_id.city) if employee.company_id.city else '')
            y = {
                'name': employee.name,
                'cnic_no': employee.identification_id,
                'ntn_no': employee.ntn,
                'designation': employee.job_id.name,
                'location': employee.company_id.name,
                'basic': current_year_employee_contributions1,
                'special_day': 0,
                'bonus': current_year_employee_contributions2,
                'fees_commsion': 0,
                'leave_encashment': 0,
                'gratuity_annuity': 0,
                'hra': current_year_employee_contributions3,
                'coalw': current_year_employee_contributions4,
                'leave_fare_assistance': 0,
                'special_allowance': 0,
                'uoa': current_year_employee_contributions5,
                'conveynce_used': car_tax,
                'taxpf': current_year_employee_contributions6,
                'start_year': first_day,
                'end_year': self.current_month,
                'print_date': current_date,
                'company_address': address,
                'company_ntn': employee.company_id.vat,
                'finance_manager': res.name,
                'tax_deducted': current_year_employee_contributions7,
                'currency_ids': payslips_of_current_year.company_id.currency_id.name,
            }

            records_new.append(y)
        return records_new

    def get_fiscal_date_start(self):
        fiscal_year_start_str = (str(date.today().year - 1) if date.today().month < 7 else str(
            date.today().year)) + '-07-01'
        return datetime.strptime(fiscal_year_start_str, '%Y-%m-%d').date()

    def get_fiscal_date_end(self):
        fiscal_year_end_str = (str(date.today().year) if date.today().month < 7 else str(
            date.today().year + 1)) + '-06-30'
        return datetime.strptime(fiscal_year_end_str, '%Y-%m-%d').date()

    def payslip_amount_PF(self):
        start_dat = self.get_fiscal_date_start()
        end_date = self.get_fiscal_date_end()
        multiple_employees = []
        for rec in self:
            positions = self.env['hr.employee'].search([('job_id', '=', 'FINANCE MANAGER')])
            for employes in rec.employee_ids:
                payslips = rec.env['hr.payslip'].search(
                    [('employee_id', '=', employes.id), ('date_from', '>=', str(start_dat)), ('state', '=', 'done'),
                     ('date_from', '<=', str(end_date))])
                total = 0
                for payslip in payslips:
                    total += payslip.line_ids.filtered(lambda x: x.code == 'PF').total
                vals = {
                    'name': employes.name,
                    'total': abs(total),
                    'position': positions.name,
                }
                multiple_employees.append(vals)
        return multiple_employees

    def performance_appraisal_report(self):
        records_data = []
        all_employees = self.employee_ids or self.env['hr.employee'].search([])

        first = date(2020, 1, 1)
        last = date(2050, 12, 31)

        for employee in all_employees:
            employee_wage = self.env['hr.contract'].search([('employee_id', '=', employee.id)]).wage

            sl_type_id = self.env['hr.leave.type'].search(
                [('company_id', '=', employee.company_id.id), ('code', '=', 'SL')]).id
            cl_type_id = self.env['hr.leave.type'].search(
                [('company_id', '=', employee.company_id.id), ('code', '=', 'CL')]).id
            pl_type_id = self.env['hr.leave.type'].search(
                [('company_id', '=', employee.company_id.id), ('code', '=', 'PL')]).id

            employee_leaves = self.env['hr.leave'].search([
                ('employee_id', '=', employee.id), ('date_from', '>=', first), ('date_to', '<=', last),
                ('state', '=', 'validate')
            ])
            employee_allocations = self.env['hr.leave.allocation'].search([
                ('employee_id', '=', employee.id), ('write_date', '>=', first), ('write_date', '<=', last),
                ('state', '=', 'validate')
            ])
            sick_leaves_count = sum(
                employee_leaves.filtered(lambda x: x.holiday_status_id.id == sl_type_id).mapped('number_of_days'))
            casual_leaves_count = sum(
                employee_leaves.filtered(lambda x: x.holiday_status_id.id == cl_type_id).mapped('number_of_days'))
            annual_leaves_count = sum(
                employee_leaves.filtered(lambda x: x.holiday_status_id.id == pl_type_id).mapped('number_of_days'))
            annual_allocation_count = sum(
                employee_allocations.filtered(lambda x: x.holiday_status_id.id == pl_type_id).mapped('number_of_days'))

            # degree = employee.academic_ids and employee.academic_ids.mapped('degree_id')[0].name

            y = {
                'name': str(employee.registration_number) + ' ' + str(employee.name),
                'birthday': employee.birthday,
                'grade': employee.contract_id.x_studio_grade,
                'department': employee.department_id.name,
                'position': employee.job_id.name,
                'joining_date': employee.appointment_date,
                # 'degree': degree,
                'gross_salary': employee_wage,
                'year_end': self.current_month,
                'sick_leave': sick_leaves_count,
                'casual_leave': casual_leaves_count,
                'earned_leave_balance': annual_allocation_count - annual_leaves_count,
                'personal_file_no': employee.x_studio_personal_file_number,
                'location': employee.work_location,
                'company_name': employee.company_id.name,
            }

            records_data.append(y)
        return records_data

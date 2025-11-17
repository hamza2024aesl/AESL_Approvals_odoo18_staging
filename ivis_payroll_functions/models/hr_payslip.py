from datetime import datetime

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.tools import date_utils, format_date


class HrPayslipInherit(models.Model):
    _inherit = 'hr.payslip'

    input_lines = fields.One2many('hr.payslip.recurring', 'line')

    def compute_sheet(self):
        res = super(HrPayslipInherit, self).compute_sheet()
        return res

    @api.onchange('employee_id', 'struct_id', 'contract_id', 'date_from', 'date_to')
    def _onchange_employee(self):
        if (not self.employee_id) or (not self.date_from) or (not self.date_to):
            return

        employee = self.employee_id
        date_from = self.date_from
        date_to = self.date_to

        self.company_id = employee.company_id
        # if not self.contract_id or self.employee_id != self.contract_id.employee_id:  # Add a default contract if not already defined
        contracts = employee._get_contracts(date_from, date_to)

        # if not contracts or not contracts[0].structure_type_id.default_struct_id:
        #     self.contract_id = False
        #     self.struct_id = False
        #     return
        if contracts:
            self.contract_id = contracts[0]
            self.struct_id = contracts[0].structure_type_id.default_struct_id

        payslip_name = self.struct_id.payslip_name or _('Salary Slip')
        self.name = '%s - %s - %s' % (
            payslip_name, self.employee_id.name or '', format_date(self.env, self.date_from, date_format="MMMM y"))

        if date_to > date_utils.end_of(fields.Date.today(), 'month'):
            self.warning_message = _(
                "This payslip can be erroneous! Work entries may not be generated for the period from %s to %s." %
                (date_utils.add(date_utils.end_of(fields.Date.today(), 'month'), days=1), date_to))
        else:
            self.warning_message = False

        self.worked_days_line_ids = self._get_new_worked_days_lines()

    def get_allied_lwp_days(self):
        previous_month = self.date_from + relativedelta(months=-1) + relativedelta(day=16)
        current_month = self.date_from + relativedelta(day=15)
        attendences = self.env['hr.attendance'].search([('attendance_date', '>=', previous_month),
                                                        ('attendance_date', '<=', current_month),
                                                        ('on_leave', '=', False),
                                                        '|',
                                                        ('status2', '=', 'absent'),
                                                        ('attendance_status', 'in', ['3', '5']),
                                                        ('employee_id', '=', self.employee_id.id)])
        x = list()
        for attendence in attendences:
            d = {
                'date': attendence.attendance_date.strftime('%A, %d-%m-%Y'),
                'amt': 0.5 if attendence.attendance_status == '3' else 1
            }
            x.append(d)
        return x

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(HrPayslipInherit, self).fields_view_get(
            view_id=view_id,
            view_type=view_type,
            toolbar=toolbar,
            submenu=submenu)

        report_account_invoice_bill = self.env.ref('hr_payroll.action_report_payslip')

        for print_submenu in res.get('toolbar', {}).get('print', []):
            if print_submenu['id'] == report_account_invoice_bill.id:
                res['toolbar']['print'].remove(print_submenu)
        return res

    def kpk_professional_tax(self, date_to):
        if str(date_to) == '06/30/2019':
            return (3000)

    def fetch_service_period(self, emp_id):
        rec = self.env['hr.contract'].search([('employee_id', '=', emp_id)])
        start_date = rec[0].date_start
        fmt = '%Y-%m-%d'

        d1 = datetime.strptime(str(start_date), fmt)
        d2 = datetime.strptime(str(self.date_to), fmt)

        relative_delta = relativedelta(d2, d1)

        days = str(relative_delta.days)
        months = str(relative_delta.months)
        years = str(relative_delta.years)

        if days == False or days == None:
            days = 0
        if months == False or months == None:
            months = 0
        if years == False or years == None:
            years = 0
        return str(years) + " Year(s), " + str(months) + " Month(s), " + str(days) + " Day(s)"

    def payslip(self, slip_id, category_name):
        user_lang = self.env.user.lang  # Get current user's language dynamically
        category_name = category_name.title()  # Ensure proper case

        total_field = "-hsl.total" if category_name == "Deduction" else "hsl.total"

        query = f"""
            SELECT hsl.name, {total_field} AS total 
            FROM hr_payslip_line AS hsl 
            INNER JOIN hr_salary_rule AS hsr ON hsl.salary_rule_id = hsr.id 
            INNER JOIN hr_salary_rule_category AS hsrc ON hsr.category_id = hsrc.id
            WHERE hsl.slip_id = %s 
            AND hsrc.name->>%s = %s 
            AND hsr.appears_on_payslip = TRUE 
            ORDER BY hsrc.name->>%s ASC, hsr.sequence ASC
        """

        self.env.cr.execute(query, (slip_id, user_lang, category_name, user_lang))
        data = self.env.cr.dictfetchall()

        return data if data else 0

    def rule_by_code(self, slip_id, code):
        self.env.cr.execute("""
            select hsl.name, hsl.code, hsl.total
            from hr_payslip_line as hsl
            where hsl.slip_id=%s and hsl.code='%s'
        """ % (slip_id, code))
        data = self.env.cr.dictfetchall()
        if len(data) > 0:
            return data
        else:
            return 0

    @api.onchange('struct_id')
    def get_otherInput(self):
        self.input_line_ids = False
        records = self.env['hr.payslip.input.type'].search([('struct_ids', '=', self.struct_id.id)])

        re = []
        for rec in records:
            r = {'input_type_id': rec.id, 'code': rec.code, 'payslip_id': self.id}
            re.append((0, 0, r))
        return {'value': {'input_line_ids': re}}

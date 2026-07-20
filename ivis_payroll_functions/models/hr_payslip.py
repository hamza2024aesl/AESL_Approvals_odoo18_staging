from datetime import datetime, time
import calendar
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.tools import date_utils, format_date


class HrPayslipInherit(models.Model):
    _inherit = 'hr.payslip'

    input_lines = fields.One2many('hr.payslip.recurring', 'line')

    # def compute_sheet(self):
    #     res = super(HrPayslipInherit, self).compute_sheet()
    #     return res

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
        prev_month = self.date_from.month - 1 or 12
        year = self.date_from.year if self.date_from.month > 1 else self.date_from.year - 1
        date_from = fields.Date.from_string(f"{year}-{prev_month:02d}-01")

        last_day = calendar.monthrange(date_from.year, date_from.month)[1]
        date_to = date_from.replace(day=last_day)

        period_start = date_from
        period_end = date_to
        start_dt = datetime.combine(period_start, time.min)
        end_dt = datetime.combine(period_end, time.max)
        lwp_type = self.env['hr.leave.type'].search([('name', '=', 'LWP')], limit=1)
        if not lwp_type:
            return []
        leaves = self.env['hr.leave'].search([
            ('employee_id', '=', self.employee_id.id),
            ('holiday_status_id', '=', lwp_type.id),
            ('state', '=', 'validate'),
            ('request_date_from', '<=', end_dt),
            ('request_date_to', '>=', start_dt),
        ], order='request_date_from asc')
        rows = []
        for leave in leaves:
            lf = max(leave.request_date_from, period_start)
            lt = min(leave.request_date_to, period_end)
            rows.append({
                'date': lf.strftime('%A, %d-%m-%Y'),
                'amt': leave.duration_display,
            })
        return rows

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
        user_lang = self.env.user.lang or 'en_US'
        total_field = "-hsl.total" if category_name == "Deduction" else "hsl.total"

        query = f"""
               SELECT
                   hsr.name->>'{user_lang}' AS name,
                   hsr.sequence,
                   COALESCE(SUM(hsl.total), 0) AS total
               FROM hr_salary_rule AS hsr
               LEFT JOIN hr_payslip_line AS hsl
                   ON hsl.salary_rule_id = hsr.id
                   AND hsl.slip_id = %s
               WHERE hsr.code = %s
                 AND hsr.appears_on_payslip = TRUE
               GROUP BY hsr.name->>'{user_lang}', hsr.sequence
               ORDER BY hsr.sequence ASC;
           """

        self.env.cr.execute(query, (slip_id, category_name))
        data = self.env.cr.dictfetchall()

        return data if data else [{'name': category_name, 'total': 0}]

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

    def get_pf_balance_as_of(self):
        """PF balance as of this specific payslip's date (ignoring future months PF)."""
        self.ensure_one()
        payslip = self

        employee = payslip.employee_id

        final_pf = (
                (employee.total or 0)
                + (employee.pf_employee or 0)
                + (employee.pf_employer or 0)
                + (employee.pf_interest or 0)
        )

        future_slips = self.env['hr.payslip'].search([
            ('employee_id', '=', employee.id),
            ('date_from', '>', payslip.date_to),
            ('state', 'in', ['done', 'paid'])
        ])
        future_pf = 0.0
        if future_slips:
            future_pf_lines = self.env['hr.payslip.line'].search([
                ('slip_id', 'in', future_slips.ids),
                ('code', 'in', ['PF_EMPLOYEE', 'PF_EMPLOYER'])
            ])
            future_pf = sum(future_pf_lines.mapped('total'))

        return final_pf - future_pf

    def compute_sheet(self):
        if self.env.context.get('salary_simulation'):
            return super().compute_sheet()

        if self.filtered(lambda p: p.is_regular):
            employees = self.mapped('employee_id')
            leaves = self.env['hr.leave'].search([
                ('employee_id', 'in', employees.ids),
                ('state', '!=', 'refuse'),
            ])

            dates = self.mapped('date_to')
            max_date = datetime.combine(max(dates), datetime.max.time())

            leaves_to_green = leaves.filtered(
                lambda l: l.payslip_state != 'blocked' and l.date_to <= max_date
            )
            leaves_to_green.write({'payslip_state': 'done'})

        return super(HrPayslipInherit, self.with_context(salary_simulation=True)).compute_sheet()

    def _get_payslip_lines(self):
        for payslip in self:
            if not payslip.contract_id:
                # Find contract that overlaps any part of the payslip period,
                # including ones that expired mid-period
                contract = self.env['hr.contract'].search([
                    ('employee_id', '=', payslip.employee_id.id),
                    ('date_start', '<=', payslip.date_to),
                    ('state', 'in', ['open', 'close']),
                    '|',
                        ('date_end', '=', False),
                        ('date_end', '>=', payslip.date_from),
                ], order='date_end desc', limit=1)
                if contract:
                    payslip.contract_id = contract
        return super()._get_payslip_lines()

from dateutil.relativedelta import relativedelta
from odoo import api, models, fields


class HrContractInherit(models.Model):
    _inherit = 'hr.contract'

    date_start = fields.Date('Start Date', required=True, default=fields.Date.today,
                             help="Start date of the contract.")
    trial_date_end = fields.Date('End of Trial Period',
                                 help="End date of the trial period (if there is one).")
    employee_account = fields.One2many('account.salary', 'contract_id')
    probation_period = fields.Selection([('threemonths', '3 Months'), ('sixmonths', '6 Months')])
    notice_period = fields.Boolean(string="Notice Period")
    x_studio_grade = fields.Char(string="Grade")

    @api.onchange('probation_period')
    def trial_date_calc(self):
        if self.date_start:
            date_start_dt = fields.Datetime.from_string(self.date_start)
            if self.probation_period == 'threemonths':
                dt = date_start_dt + relativedelta(months=3)
                self.trial_date_end = fields.Datetime.to_string(dt)
            elif self.probation_period == 'sixmonths':
                dt = date_start_dt + relativedelta(months=6)
                self.trial_date_end = fields.Datetime.to_string(dt)

    @api.model_create_multi
    def create(self, vals):
        res = super(HrContractInherit, self).create(vals)
        res.employee_id.dates_line()
        return res

    # @api.multi
    def write(self, vals):
        res = super(HrContractInherit, self).write(vals)
        self.employee_id.dates_line()
        return res

    @api.onchange('notice_period')
    def notice_period_change(self):
        if self.state == 'open':
            self.employee_id.notice_period = self.notice_period

    @api.model
    def default_get(self, fields_list):
        res = super(HrContractInherit, self).default_get(fields_list)
        employee_id = self.env.context.get('default_employee_id')
        if employee_id:
            employee = self.env['hr.employee'].browse(employee_id)
            if employee:
                if 'department_id' in fields_list:
                    res['department_id'] = employee.department_id.id or False
                if 'job_id' in fields_list:
                    res['job_id'] = employee.job_id.id or False
                if 'company_id' in fields_list:
                    res['company_id'] = employee.company_id.id or False
                if 'x_studio_grade' in fields_list:
                    res['x_studio_grade'] = employee.x_studio_grade or False
        return res

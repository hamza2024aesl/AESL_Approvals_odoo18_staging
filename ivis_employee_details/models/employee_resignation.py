from dateutil.relativedelta import relativedelta

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class EmployeeResignation(models.Model):
    _name = 'employee.resignation'
    _description = "Resignation"
    company_id = fields.Many2one('res.company', string='Companys', index=True,
                                 default=lambda self: self.env.user.company_id)
    emp_name = fields.Many2one('hr.employee', string="Name")
    # emp_image = fields.Binary(related='emp_name.image')
    emp_designation = fields.Many2one(related='emp_name.job_id', string='Designation')
    company = fields.Many2one(related='emp_name.company_id', string='Company')
    emp_division = fields.Char(related='emp_name.division', string='Division')
    station = fields.Char(related='emp_name.work_location_name', string='Station')
    appointment_date = fields.Date(string="Appointment Date", related='emp_name.appointment_date')
    resignation_date = fields.Date(string="Resignation_date")
    # leaving_date = fields.Date(related='emp_name.exit_date', string='Last Date')
    department = fields.Many2one(related='emp_name.department_id', string="Department")
    immediate_boss = fields.Many2one(related='emp_name.parent_id', string="Immediate Boss")
    leaving_status = fields.Selection([('resignation', 'Resignation'), ('termination', 'Termination')],
                                      string='Leaving type', required=True)
    # company_property = fields.Many2many('account.asset.asset', 'employee_asset_rel', 'employee_id', 'asset_id',
    #                                     string="Company Property")
    exit_date = fields.Char(string='Exit Date')
    emp_badge = fields.Char(related='emp_name.barcode')
    is_uniform = fields.Selection([('blocked', 'Have Uniform'), ('done', 'Returned')], default='done', string='Uniform')
    has_locker_key = fields.Selection([('blocked', 'Has Locker Keys'), ('done', 'Returned')], default='done',
                                      string='Locker key')
    has_company_vehicle = fields.Selection([('blocked', 'Has Vehicle'), ('done', 'Returned')], default='done',
                                           string='Company vehicle')
    others = fields.Selection([('blocked', 'Yes'), ('done', 'No')], default='done', string='Others')
    company_card = fields.Selection([('blocked', 'Have Card'), ('done', 'Returned')], string='Company ID card',
                                    default='done')
    hr_remarks = fields.Text(string="HR Dept.Remarks")
    boss_remarks = fields.Text(string="Immediate Boss Remarks")
    gm_remark = fields.Text(string="GM Remarks")
    gd_remark = fields.Text(string="GD Remarks")
    other_note = fields.Text()
    note = fields.Text()
    description = fields.Text('HR Remarks')
    state = fields.Selection(
        [('draft', 'Draft'), ('buh', 'Waiting for First approval'), ('vp', 'Waiting for Second Approval'),
         ('final_approval', 'Final Approval'), ('clearance_approved', 'Clearance Approved'), ('approved', 'Approved'),
         ('final_settlemnet', 'Final Settelment Approved')], string='State', default='draft')
    clearance_employee = fields.One2many('employee.cl', 'employee_clearance', string='Clearance Checklist')

    _sql_constraints = [
        ('name_uniq', 'unique(emp_name)', 'Resignation form of this employee already exists!!'),
    ]
    
    @api.onchange('resignation_date')
    def calculate_exit_date(self):
        for rec in self:
            if rec.resignation_date:
                dt = rec.resignation_date + relativedelta(months=3)
                rec.exit_date = dt

    def buh_clearance(self):
        self.state = 'buh'
        self.emp_name.resignation_date = self.resignation_date

    def vp_clearance(self):
        self.state = 'vp'

    def fa_clearance(self):
        self.state = 'final_approval'
        self.emp_name.exit_date = self.exit_date

    def approve_clearance(self):
        for rec in self:
            contract = self.env['hr.contract'].search([('employee_id', '=', rec.emp_name.id), ('state', '=', 'open')])
            if not contract:
                raise ValidationError("No contract in  Runing state ")
            else:
                rec.state = 'clearance_approved'

    def clearance_received(self):
        for approvals in self.clearance_employee:
            if (approvals.received in 'no'):
                raise ValidationError('All items should be received')
            else:
                self.state = 'approved'

    def name_get(self):
        result = []
        for record in self:
            if self.emp_name.barcode:
                name = 'Employee Clearance Form of ' + record.emp_name.name + '-' + str(self.emp_name.barcode)
            else:
                name = 'Employee Clearance Form of ' + record.emp_name.name
            result.append((record.id, name))
        return result

    # @api.onchange('emp_name')
    # def check_name(self):
    #     if self.emp_name:
    #         emp_contract = self.env['hr.contract'].search([('employee_id', '=', self.emp_name.id), ('state', '=', 'open')], limit=1)
    #         self.exit_date = emp_contract.date_end

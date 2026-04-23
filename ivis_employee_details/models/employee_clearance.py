from odoo import models, fields


class EmployeeClearance(models.Model):
    _name = 'employee.clearance'
    _description = "Clearance"

    emp_name = fields.Many2one('hr.employee', string="Name")
    # emp_image = fields.Binary(related='emp_name.image')
    emp_designation = fields.Many2one(related='emp_name.job_id', string='Designation')
    company = fields.Many2one(related='emp_name.company_id', string='Company')
    emp_division = fields.Char(related='emp_name.division', string='Division')
    station = fields.Char(related='emp_name.work_location_name', string='Station')
    appointment_date = fields.Date(related='emp_name.appointment_date', string="Appointment Date")
    leaving_date = fields.Date(related='emp_name.exit_date', string='Last Date')
    department = fields.Many2one(related='emp_name.department_id', string="Department")
    immediate_boss = fields.Many2one(related='emp_name.parent_id', string="Immediate Boss")
    leaving_status = fields.Selection(related='emp_name.leave_type', string='Leaving type')
    # company_property = fields.Many2many('account.asset.asset','employee_asset_rel', 'employee_id', 'asset_id', string="Company Property")
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
         ('final_approval', 'Final Approval'), ('approved', 'Approved')], string='State', default='draft')

    def buh_clearance(self):
        self.state = 'buh'

    def vp_clearance(self):
        self.state = 'vp'

    def fa_clearance(self):
        self.state = 'final_approval'

    def approve_clearance(self):
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

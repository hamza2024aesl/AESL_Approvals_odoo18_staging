from dateutil.relativedelta import relativedelta
from odoo import fields, models, api, exceptions
from odoo.exceptions import UserError


class my_change_request(models.Model):
    _name = 'my.change.request'
    _inherit = ['mail.thread']

    state = fields.Selection([
        ('new', 'New'),
        ('draft', 'Draft'),
        ('first', 'Waiting for Manager'),
        ('second', 'Waiting for HR'),
        ('done', 'Done'),
        ('rejected', 'Rejected'),
    ], string='Status', readonly=True, copy=False, index=True, track_visibility='onchange', default='new')
    reason = fields.Selection([('change_shift', 'Shift Change'),
                               ('at_bank', 'At Bank'),
                               ('forgot_to_mark', "Forgot to Mark"),
                               ('out_station', 'Out Station Duty'),
                               ('others', 'Others'),
                               ('duplicate', 'Ignore'),
                               ('ot_adjustment', 'Overtime Adjustment')
                               ])

    def _calc_att(self):
        c_id = self._context.get('active_id', False)
        CurrentAtt = self.env['hr.attendance'].search([('id', '=', c_id)])
        return CurrentAtt

    name = fields.Char()
    description = fields.Text(String="Description", track_visibility='onchange')
    attendance_id = fields.Many2one('hr.attendance', default=_calc_att)
    department_id = fields.Many2one('hr.department', related="attendance_id.employee_id.department_id", store=True)
    employee_id = fields.Many2one('hr.employee', related='attendance_id.employee_id', store=True)
    manager = fields.Many2one('hr.employee', compute='get_my_manager', default=False, store=True)
    my_manager = fields.Boolean(compute="my_manager_compute")
    new_check_in = fields.Datetime("New Check In")
    new_check_out = fields.Datetime("New Check Out")
    new_shift = fields.Many2one('resource.calendar', string='New Shift')

    @api.onchange('attendance_id')
    def defaultaAttendance(self):
        if self.attendance_id:
            self.new_check_in = self.attendance_id.check_in
            self.new_check_out = self.attendance_id.check_out
            self.new_shift = self.attendance_id.current_shift.id

    @api.depends('attendance_id.employee_id')
    def get_my_manager(self):
        self.manager = self.sudo().attendance_id.employee_id.parent_id.id

    def my_manager_compute(self):
        if self.sudo().manager.user_id:
            if self.sudo().manager.user_id.id == self.env.uid:
                self.my_manager = True
                return
        self.my_manager = False

    def generate_request(self):
        if self.new_check_out <= self.new_check_in:
            raise UserError(('Error!'), ('Check In time must preceed the Check Out time!'))

        if not self.name:
            name = str(self.attendance_id.employee_id.name) + " from " + str(self.new_check_in + relativedelta(hours=5))
            if self.attendance_id.check_out:
                name = name + " to " + str(self.new_check_out + relativedelta(hours=5))

            self.name = name
        self.attendance_id.write({'change_request': self.id, 'request_created': True})
        self.state = "first"

    def copy(self):
        raise exceptions.UserError('You cannot duplicate a change request, because it is unique for every attendance.')

    def save_request(self):
        if self.new_check_out <= self.new_check_in:
            raise UserError(('Error!'), ('Check In time must preceed the Check Out time!'))

        name = str(self.attendance_id.employee_id.name) + " from " + str(self.attendance_id.check_in)
        if self.attendance_id.check_out:
            name = name + " to " + str(self.attendance_id.check_out)

        self.name = name

        self.attendance_id.write({'change_request': self.id, 'request_created': True})
        self.state = "draft"

    def vlidate_request_manager(self):
        self.state = 'second'

    def vlidate_request_hr(self):
        if not (self.new_check_in or self.new_check_out):
            raise UserError(('Error!'), ('You must enter either \"New Check In\" time or \"New Check Out\" time.'))
        # < Muhammad Usama Imran
        if self.reason == 'duplicate':
            self.attendance_id.isduplicate = True
            self.state = 'done'
            return
        if self.new_check_in:
            self.attendance_id.new_check_in = self.attendance_id.check_in
            self.attendance_id.check_in = self.new_check_in  # New check-in is old check-in
        if self.new_check_out:
            self.attendance_id.new_check_out = self.attendance_id.check_out
            self.attendance_id.check_out = self.new_check_out  # New check-out is old check-out
        if self.new_shift:
            self.attendance_id.new_shift = self.attendance_id.current_shift
            self.attendance_id.current_shift = self.new_shift
        if self.attendance_id.previous_dates:
            self.attendance_id.previous_dates = False
        self.state = 'done'

    # Muhammad Usama Imran >

    def reject_request_manager(self):
        self.state = 'rejected'

    def reject_request_hr(self):
        self.state = 'rejected'

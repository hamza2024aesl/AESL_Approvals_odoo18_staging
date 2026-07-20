from odoo import fields, models, api
from odoo.exceptions import UserError


class my_change_request(models.Model):
    _name = 'my.change.request'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']

    state = fields.Selection([
        ('new', 'New'),
        ('draft', 'Draft'),
        ('first', 'Waiting for Manager'),
        ('second', 'Waiting for HR'),
        ('done', 'Done'),
        ('rejected', 'Rejected'),
    ], string='Status', readonly=True, copy=False, index=True, track_visibility='onchange', default='new')
    reason = fields.Selection([
        ('at_bank', 'At Bank'),
        ('at_forum_office', 'At Forum Office'),
        ('forgot_to_mark', "Forgot to Mark"),
        ('at_kaat_office', "At KAAT Office"),
        ('at_director_residence', "At Director Residence"),
        ('at_garden', "At Garden Office")
    ])

    def _calc_att(self):
        c_id = self._context.get('active_id', False)
        CurrentAtt = self.env['hr.attendance'].search([('id', '=', c_id)])

        return CurrentAtt

    name = fields.Char()
    description = fields.Text(String="Description", track_visibility='onchange')
    attendance_id = fields.Many2one('hr.attendance', default=_calc_att)
    manager = fields.Many2one('hr.employee', related="attendance_id.employee_id.parent_id", store=True)
    my_manager = fields.Boolean(compute="my_manager_compute")

    new_check_in = fields.Datetime("New Check In")
    new_check_out = fields.Datetime("New Check Out")

    @api.onchange('attendance_id')
    def defaultaAttendance(self):
        if self.attendance_id:
            self.new_check_in = self.attendance_id.check_in
            self.new_check_out = self.attendance_id.check_out

    def my_manager_compute(self):
        if self.manager.user_id:
            if self.manager.user_id.id == self.env.uid:
                self.my_manager = True
                return
        self.my_manager = False

    def generate_request(self):

        if self.new_check_out <= self.new_check_in:
            raise UserError(('Error!'), ('Check In time must preceed the Check Out time!'))

        if not self.name:
            name = str(self.attendance_id.employee_id.name) + " from " + str(self.attendance_id.check_in)
            if self.attendance_id.check_out:
                name = name + " to " + str(self.attendance_id.check_out)

            self.name = name
        self.attendance_id.write({'change_request': self.id, 'request_created': True})
        self.state = "first"

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

        if self.new_check_in and not self.new_check_out:
            self.attendance_id.new_check_in = self.new_check_in
            self.attendance_id.updateRecord()
            self.state = 'done'

        elif self.new_check_out and not self.new_check_in:
            self.attendance_id.new_check_out = self.new_check_out
            self.attendance_id.updateRecord()
            self.state = 'done'
        else:
            self.attendance_id.new_check_in = self.new_check_in
            self.attendance_id.new_check_out = self.new_check_out
            self.attendance_id.updateRecord()
            self.state = 'done'

    def reject_request_manager(self):
        self.state = 'rejected'

    def reject_request_hr(self):
        self.state = 'rejected'

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HolidaysExtend_Class(models.Model):
    _inherit = "hr.leave"

    month = fields.Integer('Month')
    year = fields.Integer('Year')


class resourceCalendar(models.Model):
    _inherit = 'resource.calendar'

    in_policy_id = fields.One2many('working.schedule.in', 'working_schedule_in')
    out_policy_id = fields.One2many('working.schedule.out', 'working_schedule_out')
    compensatory_hours = fields.Integer('Compensatory Hours', required=False, default=0)
    shift = fields.Selection([('day', 'Day'), ('night', 'Night')], string="Shift", required=False)
    missed_in_out_duration = fields.Float(string="Missed In/Out")
    overtime_start = fields.Float('Overtime Start Duration',
                                  help="After how much duration the working time should be considered as overtime. (inclusive)")
    exclude = fields.Boolean('Exclude?')

    @api.onchange('in_policy_id')
    def check_in_policy(self):
        for rec in self:
            lines_list = []
            time_to_list = []
            for l in rec.in_policy_id:
                if l.status:
                    if l.time_from not in lines_list:
                        lines_list.append(l.time_from)
                    elif l.time_from in lines_list:
                        raise ValidationError(_("Warning! You are overlapping From Duration in more than one record"))
                    if l.time_to not in time_to_list:
                        time_to_list.append(l.time_to)
                    elif l.time_to in time_to_list:
                        raise ValidationError(_("Warning! You are overlapping To Duration in more than one record"))

    @api.onchange('out_policy_id')
    def check_out_policy(self):
        for rec in self:
            lines_list = []
            time_to_list = []
            for l in rec.out_policy_id:
                if l.status:
                    if l.time_from not in lines_list:
                        lines_list.append(l.time_from)
                    elif l.time_from in lines_list:
                        raise ValidationError(_("Warning! You are overlapping From Duration in more than one record"))
                    if l.time_to not in time_to_list:
                        time_to_list.append(l.time_to)
                    elif l.time_to in time_to_list:
                        raise ValidationError(_("Warning! You are overlapping To Duration in more than one record"))

    def get_attendances_for_weekday(self, day_dt):
        """ Given a day datetime, return matching attendances """
        self.ensure_one()
        weekday = day_dt.weekday()
        attendances = self.env['resource.calendar.attendance']

        for attendance in self.attendance_ids.filtered(
                lambda att:
                int(att.dayofweek) == weekday and
                not (att.date_from and fields.Date.from_string(att.date_from) > day_dt.date()) and
                not (att.date_to and fields.Date.from_string(att.date_to) < day_dt.date())):
            attendances |= attendance
        return attendances


class workingScheduleIn(models.Model):
    _name = 'working.schedule.in'

    working_schedule_in = fields.Many2one('resource.calendar', ondelete="cascade")
    time_from = fields.Float('From Duration (HH:MM)')
    time_to = fields.Float('To Duration (HH:MM)')
    status = fields.Selection(
        [('0', 'OK'), ('1', 'Late-In'), ('2', 'Quarter-Day'), ('3', 'Half-Day'), ('4', 'Tri-Quarter'),
         ('5', 'Full-Day')])
    action = fields.Float('Action')


class workingScheduleOut(models.Model):
    _name = 'working.schedule.out'

    working_schedule_out = fields.Many2one('resource.calendar', ondelete="cascade")
    time_from = fields.Float('From Duration (HH:MM)')
    time_to = fields.Float('To Duration (HH:MM)')
    status = fields.Selection(
        [('0', 'OK'), ('1', 'Early-Out'), ('2', 'Quarter-Day'), ('3', 'Half-Day'), ('4', 'Tri-Quarter'),
         ('5', 'Full-Day')])
    action = fields.Float('Action')

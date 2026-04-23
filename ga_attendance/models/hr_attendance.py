from datetime import datetime, timedelta

from odoo import models, fields, api
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class Attendancelog(models.Model):
    _name = 'ga.attendance.log'

    employee = fields.Many2one('hr.employee')
    punching_date = fields.Date()


class hrAttendance(models.Model):
    _inherit = 'hr.attendance'

    working_hours = fields.Float('Working Time (minutes)', compute='_compute_worked_hours', default=False, store=True)
    standard_hours = fields.Float('Standard Time (minutes)', compute='_compute_worked_hours', default=False, store=True)
    over_time = fields.Float('Over/Under Time (minutes)', compute='_compute_worked_hours', default=False, store=True)
    over_time_hr = fields.Float('Over Time (Hrs)', compute='_compute_worked_hours', default=False, store=True)
    normal_working_hours = fields.Float('Standard Working Hours', compute='_compute_worked_hours', default=False,
                                        store=True)
    late_in_time = fields.Float('Late In Time', compute='_get_in_status', default=False, store=True)
    in_status = fields.Selection(
        [('0', 'Ok'), ('1', 'Late-In'), ('2', 'Quarter-Day'), ('3', 'Half-Day'), ('4', 'Tri-Quarter'),
         ('5', 'Full-Day')], 'In status', compute='_get_in_status', default=False, store=True)
    early_time_out = fields.Float('Early Out Time', compute='_get_out_status', default=False, store=True)
    out_status = fields.Selection(
        [('0', 'Ok'), ('1', 'Early-Out'), ('2', 'Quarter-Day'), ('3', 'Half-Day'), ('4', 'Tri-Quarter'),
         ('5', 'Full-Day')], 'Out status', compute='_get_out_status', default=False, store=True)
    attendance_status = fields.Selection(
        [('0', 'Ok'), ('1', 'Late'), ('2', 'Quarter-Day'), ('3', 'Half-Day'), ('4', 'Tri-Quarter'), ('5', 'Full-Day')],
        'Attendance status', compute='_get_attendance_status_ga', default=False, store=True)
    extra_day = fields.Selection([('yes', 'Yes'), ('no', 'No')], 'Extra Day')
    compensatory = fields.Selection([('yes', 'Yes'), ('no', 'No')], 'Compensatory')
    compensatory_leave = fields.Integer('Compensatory Leave')
    penalty = fields.Float('Penalty')
    status2 = fields.Selection([('present', 'Present'), ('absent', 'Absent'), ('off_day', 'Off-Day'),
                                ('missed_check_out', 'Missed to Check Out'), ('missed_check_in', 'Missed to Check In')],
                               string='Status', default=False)
    status = fields.Selection([('present', 'Present'), ('absent', 'Absent'), ('off_day', 'Off-Day'),
                               ('missed_check', 'Missed to Check In/Out')], string='Status', default=False,
                              compute='_get_status', store=True)
    current_shift = fields.Many2one('resource.calendar', string='Current Shift')
    new_shift = fields.Many2one('resource.calendar', string='Old Shift')
    employee_id = fields.Many2one('hr.employee', string="Employee")
    check_in = fields.Datetime(required=False, default=False)
    check_out = fields.Datetime(string="Check Out")
    all_records = fields.Char('Other Records', help="It is a technical field.", compute='check_between_times',
                              store=True)
    toggle = fields.Boolean('Compute')
    department_id = fields.Many2one('hr.department', string="Department", related="employee_id.department_id",
                                    store=True)

    # Change Request related work
    new_check_in = fields.Datetime("Old Check In")
    new_check_out = fields.Datetime("Old Check Out")
    isduplicate = fields.Boolean('Duplicate?')
    on_leave = fields.Boolean('On Leave', compute='check_if_on_leave', default=False, store=True)
    is_suspicious = fields.Boolean('Suspicious')

    def trigger_computes(self):
        if self.toggle:
            self.toggle = False
        else:
            self.toggle = True

    def _my_request(self):
        if self.change_request:
            self.request_created = True
        else:
            self.request_created = False

    change_request = fields.Many2one('my.change.request', string="Change Request")
    request_created = fields.Boolean(compute='_my_request', store=True)

    @api.depends('check_in', 'check_out', 'state', 'toggle')
    def _get_status(self):
        for rec in self:
            if rec.state == 'done' and rec.status != 'suspicious':
                if rec.mark_off == True:
                    rec.status = 'off_day'
                    rec.status2 = 'off_day'
                elif not (rec.check_in and rec.check_out):
                    rec.status = 'absent'
                    rec.status2 = 'absent'
                elif rec.check_in == rec.check_out:
                    rec.status = 'missed_check'
                elif rec.check_in < rec.check_out:
                    rec.status = 'present'
                    rec.status2 = 'present'

    @api.depends('state', 'status', 'toggle')
    def check_if_on_leave(self):
        for rec in self:
            if rec.state == 'done':
                rec._cr.execute('''SELECT id FROM hr_leave
                                WHERE employee_id = %s AND DATE(date_from) <= to_date('%s', 'YYYY-MM-DD')
                                AND DATE(date_to) >= to_date('%s', 'YYYY-MM-DD') AND state = 'validate';''' % (
                rec.employee_id.id, rec.date_ga, rec.date_ga))
                result = rec._cr.dictfetchall()
                if result:
                    rec.on_leave = True

    @api.depends('employee_id', 'check_in', 'check_out', 'current_shift', 'toggle')
    def _compute_worked_hours(self):
        for attendance in self:
            if not (attendance.check_out and attendance.check_in):
                continue
            check_out = datetime.strptime(str(attendance.check_out), DEFAULT_SERVER_DATETIME_FORMAT)
            check_in = datetime.strptime(str(attendance.check_in), DEFAULT_SERVER_DATETIME_FORMAT)
            delta = check_out - check_in
            attendance.worked_hours = delta.total_seconds() / 3600.0
            attendance.working_hours = (delta.total_seconds() / 60)  # Minutes
            if attendance.current_shift:
                attendance.normal_working_hours = attendance.current_shift.hours_per_day
                attendance.standard_hours = attendance.current_shift.hours_per_day * 60
                # attendance.normal_working_hours = attendance.current_shift.uom_id.factor
                # attendance.standard_hours = attendance.current_shift.uom_id.factor * 60
                duration = attendance.worked_hours - attendance.normal_working_hours
                if duration >= attendance.current_shift.overtime_start:
                    date = datetime.strptime(str(attendance.date_ga), '%Y-%m-%d')
                    schd = attendance.current_shift.get_attendances_for_weekday(date)
                    dur = 0
                    if schd:
                        start = min(schd.mapped('hour_from')) - 5
                        in_time = (check_in - date).days * 24.0 + (check_in - date).seconds / 3600.0
                        dur = start - in_time
                        attendance.over_time_hr = duration if dur <= 0 else duration - dur
                    else:
                        attendance.over_time_hr = attendance.worked_hours
                    if attendance.current_shift.exclude and schd:
                        attendance.over_time_hr -= attendance.current_shift.overtime_start
                    if attendance.over_time_hr > 0:
                        attendance.over_time = attendance.over_time_hr * 60.0

    @api.depends('employee_id', 'check_in', 'check_out', 'current_shift', 'toggle')
    def _get_in_status(self):
        for rec in self:
            if not (rec.check_in and rec.check_out and rec.date_ga and rec.current_shift):
                return

            date = datetime.strptime(str(rec.date_ga), '%Y-%m-%d')
            schd = rec.current_shift.get_attendances_for_weekday(date)
            if not schd:
                rec.extra_day = 'yes'
                rec.late_in_time = 0
                rec.in_status = '0'
                return
            if rec.current_shift.shift == 'day':
                schd_in_time = min(schd.mapped('hour_from'))
            else:
                schd_in_time = max(schd.mapped('hour_from'))
            check_in_time = (datetime.strptime(str(rec.check_in), DEFAULT_SERVER_DATETIME_FORMAT) + timedelta(
                hours=5)).time()
            delta = (check_in_time.hour + check_in_time.minute / 60.0) - schd_in_time
            if delta <= 0:
                rec.in_status = '0'
                return
            for i in rec.current_shift.in_policy_id:
                if i.time_from <= delta <= i.time_to:
                    rec.late_in_time = delta
                    rec.in_status = i.status
                    return

    def check_gazzated_holiday(self, dt):
        gazzated_holiday = self.env['holidays.schedule'].search_count([('date', '=', dt.date())])
        return gazzated_holiday

    @api.depends('employee_id', 'check_in', 'check_out', 'current_shift', 'toggle')
    def _get_out_status(self):
        for rec in self:
            if not (rec.check_in and rec.check_out and rec.date_ga and rec.current_shift):
                return
            date = datetime.strptime(str(rec.date_ga), '%Y-%m-%d')
            schd = rec.current_shift.get_attendances_for_weekday(date)
            if not schd:
                rec.extra_day = 'yes'
                rec.early_time_out = 0
                rec.out_status = '0'
                if rec.current_shift.compensatory_hours and rec.worked_hours >= rec.current_shift.compensatory_hours and rec.employee_id.overtime:
                    rec.compensatory = 'yes'
                    rec.compensatory_leave = 1
                return
            gazzated_holiday = rec.check_gazzated_holiday(date)

            if gazzated_holiday > 0:
                if schd and (
                        rec.worked_hours - rec.normal_working_hours) >= rec.current_shift.compensatory_hours and rec.current_shift.compensatory_hours and rec.employee_id.overtime:
                    rec.compensatory = 'yes'
                    rec.compensatory_leave = 1
            elif gazzated_holiday == 0 and schd and rec.worked_hours >= rec.current_shift.compensatory_hours and rec.current_shift.compensatory_hours and rec.employee_id.overtime:
                rec.compensatory = 'yes'
                rec.compensatory_leave = 1

            if rec.current_shift.shift == 'day':
                schd_out_time = max(schd.mapped('hour_to'))
            else:
                schd_out_time = min(schd.mapped('hour_to'))
            check_out_time = (datetime.strptime(str(rec.check_out), DEFAULT_SERVER_DATETIME_FORMAT) + timedelta(
                hours=5)).time()
            delta = (check_out_time.hour + check_out_time.minute / 60.0)
            # if delta < 0:
            #     self.early_time_out = abs(delta)
            #     self.out_status = '1'
            for i in rec.current_shift.out_policy_id:
                if i.time_from <= delta <= i.time_to:
                    rec.out_status = i.status
                    return

    @api.depends('state', 'toggle', 'check_in', 'check_out')
    def check_between_times(self):
        for rec in self:
            if rec.state != 'done' and not (rec.check_in and rec.check_out):
                return
            records = self.env['machine.data'].search(
                [('employee_name', '=', rec.employee_id.id), ('time', '>', rec.check_in), ('time', '<', rec.check_out),
                 ('status', '=', 'unprocessed')])
            if records:
                self.is_suspicious = True
                self.prepare_allrecords(records)

    def prepare_allrecords(self, records):
        result = ''
        for record in records:
            result += str(record.time) + ', '
        self.all_records = result

    @api.depends('employee_id', 'in_status', 'out_status', 'state', 'toggle')
    def _get_attendance_status_ga(self):
        for rec in self:
            if rec.in_status and rec.out_status:
                if rec.in_status == rec.out_status:
                    rec.attendance_status = rec.in_status
                elif int(rec.in_status) > int(rec.out_status):
                    rec.attendance_status = rec.in_status
                elif int(rec.in_status) < int(rec.out_status):
                    rec.attendance_status = rec.out_status
                    if rec.out_status == '5':
                        if rec.in_status == '0':
                            rec.attendance_status = '0'
                        elif rec.in_status == '3':
                            rec.attendance_status = '3'

    @api.constrains('check_in', 'check_out', 'employee_id', 'toggle')
    def _check_validity(self):
        """ Verifies the validity of the attendance record compared to the others from the same employee.
            For the same employee we must have :
                * maximum 1 "open" attendance record (without check_out)
                * no overlapping time slices with previous employee records
        """
        return

    @api.constrains('check_in', 'check_out')
    def _check_validity_check_in_check_out(self):
        """ verifies if check_in is earlier than check_out. """
        # Uncertain behavior
        #         for attendance in self:
        #             if attendance.check_in and attendance.check_out:
        #                 c_out = datetime.strptime(self.check_out, DEFAULT_SERVER_DATETIME_FORMAT)
        #                 c_in = datetime.strptime(self.check_in, DEFAULT_SERVER_DATETIME_FORMAT)
        #                 if c_out < c_in:
        #                     raise exceptions.ValidationError(_('"Check Out" time cannot be earlier than "Check In" time.'))
        return

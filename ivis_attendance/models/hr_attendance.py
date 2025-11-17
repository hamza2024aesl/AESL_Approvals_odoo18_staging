from odoo import models, fields, api
from datetime import datetime, timedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import math

class Attendancelog(models.Model):
    _name = 'ivis.attendance.log'
    _description = 'Attendance Log'

    employee = fields.Many2one('hr.employee')
    punching_date = fields.Date()


class hrAttendance(models.Model):
    _inherit = 'hr.attendance'

    working_hours = fields.Float('Working Time (minutes) [IVIS]', compute='_compute_worked_hours', default=False, store=True)
    standard_hours = fields.Float('Standard Time (minutes) [IVIS]', compute='_compute_worked_hours', default=False, store=True)
    over_time = fields.Float('Over Time (minutes) [IVIS]', compute='_compute_overtime_minutes', default=False, store=True)
    normal_working_hours = fields.Float('Standard Working Hours [IVIS]', compute='_compute_worked_hours', default=False, store=True)
    late_in_time = fields.Float('Late In Time [IVIS]', compute='_get_in_status', default=False, store=True)
    in_status = fields.Selection([('0','Ok'),('1','Late-In'),('2','Quarter-Day'),('3','Half-Day'),('4','Tri-Quarter'),('5','Full-Day')], 'In status [IVIS]', compute='_get_in_status', default=False, store=True)
    early_time_out = fields.Float('Early Out Time [IVIS]', compute='_get_out_status', default=False, store=True)
    out_status = fields.Selection([('0','Ok'),('1','Early-Out'),('2','Quarter-Day'),('3','Half-Day'),('4','Tri-Quarter'),('5','Full-Day')], 'Out status [IVIS]', compute='_get_out_status', default=False, store=True)
    attendance_status = fields.Selection([('0','Ok'),('1','Late'),('2','Quarter-Day'),('3','Half-Day'),('4','Tri-Quarter'),('5','Full-Day')], 'Attendance status [IVIS]', compute='_get_attendance_status_ivis', default=False, store=True)
    extra_day = fields.Selection([('yes','Yes'),('no','No')],'Extra Day [IVIS]')
    compensatory = fields.Selection([('yes','Yes'),('no','No')],'Compensatory [IVIS]')
    compensatory_leave = fields.Integer('Compensatory Leave [IVIS]')
    penalty = fields.Float('Penalty [IVIS]')
    status2 = fields.Selection([('present','Present'), ('absent','Absent'), ('off_day','Off-Day'), ('missed_check_out','Missed to Check Out'),('missed_check_in','Missed to Check In')], string='Status [IVIS2]', default=False)
    status = fields.Selection([('present','Present'), ('absent','Absent'), ('off_day','Off-Day'), ('missed_check','Missed to Check In/Out')], string='Status [IVIS]', default=False, compute='_get_status', store=True)
    current_shift = fields.Many2one('resource.calendar', string='Current Shift [IVIS]')
    machine_shift = fields.Many2one('resource.calendar', string='Old Shift [IVIS]')
    all_records = fields.Char('Other Records [IVIS]', help="It is a technical field.", compute='check_between_times',store=True)
    toggle = fields.Boolean('Compute [IVIS]')
    
    # Change Request related work
    machine_check_in = fields.Datetime("Machine Check In [IVIS]")
    machine_check_out = fields.Datetime("Machine Check Out [IVIS]")
    isduplicate = fields.Boolean('Duplicate? [IVIS]')
    on_leave = fields.Boolean('On Leave [IVIS]', compute='check_if_on_leave', default=False, store=True)
    is_suspicious = fields.Boolean('Suspicious [IVIS]')
    
    change_request = fields.Many2one('my.change.request',string="Change Request [IVIS]")
    request_created = fields.Boolean(compute='_my_request',store=True)

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

    @api.depends('check_in', 'check_out', 'state', 'toggle')
    def _get_status(self):
        for rec in self:
            if rec.state == 'done' and rec.status != 'suspicious':
                if rec.mark_off:
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
                                AND DATE(date_to) >= to_date('%s', 'YYYY-MM-DD') AND state = 'validate';''' % (rec.employee_id.id, rec.attendance_date, rec.attendance_date))
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
            attendance.working_hours = (delta.total_seconds() / 60) # Minutes
            
            if attendance.current_shift:
                attendance.normal_working_hours = attendance.current_shift.hours_per_day
                attendance.standard_hours = attendance.current_shift.hours_per_day * 60
                          
    @api.depends('employee_id', 'check_in', 'check_out', 'current_shift', 'toggle')
    def _get_in_status(self):
        for rec in self:
            if not (rec.check_in and rec.check_out and rec.attendance_date and rec.current_shift):
                return

            attendance_date = datetime.strptime(str(rec.attendance_date), '%Y-%m-%d')
            schd = rec.current_shift.get_attendances_for_weekday(attendance_date)
            if not schd:
                rec.extra_day = 'yes'
                rec.late_in_time = 0
                rec.in_status = '0'
                return
            
            if rec.current_shift.shift == 'day':
                schd_in_time = min(schd.mapped('hour_from'))
            else: # Night
                schd_in_time = max(schd.mapped('hour_from'))
                
            check_in_time = (datetime.strptime(str(rec.check_in), 
                             DEFAULT_SERVER_DATETIME_FORMAT) + timedelta(hours=5)).time()
            check_out_time = (datetime.strptime(str(rec.check_out), 
                              DEFAULT_SERVER_DATETIME_FORMAT) + timedelta(hours=5)).time()
            
            floor, ceil = math.modf(check_in_time.minute / 60)
            delta = float(check_in_time.hour + floor) - schd_in_time
            compare_value = float(check_in_time.hour + floor)
            
            if delta <= 0:
                rec.late_in_time = 0
                rec.in_status = '0'
                return
            
            for policy in rec.current_shift.in_policy_id:
                policy_start = schd_in_time + policy.time_from
                policy_end = schd_in_time + policy.time_to
 
                if policy_start <= compare_value <= policy_end:
                    rec.late_in_time = delta
                    rec.in_status = policy.status
                    
                    if policy.status == '0':
                        rec.late_in_time = 0
                                        
                if policy.adjust_time:
                    check_in_time_float = check_in_time.hour + check_in_time.minute / 60.0
                    
                    if check_out_time and schd_in_time <= check_in_time_float <= policy_end:
                        check_out_time_float = check_out_time.hour + check_out_time.minute / 60.0
                        total_hours = check_out_time_float - check_in_time_float
                        
                        if rec.current_shift.hours_per_day > total_hours:
                            rec.in_status = '1'
                            return

    def check_gazzated_holiday(self, dt):
        gazzated_holiday = self.env["resource.calendar.leaves"].search_count(
            [
                ("date_from", "<=", dt.date()),
                ("date_to", ">=", dt.date()),
                ("resource_id", "=", False),
            ]
        )
        return gazzated_holiday

    @api.depends('employee_id', 'check_in', 'check_out', 'current_shift', 'toggle')
    def _get_out_status(self):
        for rec in self:
            if not (
                rec.check_in and rec.check_out and rec.attendance_date and rec.current_shift
            ):
                return
            
            attendance_date = datetime.strptime(str(rec.attendance_date), '%Y-%m-%d')
            schd = rec.current_shift.get_attendances_for_weekday(attendance_date)
            if not schd:
                rec.extra_day = 'yes'
                rec.early_time_out = 0
                rec.out_status = '0'
                if (
                    rec.current_shift.compensatory_hours 
                    and rec.worked_hours >= rec.current_shift.compensatory_hours
                    and rec.employee_id.over_time 
                ):
                    rec.compensatory = 'yes'
                    rec.compensatory_leave = 1
                return
            
            gazzated_holiday = rec.check_gazzated_holiday(attendance_date)
            if gazzated_holiday > 0:
                if (
                    schd 
                    and (rec.worked_hours - rec.normal_working_hours) 
                    >= rec.current_shift.compensatory_hours 
                    and rec.current_shift.compensatory_hours 
                    and rec.employee_id.over_time 
                ):
                    rec.compensatory = 'yes'
                    rec.compensatory_leave = 1
            elif (
                gazzated_holiday == 0 
                and schd 
                and rec.worked_hours >= rec.current_shift.compensatory_hours 
                and rec.current_shift.compensatory_hours 
                and rec.employee_id.over_time 
            ):
                rec.compensatory = 'yes'
                rec.compensatory_leave = 1

            check_in_time = (datetime.strptime(str(rec.check_in), 
                             DEFAULT_SERVER_DATETIME_FORMAT) + timedelta(hours=5)).time()
            check_out_time = (datetime.strptime(str(rec.check_out), 
                              DEFAULT_SERVER_DATETIME_FORMAT) + timedelta(hours=5)).time()
            
            if rec.current_shift.shift == 'day':
                schd_in_time = min(schd.mapped('hour_from'))
                schd_out_time = max(schd.mapped('hour_to'))
                floor, ceil = math.modf(check_out_time.minute/60)
                delta = float(check_out_time.hour + floor) - schd_out_time
                compare_value = float(check_out_time.hour + floor)
            else:
                schd_in_time = max(schd.mapped('hour_from'))
                schd_out_time = min(schd.mapped('hour_to'))
                floor, ceil = math.modf(check_out_time.minute / 60)
                delta = float(check_out_time.hour + floor)
                compare_value = float(check_out_time.hour + floor)
                
            if delta < 0:
                self.early_time_out = abs(delta)
                self.out_status = '1'
            
            has_adjust_time = any(policy.adjust_time for policy in rec.current_shift.in_policy_id) 
               
            for policy in rec.current_shift.out_policy_id:
                policy_start = schd_out_time - policy.time_from
                policy_end = schd_out_time - policy.time_to

                if compare_value >= schd_out_time:
                    rec.out_status = '0'

                if policy_start >= compare_value >= policy_end:
                    rec.out_status = policy.status
                    rec.early_time_out = abs(delta)

                    if rec.out_status == '0':
                        self.early_time_out = 0

                if has_adjust_time:
                    check_in_time_float = check_in_time.hour + check_in_time.minute / 60.0

                    if check_in_time_float < schd_in_time:
                        check_out_time_float = check_out_time.hour + check_out_time.minute / 60.0
                        total_hours = check_out_time_float - check_in_time_float

                        if rec.current_shift.hours_per_day < total_hours:
                            rec.out_status = '0'
                            return

    @api.depends('state', 'toggle', 'check_in', 'check_out')
    def check_between_times(self):
        for rec in self:
            if rec.state != 'done' and not (rec.check_in and rec.check_out):
                return
            
            records = self.env["zk.machine.attendance"].search(
                [
                    ("employee_id", "=", rec.employee_id.id),
                    ("punching_time", ">", rec.check_in),
                    ("punching_time", "<", rec.check_out),
                    ("zk_process_status", "=", "unprocessed"),
                ]
            )
            if records:
                self.is_suspicious = True
                self.prepare_allrecords(records)

    def prepare_allrecords(self, records):
        result = ''
        for record in records:
            result += str(record.punching_time) + ', '
        self.all_records = result

    @api.depends('employee_id', 'in_status', 'out_status', 'state', 'toggle')
    def _get_attendance_status_ivis(self):
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

    # ? Do not remove - This is overwriting a base function
    @api.constrains('check_in', 'check_out', 'employee_id', 'toggle')
    def _check_validity(self):
        """ Verifies the validity of the attendance record compared to the others from the same employee.
            For the same employee we must have :
                * maximum 1 "open" attendance record (without check_out)
                * no overlapping time slices with previous employee records
        """
        return

    # ? 
    @api.constrains('check_in', 'check_out')
    def _check_validity_check_in_check_out(self):
        """ verifies if check_in is earlier than check_out. """
        return
    
    
    @api.depends('overtime_hours')
    def _compute_overtime_minutes(self):
        for rec in self:
            rec.over_time = rec.overtime_hours * 60
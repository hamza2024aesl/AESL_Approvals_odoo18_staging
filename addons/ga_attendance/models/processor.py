from datetime import datetime, timedelta
from odoo import fields, models, api, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class Attendance(models.Model):
    _inherit = 'hr.attendance'

    state = fields.Selection([('draft', 'In Process'), ('done', 'Done'), ('suspicious', 'Suspicious')], 'State',
                             required=True, copy=False, default='draft')
    date_ga = fields.Date('Date', index=True)
    previous_dates = fields.Char('Previous Dates', help="It is a technical field.", readonly=True)
    warn_text = fields.Text('Info')
    # Don't use it
    mark_off = fields.Boolean('Mark the day as Off', help="It is a technical field.")

    def name_get(self):
        result = []
        for attendance in self:
            result.append((attendance.id, _("%(empl_name)s on %(date_ga)s") % {
                'empl_name': attendance.employee_id.name,
                'date_ga': attendance.date_ga, }))
        return result

    @api.model
    def process_attendance_ga(self):
        employees = self.env['hr.employee'].search([])
        for employee in employees:
            attendance = self.env['hr.attendance']
            # Process previous attendance if any
            self.process_prev_attendance(employee)
            metadata = self.records_to_create(employee)
            for i in range(metadata[0]):
                date = metadata[1] + timedelta(days=i + 1)  # Incrementing days
                values = {'employee_id': employee.id, 'current_shift': employee.resource_calendar_id.id,
                          'date_ga': date}
                data = self.attendance_Rules(employee, date, first=True)
                if data:
                    values.update(data)
                    # values = self.AI(employee, values)
                ac = attendance.create(values)
                ac._get_status()
                ac.check_if_on_leave()
                ac._compute_worked_hours()
                ac._get_in_status()
                ac._get_out_status()
                ac.check_between_times()
                ac._get_attendance_status_ga()
        self.check_holidays_attendance()

    def check_holidays_attendance(self):
        off_check = self.env['holidays.schedule'].search([], limit=5, order='date desc')
        for oc in off_check:
            attendance = self.env['hr.attendance'].search([('date_ga', '=', oc.date)])
            if attendance:
                attendance.status = 'off_day'
                attendance.status2 = 'off_day'
                attendance.in_status = ''
                attendance.out_status = ''

    def get_employee_and_shift_wrt_to_record(self, attendance_record, date, first):
        if first:
            schd = attendance_record.resource_calendar_id.get_attendances_for_weekday(date)
            employee = attendance_record
            if not schd:
                schd = attendance_record.resource_calendar_id.attendance_ids.filtered(lambda a: a.dayofweek == '1')
        else:
            if attendance_record.current_shift:
                schd = attendance_record.current_shift.get_attendances_for_weekday(date)
            else:
                attendance_record.warn_text = "Shift is not selected."
                return
            employee = attendance_record.employee_id
            if not schd:
                schd = attendance_record.current_shift.attendance_ids.filtered(lambda a: a.dayofweek == '1')
        return (schd, employee)

    def attendance_Rules(self, attendance_record, date, first=False):
        schd, employee = self.get_employee_and_shift_wrt_to_record(attendance_record, date, first)
        if employee.resource_calendar_id.shift == 'day':
            start = min(schd.mapped('hour_from')) - 3 - 5  # -5 to exclude time zone
            end = max(schd.mapped('hour_to')) - 3 - 5
        else:
            start = max(schd.mapped('hour_from')) - 3 - 5  # -5 to exclude time zone
            end = min(schd.mapped('hour_to')) - 3 - 5
        machine = self.env['machine.data'].search([('employee_name', '=', employee.id), (
            'time', '>=', datetime.strftime(date + timedelta(hours=start), DEFAULT_SERVER_DATETIME_FORMAT)),
                                                   ('time', '<',
                                                    datetime.strftime(date + timedelta(days=1, hours=start),
                                                                      DEFAULT_SERVER_DATETIME_FORMAT)),
                                                   ('status', '=', 'unprocessed')], order='time asc')
        if machine:
            return self.attendance_validity(machine, date, start, end, attendance_record, first)
        else:
            return {}

    def attendance_validity(self, machine_data, date, start, end, attendance_record, first):
        c_in = machine_data.filtered(
            lambda r: start <= (datetime.strptime(str(r.time), DEFAULT_SERVER_DATETIME_FORMAT) - date).days * 24.0 +
                      (datetime.strptime(str(r.time), DEFAULT_SERVER_DATETIME_FORMAT) - date).seconds / 3600.0 <= (
                              start + 7))
        c_in = list(c_in)
        c_in.sort(key=lambda r: r.time)
        c_out = machine_data.filtered(
            lambda r: not (
                    start <= (datetime.strptime(str(r.time), DEFAULT_SERVER_DATETIME_FORMAT) - date).days * 24.0 +
                    (datetime.strptime(str(r.time), DEFAULT_SERVER_DATETIME_FORMAT) - date).seconds / 3600.0 <= (
                            start + 7)))
        c_out = list(c_out)
        c_out.sort(key=lambda r: r.time)
        if (c_in and c_out and first) or (
                not first and not attendance_record.check_in and not attendance_record.check_out and c_in and c_out):
            c_in[0].write({'status': 'processed'})
            c_out[-1].write({'status': 'processed'})
            return {'check_in': c_in[0].time, 'check_out': c_out[-1].time, 'state': 'done'}
        if (c_in and first) or (not first and not attendance_record.check_in and c_in):
            c_in[0].write({'status': 'processed'})
            return {'check_in': c_in[0].time}
        if (c_out and first) or (not first and not attendance_record.check_out and c_out):
            c_out[-1].write({'status': 'processed'})
            return {'check_out': c_out[-1].time}

    def AI(self, employee, vals):
        if not vals.get('check_in', False):
            return vals
        new_rec_time = vals['check_in']
        last_rec = self.get_previous_attendance(employee, always_return=True)
        if not last_rec or (type(last_rec[0]) == str and last_rec[0] == 'no'):
            return vals
        unp_recs = self.env['machine.data'].search(
            [('employee_name', '=', employee.id), ('time', '>=', last_rec.check_out), ('time', '<=', new_rec_time),
             ('status', '=', 'unprocessed')])
        unp_rec = unp_recs.filtered(lambda r: (datetime.strptime(r.time, "%Y-%m-%d %H:%M:%S") - datetime.strptime(
            last_rec.check_out, "%Y-%m-%d %H:%M:%S")) >= timedelta(hours=4)
                                              and (datetime.strptime(new_rec_time,
                                                                     "%Y-%m-%d %H:%M:%S") - datetime.strptime(r.time,
                                                                                                              "%Y-%m-%d %H:%M:%S")) >= timedelta(
            hours=4))
        if unp_rec:
            vals.update({
                'warn_text': 'Seems like the employee worked out of his/her shift, is his/her shift time changed? Mr. Robo, has completed this for you automatically.',
                'previous_dates': 'Check in was ' + new_rec_time, 'check_in': unp_rec[0].time,
                'check_out': new_rec_time, 'state': 'done'})
            unp_rec.write({'status': 'processed'})
        return vals

    #     def night_Rules(self, attendance_record, date, sd, first=False):
    #         values = {}
    #         schd, employee = self.get_employee_and_shift_wrt_to_record(attendance_record, date, first)
    #         start = max(schd.mapped('hour_from')) - 3 - 5 # -5 to exclude time zone
    #         end = min(schd.mapped('hour_to')) - 4 - 5
    #         machine = self.env['machine.data'].search([('employee_name', '=', employee.id), ('time', '>=', datetime.strftime(date + timedelta(hours=start), DEFAULT_SERVER_DATETIME_FORMAT)),
    #                                                    ('time', '<', datetime.strftime(date + timedelta(days=1, hours=start), DEFAULT_SERVER_DATETIME_FORMAT)), ('status', '=', 'unprocessed')], order='time asc')
    #         if machine:
    #             return self.attendance_validity(machine, date, start, end)
    #         else:
    #             return {}
    #         self.night_in(employee, date, sd, values, start)
    #         self.night_out(employee, date, sd, values, end)
    #         if values and values.get('check_in', False) and values.get('check_out', False):
    #             values.update({'state': 'done'})
    #         return values
    #
    #     def night_in(self, employee, date, sd, vals, start):
    #         d1 = (date + timedelta(hours=start)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
    #         d2 = (date + timedelta(hours=start + 6)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
    #         machine_in = self.env['machine.data'].search([('employee_name', '=', employee.id), ('time', '>=', d1), ('time', '<=', d2), ('status', '=', 'unprocessed')], order='time asc')
    #         if machine_in and self.verify_time(machine_in[0].time, 'in', sd):
    #             machine_in[0].status = 'processed'
    #             vals.update({'check_in': machine_in[0].time})
    #
    #     def night_out(self, employee, date, sd, vals, end):
    #         d1 = (date + timedelta(hours=end)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
    #         d2 = (date + timedelta(hours=end + 10)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
    #         machine_out = self.env['machine.data'].search([('employee_name', '=', employee.id), ('time', '>=', d1), ('time', '<=', d2), ('status', '=', 'unprocessed')], order='time asc')
    #         if machine_out and self.verify_time(machine_out[-1].time, 'out', sd):
    #             machine_out[-1].status = 'processed'
    #             return vals.update({'check_out': machine_out[-1].time})

    #     def verify_time(self, date, Type, sd):
    #         tz = timedelta(hours=5) # Adding 5 hours
    #         t = (datetime.strptime(date, DEFAULT_SERVER_DATETIME_FORMAT) + tz).time()
    #         if Type == 'in':
    #             return t >= sd
    #         elif Type == 'out':
    #             return t < sd
    #
    #     def get_shift_divider(self, employee, date):
    #         schd = employee.calendar_id.get_attendances_for_weekday(date)
    #         if not schd:
    #             schd = employee.calendar_id.attendance_ids.filtered(lambda a: a.dayofweek == '1')
    #         sd = time(hour=int(max(schd.mapped('hour_from')) - 3))
    #         return sd

    #     def get_shift(self, employee):
    #         return employee.calendar_id.shift

    def records_to_create(self, employee):
        '''How many records are need to be created? 
        It returns 0: number of records, 1: the date of last record, and 2: today's date'''

        today = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
        rec = self.get_previous_attendance(employee, True)
        if type(rec[0]) == str and rec[0] == 'no':
            last_rec = (datetime.strptime(str(rec[1]), "%Y-%m-%d") - timedelta(days=1)) if rec[1] else 0
        elif rec:
            last_rec = datetime.strptime(str(rec.date_ga), "%Y-%m-%d")
        return [(today - last_rec).days if last_rec != 0 else 1, last_rec if last_rec else (today - timedelta(days=1)),
                today]

    def get_previous_attendance(self, employee, always_return=False):
        '''It gives previous in process attendance if any, 
            else it returns False.'''

        prev_rec = self.env['hr.attendance'].search([('employee_id', '=', employee.id), ('date_ga', '!=', False)],
                                                    order='date_ga desc', limit=1)
        if not prev_rec:
            prev_rec = self.env['machine.data'].search(
                [('employee_name', '=', employee.id), ('status', '=', 'unprocessed')], order='date asc', limit=1)
            return ['no', prev_rec.date if prev_rec else False]
        if always_return:
            return prev_rec
        if prev_rec.state == 'draft':
            return prev_rec
        else:
            return False

    def process_prev_attendance(self, employee):
        recs = self.env['hr.attendance'].search(
            [('employee_id', '=', employee.id), ('date_ga', '<=', datetime.today().date()), ('state', '!=', 'done'),
             ('current_shift', '!=', False)], order='date_ga asc')
        if not recs:
            return
        for rec in recs:
            vals = {}
            date = datetime.strptime(str(rec.date_ga), "%Y-%m-%d")
            self.prev_attendance(rec, employee, date, vals)
            if (vals.get('check_in', False) and vals.get('check_out', False)) or (
                    rec.check_in and vals.get('check_out', False)) or (vals.get('check_in', False) and rec.check_out):
                vals.update({'state': 'done'})
            rec.write(vals)
            rec._get_status()
            rec.check_if_on_leave()
            rec._compute_worked_hours()
            rec._get_in_status()
            rec._get_out_status()
            rec.check_between_times()
            rec._get_attendance_status_ga()

    #     def prev_attendance_night(self, rec, employee, date, vals):
    #         holiday = self.env['holidays.schedule']
    #         sd = self.get_shift_divider(employee, date)
    #         if not (rec.check_in and rec.check_out) and date.date() + timedelta(days=2) < datetime.today().date():
    #             if holiday.isHoliday(rec.date_ga) or not employee.calendar_id.get_attendances_for_weekday(date):
    #                 vals.update({'mark_off': True, 'state': 'done'})
    #             else:
    #                 vals.update({'state': 'done'})
    #         schd, employee = self.get_employee_and_shift_wrt_to_record(rec, date, False)
    #         start = max(schd.mapped('hour_from')) - 3 - 5 # -5 to exclude time zone
    #         end = min(schd.mapped('hour_to')) - 3 - 5
    #         if rec.check_in and rec.check_out:
    #             if date.date() < datetime.today().date():
    #                 vals.update({'state': 'done'})
    #                 return
    #         if not rec.check_in:
    #             self.night_in(employee, date, sd, vals, start)
    #             if not vals.get('check_in', False) and date.date() < datetime.today().date():
    #                 vals.update({'warn_text': '''The employee forget to check-in. So, Mr. Robo is keeping check-out and check-in same.
    #                                 You can do a change request to your manager.''', 'check_in': rec.check_out})
    #         if not rec.check_out:
    #             self.night_out(employee, date, sd, vals, end)
    #             if not vals.get('check_out', False) and date < date + timedelta(days=2):
    #                 vals.update({'warn_text': '''The employee forget to check-out. So, Mr. Robo is keeping check-out and check-in same.
    #                                 You can do a change request to your manager.''', 'check_out': rec.check_in})
    #

    def prev_attendance(self, rec, employee, date, vals):
        holiday = self.env['holidays.schedule']
        dictionary = self.attendance_Rules(rec, date)
        if dictionary:
            vals.update(dictionary)
        elif not dictionary and (rec.check_in or rec.check_out) and date.date() < datetime.today().date():
            vals.update({'check_out': rec.check_in if not rec.check_out else rec.check_out,
                         'check_in': rec.check_out if not rec.check_in else rec.check_in,
                         'warn_text': '''The employee forget to check-in/check-out. So, Mr. Robo is keeping check-out and check-in same.
                            You can do a change request to your manager.'''})

            if rec.check_in and not rec.check_out:
                vals.update({'status2': 'missed_check_out'})

            elif not rec.check_in and rec.check_out:
                vals.update({'status2': 'missed_check_in'})

        elif not (rec.check_in and rec.check_out) and date.date() < datetime.today().date():
            if holiday.isHoliday(rec.date_ga) or not employee.resource_calendar_id.get_attendances_for_weekday(date):
                vals.update({'mark_off': True, 'state': 'done'})
            else:
                vals.update({'state': 'done'})

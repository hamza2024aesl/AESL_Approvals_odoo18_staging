from odoo import fields, models, api, _
from datetime import datetime, timedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import time
import logging
_logger = logging.getLogger(__name__)


class Attendance(models.Model):
    _inherit = 'hr.attendance'

    state = fields.Selection([('draft', 'In Process'), ('done', 'Done'), ('suspicious', 'Suspicious')], 'State',
                             required=True, copy=False, default='draft')
    attendance_date = fields.Date('Date [IVIS]', index=True)
    previous_dates = fields.Char('Previous Dates', help="It is a technical field.", readonly=True)
    warn_text = fields.Text('Info')
    # Don't use it
    mark_off = fields.Boolean('Mark the day as Off', help="It is a technical field.")

    def name_get(self):
        result = []
        for attendance in self:
            result.append((attendance.id, _("%(empl_name)s on %(attendance_date)s") % {
                'empl_name': attendance.employee_id.name,
                'attendance_date': attendance.attendance_date, }))
        return result

    @api.model
    def process_attendance_ivis(self):
        """
        Optimized: Processes Attendance Logs efficiently using batch operations.
        """
        Attendance = self.env["hr.attendance"]
        Employee = self.env["hr.employee"]
        cr = self.env.cr

        employees = Employee.search([])  # you can restrict with domain if needed

        _logger.info("🔍 Starting attendance processing for %d employees", len(employees))
        global_start = time.time()

        for emp_index, employee in enumerate(employees, start=1):
            emp_start = time.time()

            # Step 1: Process previous attendance
            self.process_prev_attendance(employee)

            # Step 2: Generate new records metadata
            metadata = self.records_to_create(employee)
            total_days = metadata[0]
            start_date = metadata[1]

            if not total_days or not start_date:
                continue

            _logger.info("Employee %s (%d): %d days to process", employee.name, employee.id, total_days)

            batch_inserts = []
            processed_ids = []
            for i in range(total_days):
                date = start_date + timedelta(days=i + 1)
                values = {
                    "employee_id": employee.id,
                    "current_shift": employee.resource_calendar_id.id,
                    "machine_shift": employee.resource_calendar_id.id,
                    "attendance_date": date,
                }

                data = self.attendance_Rules(employee, date, first=True)
                if data:
                    values.update(data)

                if not values.get("check_in"):
                    if values.get("check_out"):
                        values["check_in"] = values["check_out"]
                    else:
                        values["check_in"] = date

                # Collect for SQL batch insert
                batch_inserts.append(values)

                # Commit after every 500 inserts
                if len(batch_inserts) >= 500:
                    created_ids = self._bulk_create_attendance(Attendance, batch_inserts)
                    processed_ids += created_ids
                    batch_inserts = []
                    cr.commit()

            # Insert any remaining
            if batch_inserts:
                created_ids = self._bulk_create_attendance(Attendance, batch_inserts)
                processed_ids += created_ids
                cr.commit()

            # Step 3: ORM post-processing (recompute)
            if processed_ids:
                recs = Attendance.browse(processed_ids)
                batch_size = 500
                for i in range(0, len(recs), batch_size):
                    batch = recs[i:i + batch_size].with_context(prefetch_fields=False)
                    for rec in batch:
                        rec._get_status()
                        rec._get_in_status()
                        rec._get_out_status()
                        rec._get_attendance_status_ivis()
                    cr.commit()

            emp_end = time.time()
            _logger.info("✅ Processed employee %s (%d) in %.2f seconds", employee.name, employee.id,
                         emp_end - emp_start)

        global_end = time.time()
        _logger.info("🚀 All employees processed in %.2f seconds", global_end - global_start)

    def _bulk_create_attendance(self, Attendance, values_list):
        """
        Helper to insert multiple attendance records quickly using SQL.
        Returns the created record IDs.
        """
        if not values_list:
            return []

        cr = self.env.cr
        created_ids = []
        uid = self.env.uid
        now = fields.Datetime.now()

        for vals in values_list:
            # Ensure mandatory defaults
            vals.setdefault("state", "draft")
            vals.setdefault("create_uid", uid)
            vals.setdefault("write_uid", uid)
            vals.setdefault("create_date", now)
            vals.setdefault("write_date", now)

            fields_ = list(vals.keys())
            placeholders = ", ".join(["%s"] * len(fields_))
            field_names = ", ".join(fields_)

            insert_query = f"""
                INSERT INTO hr_attendance ({field_names})
                VALUES ({placeholders})
                RETURNING id
            """
            cr.execute(insert_query, list(vals.values()))
            new_id = cr.fetchone()[0]
            created_ids.append(new_id)

        return created_ids

    # @api.model
    # def process_attendance_ivis(self):
    #     """
    #     Processes "Attendance Logs" if the recent most `attendance_date` is prior to today.
    #     Handles absences, off-days, and regular working hours from that day onwards.
    #     """
    #     employees = self.env['hr.employee'].search([])
    #     # employees = self.env['hr.employee'].browse(1483)
    #     for employee in employees:
    #         attendance = self.env['hr.attendance']
    #         # Process previous attendance if any
    #         self.process_prev_attendance(employee)
    #         metadata = self.records_to_create(employee)
    #         start_time = time.time()
    #         for i in range(metadata[0]):
    #             date = metadata[1] + timedelta(days=i + 1)  # Incrementing days
    #             values = {'employee_id': employee.id, 'current_shift': employee.resource_calendar_id.id,
    #                       'machine_shift': employee.resource_calendar_id.id, 'attendance_date': date}
    #             data = self.attendance_Rules(employee, date, first=True)
    #             if data:
    #                 values.update(data)
    #             if not values.get('check_in'):
    #                 if values.get('check_out'):
    #                     values['check_in'] = values['check_out']
    #                 else:
    #                     values['check_in'] = date
    #
    #             ac = attendance.create(values)
    #             ac._get_status()
    #             # ac.check_if_on_leave()
    #             # ac._compute_worked_hours()
    #             ac._get_in_status()
    #             ac._get_out_status()
    #             # ac.check_between_times()
    #             ac._get_attendance_status_ivis()
    #             end_time = time.time()
    #             _logger.info("⏱ Loop metadata took %.3f seconds", end_time - start_time)
    #             self.env.cr.commit()

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
            start = min(schd.mapped('hour_from')) - 3 - 5 # -5 to exclude time zone
            end = max(schd.mapped('hour_to')) - 3 - 5
        else:
            start = max(schd.mapped('hour_from')) - 3 - 5  # -5 to exclude time zone
            end = min(schd.mapped('hour_to')) - 3 - 5
        machine = self.env['zk.machine.attendance'].search([('employee_id', '=', employee.id), (
            'punching_time', '>=', datetime.strftime(date + timedelta(hours=start), DEFAULT_SERVER_DATETIME_FORMAT)),
                                                   ('punching_time', '<',
                                                    datetime.strftime(date + timedelta(days=1, hours=start),
                                                                      DEFAULT_SERVER_DATETIME_FORMAT)),
                                                   ('zk_process_status', '=', 'unprocessed')], order='punching_time asc')
        if machine:
            return self.attendance_validity(machine, date, start, end, attendance_record, first)
        else:
            return {}

    def attendance_validity(self, machine_data, date, start, end, attendance_record, first):
        c_in = machine_data.filtered(
            lambda r: start <= (datetime.strptime(str(r.punching_time), DEFAULT_SERVER_DATETIME_FORMAT) - date).days * 24.0 +
                      (datetime.strptime(str(r.punching_time), DEFAULT_SERVER_DATETIME_FORMAT) - date).seconds / 3600.0 <= (
                              start + 7))
        c_in = list(c_in)

        c_in.sort(key=lambda r: r.punching_time)
        c_out = machine_data.filtered(
            lambda r: not (
                    start <= (datetime.strptime(str(r.punching_time), DEFAULT_SERVER_DATETIME_FORMAT) - date).days * 24.0 +
                    (datetime.strptime(str(r.punching_time), DEFAULT_SERVER_DATETIME_FORMAT) - date).seconds / 3600.0 <= (
                            start + 7)))
        c_out = list(c_out)
        c_out.sort(key=lambda r: r.punching_time)
        
        if (c_in and c_out and first) or (
                not first and not attendance_record.check_in and not attendance_record.check_out and c_in and c_out):
            c_in[0].write({'zk_process_status': 'processed'})
            c_out[-1].write({'zk_process_status': 'processed'})
            return {
                'check_in': c_in[0].punching_time, 'check_out': c_out[-1].punching_time, 
                'machine_check_in': c_in[0].punching_time, 'machine_check_out': c_out[-1].punching_time,
                'state': 'done'
            }
        
        if (c_in and first) or (not first and not attendance_record.check_in and c_in):
            c_in[0].write({'zk_process_status': 'processed'})
            return {
                'check_in': c_in[0].punching_time, 'machine_check_in': c_in[0].punching_time
            }
        
        if (c_out and first) or (not first and not attendance_record.check_out and c_out):
            c_out[-1].write({'zk_process_status': 'processed'})
            return {
                'check_out': c_out[-1].punching_time, 'machine_check_out': c_out[-1].punching_time
            }


    def records_to_create(self, employee):
        '''How many records are need to be created? 
        It returns 0: number of records, 1: the date of last record, and 2: today's date'''

        # today = datetime(2025, 9, 30, 0, 0, 0)
        today = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
        rec = self.get_previous_attendance(employee, True)
        if type(rec[0]) is str and rec[0] == 'no':
            last_rec = (datetime.strptime(str(rec[1]), "%Y-%m-%d") - timedelta(days=1)) if rec[1] else 0
        elif rec:
            last_rec = datetime.strptime(str(rec.attendance_date), "%Y-%m-%d")
        return [(today - last_rec).days if last_rec != 0 else 1, last_rec if last_rec else (today - timedelta(days=1)),
                today]

    def get_previous_attendance(self, employee, always_return=False):
        '''It gives previous in process attendance if any, 
            else it returns False.'''

        prev_rec = self.env['hr.attendance'].search([('employee_id', '=', employee.id), ('attendance_date', '!=', False)],
                                                    order='attendance_date desc', limit=1)
        if not prev_rec:
            prev_rec = self.env['zk.machine.attendance'].search(
                [('employee_id', '=', employee.id), ('zk_process_status', '=', 'unprocessed')], order='punching_date asc', limit=1)
            return ['no', prev_rec.punching_date if prev_rec else False]
        if always_return:
            return prev_rec
        if prev_rec.state == 'draft':
            return prev_rec
        else:
            return False

    def process_prev_attendance(self, employee):
        cr = self.env.cr
        Attendance = self.env["hr.attendance"]

        recs = Attendance.search([
            ("employee_id", "=", employee.id),
            ("attendance_date", "<=", datetime.today().date()),
            ("state", "!=", "done"),
            ("current_shift", "!=", False),
        ], order="attendance_date asc")

        if not recs:
            return

        _logger.info("Found %d records to process", len(recs))

        start_time = time.time()
        batch_updates = []
        processed_ids = []

        # --- Phase 1: SQL-based updates ---
        for rec in recs:
            vals = {}
            date = datetime.strptime(str(rec.attendance_date), "%Y-%m-%d")
            self.prev_attendance(rec, employee, date, vals)

            if (
                    (vals.get("check_in") and vals.get("check_out"))
                    or (rec.check_in and vals.get("check_out"))
                    or (vals.get("check_in") and rec.check_out)
            ):
                vals["state"] = "done"

            if vals:
                set_clause = ", ".join(f"{k} = %s" for k in vals.keys())
                sql = f"UPDATE hr_attendance SET {set_clause} WHERE id = %s"
                params = list(vals.values()) + [rec.id]
                batch_updates.append((sql, params))
                processed_ids.append(rec.id)

            # Batch commit to limit I/O
            if len(batch_updates) >= 500:
                for sql, params in batch_updates:
                    cr.execute(sql, params)
                cr.commit()
                _logger.info("Committed 500 records...")
                batch_updates = []

        # Remaining updates
        for sql, params in batch_updates:
            cr.execute(sql, params)
        cr.commit()

        mid_time = time.time()
        _logger.info("💾 SQL updates completed in %.2f seconds", mid_time - start_time)

        # --- Phase 2: ORM recomputation (only for updated records) ---
        if processed_ids:
            updated_recs = Attendance.browse(processed_ids)

            # Process in smaller ORM batches to avoid cache bloat
            batch_size = 500
            for i in range(0, len(updated_recs), batch_size):
                batch = updated_recs[i:i + batch_size]

                # Disable prefetching for speed
                batch = batch.with_context(prefetch_fields=False)

                for rec in batch:
                    rec._get_status()
                    rec._get_in_status()
                    rec._get_out_status()
                    rec._get_attendance_status_ivis()

                self.env.cr.commit()
                _logger.info("✅ ORM recompute done for records %d–%d", i + 1, i + len(batch))

        end_time = time.time()
        _logger.info("🚀 Total processing time: %.2f seconds", end_time - start_time)

    # def process_prev_attendance(self, employee):
    #     recs = self.env["hr.attendance"].search(
    #         [
    #             ("employee_id", "=", employee.id),
    #             ("attendance_date", "<=", datetime.today().date()),
    #             ("state", "!=", "done"),
    #             ("current_shift", "!=", False),
    #         ],
    #         order="attendance_date asc",
    #     )
    #
    #     if not recs:
    #         return
    #     start_time = time.time()
    #     for rec in recs:
    #         vals = {}
    #         date = datetime.strptime(str(rec.attendance_date), "%Y-%m-%d")
    #         self.prev_attendance(rec, employee, date, vals)
    #         if (
    #             (vals.get("check_in", False) and vals.get("check_out", False))
    #             or (rec.check_in and vals.get("check_out", False))
    #             or (vals.get("check_in", False) and rec.check_out)
    #         ):
    #             vals.update({'state': 'done'})
    #
    #         in_start_time = time.time()
    #         rec.write(vals)
    #         in_end_time = time.time()
    #         _logger.info("⏱ Inside Loop Previous took %.3f seconds", in_end_time - in_start_time)
    #         rec._get_status()
    #         # rec.check_if_on_leave()
    #         # rec._compute_worked_hours()
    #         rec._get_in_status()
    #         rec._get_out_status()
    #         # rec.check_between_times()
    #         rec._get_attendance_status_ivis()
    #         end_time = time.time()
    #         _logger.info("⏱ Loop L Previous took %.3f seconds", end_time - start_time)
    #         self.env.cr.commit()


    def prev_attendance(self, rec, employee, date, vals):
        public_holiday = self.env['resource.calendar.leaves'].search([('resource_id', '=', False)])
        holiday = False
        
        for line in public_holiday:
            start_date = line.date_from + timedelta(hours=5)
            end_date = line.date_to + timedelta(hours=5)
            if start_date.date() <= rec.attendance_date <= end_date.date():
                holiday = True
                break
            
        dictionary = self.attendance_Rules(rec, date)
        if dictionary:
            vals.update(dictionary)
            
        elif not dictionary and (rec.machine_check_in or rec.machine_check_out) and date.date() < datetime.today().date():
            vals.update({
                'check_out': rec.check_in if not rec.check_out else rec.check_out,
                'check_in': rec.check_out if not rec.check_in else rec.check_in,
                'warn_text': '''The employee forget to check-in/check-out. So, Mr. Robo is keeping check-out and check-in same.
                                You can do a change request to your manager.'''
            })

            if rec.machine_check_in and not rec.machine_check_out:
                vals.update({'status2': 'missed_check_out'})

            elif not rec.machine_check_in and rec.machine_check_out:
                vals.update({'status2': 'missed_check_in'})

        elif not (rec.machine_check_in and rec.machine_check_out) and date.date() < datetime.today().date():

            weekdays = ['Saturday', 'Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
            
            if (
                holiday 
                or rec.attendance_date.strftime('%A') == weekdays[int(employee.off_day_1)]
                or rec.attendance_date.strftime('%A') == weekdays[int(employee.off_day_2)]
            ):
                vals.update({'mark_off': True, 'state': 'done'})
            else:
                vals.update({'state': 'done'})

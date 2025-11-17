from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta, time
import calendar
from math import ceil
from odoo.tools.float_utils import float_round
from odoo.exceptions import ValidationError


class HrLeaveInherit(models.Model):
    _inherit = 'hr.leave'

    remaining_leaves = fields.Float(compute='CheckRemainingLeaves')

    @api.onchange('employee_id')
    def CheckRemainingLeaves(self):
        self.remaining_leaves = 0
        if not self.employee_id:
            emp = self.env['hr.employee'].search([('user_id', '=', self.env.uid)])
        else:
            emp = self.employee_id
        if emp and self.holiday_status_id:
            records = self.env['hr.leave.report'].search([
                ('employee_id', '=', emp.id),
                ('holiday_status_id', '=', self.holiday_status_id.id),
            ])
            self.remaining_leaves = 0
            for rec in records:
                self.remaining_leaves += rec.number_of_days

    @api.constrains('number_of_days', 'remaining_leaves')
    def _check_number_days(self):
        for rec in self:
            # if 'official visit' in rec.holiday_status_id.name.lower():
            if rec.holiday_status_id.requires_allocation == 'no':
                pass
            else:
                if rec.remaining_leaves < rec.number_of_days:
                    raise ValidationError(
                        _('The number of remaining time off is not sufficient for this time off type.\nPlease also check the time off waiting for validation.'))

    def action_approve(self):
        res = super(HrLeaveInherit, self).action_approve()
        attendances = self.env['hr.attendance'].search(
            [('employee_id', '=', self.employee_id.id), ('attendance_date', '<=', self.request_date_to),
             ('attendance_date', '>=', self.request_date_from)])
        if self.request_unit_half:
            attendances = attendances.filtered(lambda x: x.attendance_date == self.request_date_from)
        for attendance in attendances:
            attendance.on_leave = True
        return res

    def _create_lwp_leave(self, employee, start_date, end_date, lwp_leave_type, half_day=False, day_period=None):
        try:
            overlapping_leave = self.env['hr.leave'].search([
                ('employee_id', '=', employee.id),
                ('request_date_from', '<=', end_date),
                ('request_date_to', '>=', start_date),
                ('state', 'not in', ['cancel', 'refuse']),
            ], limit=1)
            overlapping_leave
            if overlapping_leave:
                return False

            leave = self.create({
                'name': 'Auto Leave Without Pay',
                'employee_id': employee.id,
                'date_from': fields.Datetime.to_string(start_date),
                'date_to': fields.Datetime.to_string(end_date + timedelta(hours=23, minutes=59)),
                'holiday_status_id': lwp_leave_type.id,
                'request_date_from': start_date,
                'request_date_to': end_date,
                'request_unit_half': half_day,
                'request_date_from_period': day_period,
            })
            if leave.state == 'confirm':
                leave.action_approve()
            if leave.state in ['validate1', 'validate']:
                leave.action_validate()
            return leave
        except Exception as e:
            return False

    @api.model
    def create_lwp_for_absent_days(self, date_from=None, date_to=None):
        current_date = datetime.today().date()

        if not date_from:
            prev_month = current_date.month - 1 or 12
            year = current_date.year if current_date.month > 1 else current_date.year - 1
            date_from = datetime(year, prev_month, 1).date()
        if not date_to:
            prev_month = current_date.month - 1 or 12
            year = current_date.year if current_date.month > 1 else current_date.year - 1
            last_day = calendar.monthrange(year, prev_month)[1]
            date_to = datetime(year, prev_month, last_day).date()

        if isinstance(date_from, str):
            date_from = fields.Date.from_string(date_from)
        if isinstance(date_to, str):
            date_to = fields.Date.from_string(date_to)
        if date_to > current_date:
            date_to = current_date

        lwp_leave_type = self.env['hr.leave.type'].search([('name', '=', 'LWP')], limit=1)
        if not lwp_leave_type:
            raise UserError("Leave type 'LWP' not found.")

        employees = self.env['hr.employee'].search([
            ('active', '=', True),
            ('contract_id.state', '=', 'open')
        ])

        all_leaves = self.env['hr.leave'].search([
            ('employee_id', 'in', employees.ids),
            ('request_date_to', '>=', date_from),
            ('request_date_from', '<=', date_to),
            ('state', 'not in', ['cancel', 'refuse']),
            ('payslip_state', '!=', 'done'),
        ])

        leaves_dict = {}
        for leave in all_leaves:
            emp_id = leave.employee_id.id
            if emp_id not in leaves_dict:
                leaves_dict[emp_id] = set()
            start = leave.request_date_from
            end = leave.request_date_to
            while start <= end:
                leaves_dict[emp_id].add(start)
                start += timedelta(days=1)

        all_attendances = self.env['hr.attendance'].search([
            ('employee_id', 'in', employees.ids),
            ('check_in', '>=', fields.Datetime.to_string(date_from)),
            ('check_in', '<=', fields.Datetime.to_string(date_to + timedelta(days=1))),
        ])

        attendance_dict = {}
        for attendance in all_attendances:
            emp_id = attendance.employee_id.id
            att_date = attendance.check_in.date()
            if emp_id not in attendance_dict:
                attendance_dict[emp_id] = {}
            attendance_dict[emp_id][att_date] = attendance

        for employee in employees:
            current_day = date_from
            emp_id = employee.id

            grade = int(employee.x_studio_grade or 0)
            if grade < 14:
                while current_day <= date_to:
                    try:
                        # Skip Saturdays (5) and Sundays (6)
                        if current_day.weekday() in (5, 6):
                            current_day += timedelta(days=1)
                            continue

                        attendance = attendance_dict.get(emp_id, {}).get(current_day, None)
                        status = attendance.status2 if attendance else None
                        in_status = attendance.in_status if attendance else None

                        if not attendance:
                            current_day += timedelta(days=1)
                            continue

                        is_holiday = self.env['resource.calendar.leaves'].search([
                            ('date_from', '<=', current_day),
                            ('date_to', '>=', current_day),
                            ('resource_id', '=', False)
                        ], limit=1)

                        if is_holiday:
                            current_day += timedelta(days=1)
                            continue

                        if status == 'off_day':
                            current_day += timedelta(days=1)
                            continue
                        elif status == 'absent':
                            if emp_id in leaves_dict and current_day in leaves_dict[emp_id]:
                                current_day += timedelta(days=1)
                                continue
                            self._create_lwp_leave(employee, current_day, current_day, lwp_leave_type)
                        elif in_status == '3':
                            if emp_id in leaves_dict and current_day in leaves_dict[emp_id]:
                                current_day += timedelta(days=1)
                                continue
                            self._create_lwp_leave(employee,current_day,current_day,lwp_leave_type,half_day=True,day_period='am')
                        elif in_status == '5':
                            if emp_id in leaves_dict and current_day in leaves_dict[emp_id]:
                                current_day += timedelta(days=1)
                                continue
                            self._create_lwp_leave(employee, current_day, current_day, lwp_leave_type)

                        current_day += timedelta(days=1)

                    except Exception:
                        current_day += timedelta(days=1)
                        continue

    @api.depends('date_from', 'date_to', 'resource_calendar_id', 'holiday_status_id.request_unit', 'request_unit_half')
    def _compute_duration(self):
        """
        Compute number_of_days & number_of_hours but exclude Saturdays & Sundays.
        """
        for leave in self:
            days = 0
            hours = 0.0

            if leave.date_from and leave.date_to:
                calendar = leave.resource_calendar_id or leave.employee_id.resource_calendar_id

                # If half-day leave is requested, handle separately
                if leave.request_unit_half:
                    # Half-day leave → fixed 0.5 days & half of hours_per_day
                    days = 0.5
                    hours = calendar.hours_per_day / 2 if calendar and calendar.hours_per_day else 0
                else:
                    # Count working days excluding weekends
                    current_day = leave.date_from.date()
                    while current_day <= leave.date_to.date():
                        if current_day.weekday() not in (5, 6):  # Skip Saturday & Sunday
                            days += 1
                        current_day += timedelta(days=1)

                    # Total hours = working days × hours_per_day
                    hours = days * (calendar.hours_per_day if calendar and calendar.hours_per_day else 0)

                # Round up if leave is counted in days
                if leave.leave_type_request_unit == 'day':
                    days = ceil(days)

            leave.number_of_days = days
            leave.number_of_hours = hours

    @api.depends('number_of_hours', 'number_of_days', 'leave_type_request_unit')
    def _compute_duration_display(self):
        """
        Show duration as "X days" or "HH:MM hours" excluding weekends.
        """
        for leave in self:
            duration = leave.number_of_days
            unit = _('days')
            display = "%g %s" % (float_round(duration, precision_digits=2), unit)

            if leave.leave_type_request_unit == "hour":
                hours, minutes = divmod(abs(leave.number_of_hours) * 60, 60)
                minutes = round(minutes)
                if minutes == 60:
                    minutes = 0
                    hours += 1
                duration = '%d:%02d' % (hours, minutes)
                unit = _("hours")
                display = f"{duration} {unit}"

            leave.duration_display = display

    def _validate_leave_days(self):
        for leave in self:
            # Block full-day leaves on weekends if no working days exist
            if leave.number_of_days == 0:
                raise ValidationError(_("You cannot request leave only on weekends (Saturday/Sunday)."))

            # Block half-day leaves on Saturday and Sunday
            if leave.request_unit_half and leave.date_from and leave.date_from.weekday() in (5, 6):
                raise ValidationError(_("Half-day leave cannot be requested on Saturday or Sunday."))

    @api.model_create_multi
    def create(self, vals):
        res = super(HrLeaveInherit, self).create(vals)
        res._validate_leave_days()  # Validate after computation
        return res

    def write(self, vals):
        res = super(HrLeaveInherit, self).write(vals)
        self._validate_leave_days()  # Validate after computation
        return res


class HrLeaveTypeInherit(models.Model):
    _inherit = 'hr.leave.type'

    auto_allocate = fields.Boolean('Auto Allocation', default=False)
    allowed_in_probation = fields.Boolean('Allow In Probation', default=False)
    leaves_quantity = fields.Integer('Total Leaves', default=0)
    prorate_basis = fields.Boolean('Prorate Basis', default=False)
    leaves_collapse = fields.Boolean('Collapse', default=True)

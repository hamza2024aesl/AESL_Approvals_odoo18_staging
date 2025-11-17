import logging
import math
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
import datetime
from datetime import datetime, timedelta, time, date
from dateutil import relativedelta as rdelta
import calendar

_logger = logging.getLogger(__name__)


class HrContractInherit(models.Model):
    _inherit = 'hr.contract'

    is_allocated = fields.Boolean()

    def deduct_leaves_with_absent_count(self, payslip_id, date_from, date_to, employee_id):
        if date_from and date_to:
            absent = 0
            lst = []
            previous_month = payslip_id.date_from + relativedelta(months=-1) + relativedelta(day=int(date_from))
            current_month = payslip_id.date_from + relativedelta(day=int(date_to))
            absent_days = self.env['hr.attendance'].search([
                ('employee_id', '=', employee_id),
                ('attendance_date', '>=', previous_month),
                ('attendance_date', '<=', current_month),
                ('status', 'not in', ['present', 'off_day']),
                ('state', '=', 'done'),
                ('on_leave', '=', False)
            ])

            for absent_day in absent_days:
                leaves = self.env['hr.leave'].search(
                    [('employee_id', '=', employee_id), ('request_date_from', '>=', absent_day.attendance_date),
                     ('request_date_to', '<=', absent_day.attendance_date), ('state', '!=', 'validate')])
                if leaves:
                    for _ in leaves:
                        absent += 1
                else:
                    absent += 1

            full_half_days = self.env['hr.attendance'].search([
                ('employee_id', '=', employee_id),
                ('attendance_date', '>=', previous_month),
                ('attendance_date', '<=', current_month),
                ('status', '=', 'present'),
                ('state', '=', 'done'),
                ('on_leave', '=', False)
            ])

            for half in full_half_days.filtered(lambda x: x.attendance_status == '3'):
                leaves = self.env['hr.leave'].search([
                    ('employee_id', '=', employee_id),
                    ('request_date_from', '>=', half.attendance_date),
                    ('request_date_to', '<=', half.attendance_date),
                    ('state', '!=', 'validate')
                ])
                count = 0
                if leaves:
                    for _ in leaves:
                        absent += 0.5
                else:
                    absent += 0.5

            for full in full_half_days.filtered(lambda x: x.attendance_status == '5'):
                leaves = self.env['hr.leave'].search([
                    ('employee_id', '=', employee_id),
                    ('request_date_from', '>=', full.attendance_date),
                    ('request_date_to', '<=', full.attendance_date),
                    ('state', '!=', 'validate')
                ])
                count = 0
                if leaves:
                    for _ in leaves:
                        absent += 1
                else:
                    absent += 1

            count = 0.0
            pl_leave_type = self.env['hr.leave.type'].search([('name', '=', 'PL')], limit=1)
            pl_leaves = self.env['hr.leave.report'].search([
                ('employee_id', '=', employee_id),
                ('holiday_status_id', '=', pl_leave_type.id)
            ])

            for pl_leave in pl_leaves:
                count += pl_leave.number_of_days

            days = 0
            if count > 0.0:
                if absent > count:
                    days = absent - count
                else:
                    days = absent

            total_days = days / 23 * 30
            frac, whole = math.modf(total_days)
            if frac < 0.5:
                total_days = whole
            elif 0.5 <= frac < 0.99:
                total_days = whole + 0.5

            return total_days

    def _is_public_holiday(self, attendance_date):
        return any(self.env['resource.calendar.leaves'].search([
            ('date_from', '<=', str(attendance_date)),
            ('date_to', '>=', str(attendance_date)),
            ('resource_id', '=', None)
        ]))

    def _count_absent_days(self, absent_day, leaves, is_att, absent):
        holiday_flag = False

        if self._is_public_holiday(absent_day.attendance_date):
            holiday_flag = True

        if leaves:
            for _ in leaves:
                if absent_day not in is_att and not holiday_flag:
                    is_att.append(absent_day)
                    absent += 1
        else:
            if absent_day not in is_att and not holiday_flag:
                is_att.append(absent_day)
                absent += 1

        return absent, is_att

    def get_attendance_with_absent_count(self, payslip_id, date_from, date_to, employee_id):
        if date_from and date_to:
            absent = 0
            is_att = []
            previous_month = payslip_id.date_from + relativedelta(months=-1) + relativedelta(day=int(date_from))
            current_month = payslip_id.date_from + relativedelta(day=int(date_to))

            update_days = self.env['hr.attendance'].search([
                ('employee_id', '=', employee_id),
                ('attendance_date', '>=', previous_month),
                ('attendance_date', '<=', current_month),
                ('status', 'not in', ['off_day']),
                ('extra_day', '!=', 'yes'),
                ('state', '=', 'done'),
                ('on_leave', '=', False)
            ])

            for update_day in update_days:
                leaves = self.env['hr.leave'].search([
                    ('employee_id', '=', employee_id),
                    ('request_date_from', '>=', update_day.attendance_date),
                    ('state', '=', 'validate')
                ])
                if leaves:
                    for _ in leaves.filtered(
                            lambda x: (
                                    x.request_date_from >= update_day.attendance_date
                                    and x.request_date_to <= update_day.attendance_date
                                    if x.request_date_to else False
                            )
                    ):
                        update_day.on_leave = True
                    for _ in leaves.filtered(
                            lambda x: x.request_date_from == update_day.attendance_date and x.request_unit_half):
                        update_day.on_leave = True

            absent_days = self.env['hr.attendance'].search([
                ('employee_id', '=', employee_id),
                ('attendance_date', '>=', previous_month),
                ('attendance_date', '<=', current_month),
                ('extra_day', '!=', 'yes'),
                ('status', 'not in', ['present', 'off_day']),
                ('state', '=', 'done'),
                ('on_leave', '=', False)
            ])

            for absent_day in absent_days.filtered(lambda x: x.status2 == 'missed_check_in' or x.status == 'absent'):
                leaves = self.env['hr.leave'].search([
                    ('employee_id', '=', employee_id),
                    ('request_date_from', '>=', absent_day.attendance_date),
                    ('request_date_to', '<=', absent_day.attendance_date),
                    ('state', '!=', 'validate')
                ])
                holiday_flag = False

                if self._is_public_holiday(absent_day.attendance_date):
                    holiday_flag = True

                if leaves:
                    for _ in leaves:
                        if absent_day not in is_att and not holiday_flag:
                            is_att.append(absent_day)
                            absent += 1
                else:
                    if absent_day not in is_att and not holiday_flag:
                        is_att.append(absent_day)
                        absent += 1

                absent, is_att = self._count_absent_days(absent_day, leaves, is_att, absent)

            _logger.info('IVIS - Full Day Absents %s------ ' % absent)

            full_half_days = self.env['hr.attendance'].search([
                ('employee_id', '=', employee_id),
                ('attendance_date', '>=', previous_month),
                ('attendance_date', '<=', current_month),
                ('extra_day', '!=', 'yes'),
                ('status', 'in', ['present', 'missed_check']),
                ('state', '=', 'done'),
                ('on_leave', '=', False)
            ])

            for half in full_half_days.filtered(lambda x: x.attendance_status == '3'):
                leaves = self.env['hr.leave'].search([
                    ('employee_id', '=', employee_id),
                    ('request_date_from', '>=', half.attendance_date),
                    ('request_date_to', '<=', half.attendance_date),
                    ('state', '!=', 'validate')
                ])
                holiday_flag = False

                if self._is_public_holiday(half.attendance_date):
                    holiday_flag = True

                if leaves:
                    for _ in leaves:
                        if half not in is_att and not holiday_flag:
                            is_att.append(half)
                            absent += 0.5
                else:
                    if half not in is_att and not holiday_flag:
                        is_att.append(half)
                        absent += 0.5

                absent, is_att = self._count_absent_days(half, leaves, is_att, absent)

            _logger.info('IVIS - Half day Absents count (Attendance status 3 %s------ ' % absent)

            for full in full_half_days.filtered(lambda x: x.attendance_status == '5'):
                leaves = self.env['hr.leave'].search([
                    ('employee_id', '=', employee_id),
                    ('request_date_from', '>=', full.attendance_date),
                    ('request_date_to', '<=', full.attendance_date),
                    ('state', '!=', 'validate')
                ])
                holiday_flag = False

                if self._is_public_holiday(full.attendance_date):
                    holiday_flag = True

                if leaves:
                    for _ in leaves:
                        if full not in is_att and not holiday_flag:
                            is_att.append(full)
                            absent += 1
                else:
                    if full not in is_att and not holiday_flag:
                        is_att.append(full)
                        absent += 1

                absent, is_att = self._count_absent_days(full, leaves, is_att, absent)

            _logger.info('IVIS - Half day Absents count (Attendance status 5) %s------ ' % absent)

            # lwp_negative = self.get_leaves_balance_run(employee_id)   27june2022
            lwp_negative = 0  # 27june2022
            _logger.info('LWP negative %s------ ' % lwp_negative)
            total_days = (absent + lwp_negative) / 23 * 30
            return round(total_days)

    def create_leaves(self, contract, duration, leave_type):
        desc = ''
        # Get the previous month
        prev_month = (date.today().replace(day=1) - timedelta(days=1)).month
        # Get the name of the previous month
        prev_month_name = calendar.month_name[prev_month]

        desc = 'PL Allocation - ' + prev_month_name + ' ' + str(date.today().year)

        vals = {
            'employee_id': contract.employee_id.id,
            'name': desc,
            'number_of_days': str(duration),
            'holiday_status_id': leave_type,
        }
        rec = self.env['hr.leave.allocation'].create(vals)
        rec.action_approve()

    def get_total_leaves_types(self, company_id):
        return self.env['hr.leave.type'].search([('auto_allocate', '=', True), ('company_id', '=', company_id.id)])

    def assign_probation_leaves(self, contract):
        probation_leaves = contract.env['hr.leave.type'].search(
            [('auto_allocate', '=', True), ('allowed_in_probation', '=', True),
             ('company_id','=', contract.company_id.id)])
        for probation_leave in probation_leaves:
            duration = rdelta.relativedelta(contract.trial_date_end, contract.date_start)
            if probation_leave.leaves_quantity / 12.0 * duration.months > 0:
                if probation_leave.prorate_basis:
                    if date.today().day == contract.date_start.day:
                        leaves = probation_leave.leaves_quantity / 12.0
                        self.create_leaves(contract, leaves, probation_leave.id)
                    if date.today().month == 2 and date.today().day == 28:
                        if contract.date_start.day in [29, 30, 31]:
                            leaves = probation_leave.leaves_quantity / 12.0
                            self.create_leaves(contract, leaves, probation_leave.id)

    def assign_permanent_leaves(self, contract):
        fiscal_year_end_str = str(date.today().year) + '-' + str(12) + '-' + str(31)
        fiscal_year_end = (datetime.strptime(fiscal_year_end_str, '%Y-%m-%d').date())
        duration = rdelta.relativedelta(fiscal_year_end, contract.date_start)
        dur = duration.months
        leave_types = self.get_total_leaves_types(contract.company_id)
        if len(leave_types) == 0:
            return
        for leave_type in leave_types:
            if contract.contract_type_id.code == 'Permanent':
                if leave_type.leaves_quantity > 0:
                    if leave_type.leaves_collapse:
                        leaves = 0
                        if 'PL' not in leave_type.name:
                            if not contract.is_allocated:
                                if not leave_type.prorate_basis:
                                    leaves = leave_type.leaves_quantity
                                if leave_type.prorate_basis:
                                    leaves = (leave_type.leaves_quantity / 12) * dur
                                self.create_leaves(contract, leaves, leave_type.id)
                        if 'PL' in leave_type.name:
                            leaves = leave_type.leaves_quantity / 12.0
                            self.create_leaves(contract, leaves, leave_type.id)
                    else:
                        leaves = 0
                        previous_days = 0.0
                        record = contract.env['hr.leave.report'].search(
                            [('employee_id', '=', contract.employee_id.id),
                             ('holiday_status_id', '=', leave_type.id), ('state', 'in', ['validate', 'refuse'])])
                        for rec in record:
                            previous_days = rec.number_of_days + previous_days

                        if 'PL' not in leave_type.name:
                            if not contract.is_allocated:
                                if not leave_type.prorate_basis:
                                    leaves = leave_type.leaves_quantity
                                if leave_type.prorate_basis:
                                    leaves = (leave_type.leaves_quantity / 12) * dur
                                self.create_leaves(contract, leaves, leave_type.id)
                        if 'PL' in leave_type.name:
                            leaves = leave_type.leaves_quantity / 12.0
                            if leaves + previous_days >= leave_type.max_days:
                                pass
                            else:
                                self.create_leaves(contract, leaves, leave_type.id)
        contract.is_allocated = True

    def leaves_scheduler(self):
        contracts = self.env['hr.contract'].search([('state', '=', 'open')])
        for contract in contracts:
            if contract.contract_type_id.code == 'Probation' and contract.date_start and contract.trial_date_end:
                self.assign_probation_leaves(contract)
            elif contract.contract_type_id.code == 'Permanent':
                if date.today().day == 1:
                    self.assign_permanent_leaves(contract)
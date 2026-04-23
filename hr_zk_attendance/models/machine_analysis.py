# -*- coding: utf-8 -*-
###################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#    Copyright (C) 2018-TODAY Cybrosys Technologies(<http://www.cybrosys.com>).
#    Author: cybrosys(<https://www.cybrosys.com>)
#
#    This program is free software: you can modify
#    it under the terms of the GNU Affero General Public License (AGPL) as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###################################################################################
from odoo import tools
from odoo import models, fields, api, _
from datetime import datetime, timedelta
import pytz



class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    device_id = fields.Char(string='Biometric Device ID')


class ZkMachine(models.Model):
    _name = 'zk.machine.attendance'
    _description = 'ZK Machine Attendance'
    _inherit = 'hr.attendance'

    @api.constrains('check_in', 'check_out', 'employee_id')
    def _check_validity(self):
        """overriding the __check_validity function for employee attendance."""
        pass

    def _default_employee(self):
        pass

    employee_id = fields.Many2one('hr.employee', string="Employee", default=_default_employee, required=False)
    machine_code = fields.Char(string='Machine')
    punch_type = fields.Selection([('0', 'Check In'),
                                   ('1', 'Check Out'),
                                   ('2', 'Break Out'),
                                   ('3', 'Break In'),
                                   ('4', 'Overtime In'),
                                   ('5', 'Overtime Out')],
                                  string='Punching Type')

    attendance_type = fields.Selection([('1', 'Finger'),
                                        ('15', 'Face'),
                                        ('2', 'Type_2'),
                                        ('3', 'Password'),
                                        ('4', 'Card')], string='Category')
    device_id = fields.Char(string='Biometric Device ID')
    punching_time = fields.Datetime(string='Punching Time')
    punching_date = fields.Date(string='Punching Date')
    address_id = fields.Many2one('res.partner', string='Working Address')
    is_attendance_machine = fields.Boolean()
    zk_process_status = fields.Selection([('unprocessed', 'Unprocessed'), ('processed', 'Processed')], default='unprocessed')
    shift = fields.Selection([('day', 'Day'), ('night', 'Night')], compute="_get_shift", string="Shift", store=True)
    atten_mode = fields.Selection([
        ('Device', 'Device'),
        ('Import', 'Import'),
        ('Web Service', 'Web Service')
    ], string="Attendance Mode")

    def scheduled_attendance_check(self):
        EmployeeObj = self.env["hr.employee"]
        AttendanceObj = self.env["hr.attendance"]
        AnalysisObj = self.env["zk.machine.attendance"]

        for employee in EmployeeObj.search([]):
            self.process_employee_attendance(employee, AttendanceObj, AnalysisObj)

    def checkin_min(self, machine_analysis_in):
        # Extracting unique dates from machine_analysis_in
        unique_dates = set(machine_analysis_in.mapped('punching_date'))

        machine_analysis_data = []
        for date in unique_dates:
            # Filtering machine_analysis_in for a particular date
            records_for_date = machine_analysis_in.filtered(lambda x: x.punching_date == date)

            # Finding the record with minimum time for the current date
            min_time_record = min(records_for_date, key=lambda x: x.punching_time)

            # Adding the minimum time record for the current date to machine_analysis_data
            machine_analysis_data.append(min_time_record)
        return machine_analysis_data

    def checkout_max(self, machine_analysis_out, attendance_id):
        unique_dates = set(machine_analysis_out.mapped('punching_date'))

        for date in unique_dates:
            # Filtering machine_analysis_out for a particular date
            records_for_date = machine_analysis_out.filtered(lambda x: x.punching_date == date)

            # Finding the record with maximum time for the current date
            max_time_record = max(records_for_date, key=lambda x: x.punching_time)

            if attendance_id.check_in > max_time_record.punching_time:
                attendance_id.check_out = attendance_id.check_in
                attendance_id.check_in = max_time_record.punching_time
            else:
                attendance_id.check_out = max_time_record.punching_time
            attendance_id.status = 'OK'
            max_time_record.zk_process_status = 'processed'

    def get_checkout_max(self, machine_analysis_out):
        # Extracting unique dates from machine_analysis_in
        unique_dates = set(machine_analysis_out.mapped('punching_date'))

        machine_analysis_data = []
        for date in unique_dates:
            # Filtering machine_analysis_in for a particular date
            records_for_date = machine_analysis_out.filtered(lambda x: x.punching_date == date)

            # Finding the record with minimum time for the current date
            min_time_record = max(records_for_date, key=lambda x: x.punching_time)

            # Adding the minimum time record for the current date to machine_analysis_data
            machine_analysis_data.append(min_time_record)
        return machine_analysis_data

    def process_employee_attendance(self, employee, AttendanceObj, AnalysisObj):
        attendance_id = AttendanceObj.search([("employee_id", "=", employee.id)], limit=1)
        if attendance_id:
            if not attendance_id.check_out:
                machine_analysis_out = AnalysisObj.search([("employee_id", '=', employee.id),
                                                           ("punch_type", "=", "1"),
                                                           ('zk_process_status', '=', 'unprocessed'),
                                                           ('punching_date', '=', attendance_id.check_in.date())])

                if machine_analysis_out:
                    self.checkout_max(machine_analysis_out, attendance_id)
                else:
                    attendance_id.check_out = attendance_id.check_in
                    attendance_id.status = 'Missed Check Out'
            else:
                machine_analysis_in = AnalysisObj.search([("employee_id", '=', employee.id),
                                                          ("punch_type", "=", "0"),
                                                          ("punching_date", ">", attendance_id.check_in),
                                                          ('zk_process_status', '=', 'unprocessed')])
                if machine_analysis_in:
                    machine_analysis_data = self.checkin_min(machine_analysis_in)
                    sorted_machine_analysis_in = sorted(machine_analysis_data, key=lambda x: x.id)
                    for in_data in sorted_machine_analysis_in:
                        same_date_atten = AttendanceObj.search([('employee_id', '=', employee.id)])
                        if same_date_atten.filtered(lambda x: x.check_in.date() == in_data.punching_time.date()):
                            continue
                        attendance_id = AttendanceObj.create({
                            'employee_id': employee.id,
                            'check_in': in_data.punching_time,
                        })
                        in_data.zk_process_status = 'processed'
                        machine_analysis_out = AnalysisObj.search([("employee_id", '=', employee.id),
                                                                   ("punch_type", "=", "1"),
                                                                   ('zk_process_status', '=', 'unprocessed'),
                                                                   ('punching_date', '=', in_data.punching_date)])
                        if machine_analysis_out:
                            self.checkout_max(machine_analysis_out, attendance_id)
                        else:
                            attendance_id.check_out = in_data.punching_time
                            attendance_id.status = 'Missed Check Out'

                    # process only check out records
                    machine_analysis_out = AnalysisObj.search([("employee_id", '=', employee.id),
                                                               ("punch_type", "=", "1"),
                                                               ("punching_time", ">", attendance_id.check_in),
                                                               ('zk_process_status', '=', 'unprocessed')])
                    if machine_analysis_out:
                        machine_analysis_out = self.get_checkout_max(machine_analysis_out)
                        sorted_machine_analysis_out = sorted(machine_analysis_out, key=lambda x: x.id)

                        for out_data in sorted_machine_analysis_out:
                            attendance_id = AttendanceObj.search([('employee_id', '=', employee.id)])
                            if not attendance_id.filtered(lambda x: x.check_in.date() == out_data.punching_time.date()):
                                attendance_id = AttendanceObj.create({
                                    'employee_id': employee.id,
                                    'check_in': out_data.punching_time,
                                    'check_out': out_data.punching_time,
                                    'status': 'Missed Check In'
                                })
                                out_data.zk_process_status = 'processed'

        else:
            machine_analysis_in = AnalysisObj.search([("employee_id", '=', employee.id),
                                                      ("punch_type", "=", "0"),
                                                      ('zk_process_status', '=', 'unprocessed')])
            if machine_analysis_in:
                machine_analysis_data = self.checkin_min(machine_analysis_in)

                sorted_machine_analysis_in = sorted(machine_analysis_data, key=lambda x: x.id)
                for in_data in sorted_machine_analysis_in:
                    attendance_id = AttendanceObj.create({
                        'employee_id': employee.id,
                        'check_in': in_data.punching_time,
                    })
                    in_data.zk_process_status = 'processed'
                    machine_analysis_out = AnalysisObj.search([("employee_id", '=', employee.id),
                                                               ("punch_type", "=", "1"),
                                                               ('zk_process_status', '=', 'unprocessed'),
                                                               ('punching_date', '=', in_data.punching_date)])
                    if machine_analysis_out:
                        self.checkout_max(machine_analysis_out, attendance_id)
                    else:
                        attendance_id.check_out = in_data.punching_time
                        attendance_id.status = 'Missed Check Out'

                # process only check out records
                machine_analysis_out = AnalysisObj.search([("employee_id", '=', employee.id),
                                                           ("punch_type", "=", "1"),
                                                           ('zk_process_status', '=', 'unprocessed')])
                if machine_analysis_out:
                    machine_analysis_out = self.get_checkout_max(machine_analysis_out)
                    sorted_machine_analysis_out = sorted(machine_analysis_out, key=lambda x: x.id)


                    for out_data in sorted_machine_analysis_out:
                        attendance_id = AttendanceObj.search([('employee_id', '=', employee.id)])
                        if not attendance_id.filtered(lambda x: x.check_in.date() == out_data.punching_time.date()):
                            attendance_id = AttendanceObj.create({
                                'employee_id': employee.id,
                                'check_in': out_data.punching_time,
                                'check_out': out_data.punching_time,
                                'status': 'Missed Check In'
                            })
                            out_data.zk_process_status = 'processed'

    @api.model_create_multi
    def create(self, vals):
        data = super(ZkMachine, self).create(vals)
        if self.env.context.get('webservice') == True:
            datetime_obj = data.punching_time
            user_timezone = pytz.timezone(data.create_uid.tz or 'GMT')
            local_dt = datetime_obj.astimezone(user_timezone)
            new_datetime = datetime_obj - local_dt.utcoffset()
            data.punching_time = new_datetime.strftime('%Y-%m-%d %H:%M:%S')
            data.punching_date = new_datetime.strftime('%Y-%m-%d')
        return data

class ReportZkDevice(models.Model):
    _name = 'zk.report.daily.attendance'
    _description = 'Daily Attendance Report'
    _auto = False
    _order = 'punching_day desc'

    name = fields.Many2one('hr.employee', string='Employee')
    punching_day = fields.Datetime(string='Date')
    address_id = fields.Many2one('res.partner', string='Working Address')
    attendance_type = fields.Selection([('1', 'Finger'),
                                        ('15', 'Face'),
                                        ('2', 'Type_2'),
                                        ('3', 'Password'),
                                        ('4', 'Card')],
                                       string='Category')
    punch_type = fields.Selection([('0', 'Check In'),
                                   ('1', 'Check Out'),
                                   ('2', 'Break Out'),
                                   ('3', 'Break In'),
                                   ('4', 'Overtime In'),
                                   ('5', 'Overtime Out')], string='Punching Type')
    punching_time = fields.Datetime(string='Punching Time')

    def init(self):
        tools.drop_view_if_exists(self._cr, 'zk_report_daily_attendance')
        query = """
            create or replace view zk_report_daily_attendance as (
                select
                    min(z.id) as id,
                    z.employee_id as name,
                    z.write_date as punching_day,
                    z.address_id as address_id,
                    z.attendance_type as attendance_type,
                    z.punching_time as punching_time,
                    z.punch_type as punch_type
                from zk_machine_attendance z
                    join hr_employee e on (z.employee_id=e.id)
                GROUP BY
                    z.employee_id,
                    z.write_date,
                    z.address_id,
                    z.attendance_type,
                    z.punch_type,
                    z.punching_time
            )
        """
        self._cr.execute(query)

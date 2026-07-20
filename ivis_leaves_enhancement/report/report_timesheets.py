import datetime
from dateutil.relativedelta import *
from odoo import models, api


class ReportTimesheet(models.AbstractModel):
    _name = 'report.ga_leaves_enhancement.report_emp_time_sheet'
    _description = 'TimeSheet Report'

    @api.model
    def render_html(self, docids, data=None):
        employee_type = {}
        leaves_arr = []
        off_days = 0
        absent_days = 0
        present_days = 0
        early_departure_days = 0
        late_coming_days = 0
        on_time_days = 0
        self.model = self.env.context.get('active_model')
        docs = self.env[self.model].browse(data['form']['employee'])
        employee_type = self.get_employee_type(data['form']['employee'])
        for line in self.env['hr.leave.status'].search([]):
            leaves_arr.append({'leave_type': line.name,
                               'total': self.get_employee_leave(data['form']['employee'], line.id, 'add', 'validate'),
                               'avail_in_month': self.get_employee_leave_avail(data['form']['employee'], line.id,
                                                                               'remove',
                                                                               'validate',
                                                                               data['form']['from_date'],
                                                                               data['form']['to_date']),
                               'avail_in_year': self.get_employee_leave_avail(data['form']['employee'], line.id,
                                                                              'remove', 'validate',
                                                                              datetime.datetime.now().date().replace(
                                                                                  month=1),
                                                                              datetime.datetime.now().date().replace(
                                                                                  month=1) + relativedelta(years=+1,
                                                                                                           days=-1)),
                               'remaining': self.get_employee_leave(data['form']['employee'], line.id, 'add',
                                                                    'validate') - self.get_employee_leave(
                                   data['form']['employee'], line.id, 'remove', 'validate')
                               })
        timesheets = self.get_timesheets(data['form'])
        # self.env.cr.execute(
        #     """select count(*) from working_schedule_holidays where date >= '{0}' and date <= '{1}'""".format(
        #         data['form']['from_date'], data['form']['to_date']))
        # holiday_count = str(self.env.cr.dictfetchall()[0]['count']).split('L')[0]
        emp_contract = self.env['hr.contract'].search([('employee_id', '=', data['form']['employee'])])
        for rec in timesheets:
            if rec['schedules'] == None:
                off_days += 1
            if rec['remarks'] == 'absent' and rec['schedules'] != None:
                absent_days += 1
            if rec['remarks'] == 'present':
                present_days += 1
            if rec['early_out'] != 0.0:
                early_departure_days += 1
            if rec['late_in'] != 0.0:
                late_coming_days += 1
            if rec['on_time_arrival'] == '0':
                on_time_days += 1
        number_of_days = int(str(
            datetime.datetime.strptime(data['form']['to_date'], '%Y-%m-%d').date() - datetime.datetime.strptime(
                data['form']['from_date'], '%Y-%m-%d').date())[:2]) + 1
        if data['form']['from_date'] and data['form']['to_date']:
            period = "From Date: " + datetime.datetime.strptime(data['form']['from_date'], '%Y-%m-%d').strftime(
                '%d-%b-%y') + " To Date: " + datetime.datetime.strptime(data['form']['to_date'], '%Y-%m-%d').strftime(
                '%d-%b-%y')
        docargs = {
            'doc_ids': self.ids,
            'doc_model': self.model,
            'docs': docs,
            'timesheets': timesheets,
            'leaves': leaves_arr,
            'period': period,
            'employee_type': employee_type,
            'total_days': number_of_days,
            'off_days': off_days,
            'absent_days': absent_days,
            'present_days': present_days,
            'early_departure_days': early_departure_days,
            'late_coming_days': late_coming_days,
            'on_time_days': on_time_days,
            'no_of_holiday': emp_contract.holidays_count(data['form']['from_date'], data['form']['to_date']),
            'no_of_leave': self.get_leaves_count(data['form']['employee'], data['form']['from_date'],
                                                 data['form']['to_date'])
        }
        return self.env['report'].render('ivis_leaves_enhancement.report_emp_time_sheet', docargs)

    def get_employee_leave_avail(self, employee_id, leave, type, state, date_from, date_to):
        self.env.cr.execute(
            """select sum(number_of_days_temp) from hr_holidays where holiday_status_id={0} and employee_id={1} and type='{2}' and state='{3}' and date_from>='{4}' and date_to<='{5}'""".format(
                leave,
                employee_id, type, state, date_from, date_to))
        ListOfDictionary = self.env.cr.dictfetchall()[0]
        if ListOfDictionary['sum'] == None:
            return 0.0
        else:
            return ListOfDictionary['sum']

    def get_employee_leave(self, employee_id, leave, type, state):
        self.env.cr.execute(
            """select sum(number_of_days_temp) from hr_holidays where holiday_status_id={0} and employee_id={1} and type='{2}' and state='{3}'""".format(
                leave,
                employee_id, type, state))
        ListOfDictionary = self.env.cr.dictfetchall()[0]
        if ListOfDictionary['sum'] == None:
            return 0.0
        else:
            return ListOfDictionary['sum']

    def get_employee_type(self, x):
        c1 = self.env['hr.contract'].search([('employee_id', '=', x)])
        if c1:
            return c1.read(['emp_type', 'date_start'])[0]

    def get_scheduled_start(self, day, calendar):
        rc = self.env['resource.calendar.attendance'].search([('calendar_id', '=', calendar), ('dayofweek', '=', day)])
        if rc:
            return rc.read(['name', 'hour_from', 'hour_to'])[0]

    def get_timesheets(self, docs):
        if docs['from_date'] and docs['to_date']:
            h1 = self.env['hr.employee'].search([('id', '=', docs['employee'])])
            rec = self.env['hr.attendance'].search([('employee_id', '=', docs['employee']),
                                                    ('check_in', '>=',
                                                     docs['from_date']),
                                                    ('check_out', '<=',
                                                     docs['to_date'])],
                                                   order='check_in')
            records = []
            for r in rec:
                vals = {
                    'time_in': datetime.datetime.strptime(
                        str(datetime.datetime.strptime(r.check_in, '%Y-%m-%d %H:%M:%S') + relativedelta(hours=5)),
                        '%Y-%m-%d %H:%M:%S').strftime('%d-%m-%Y %H:%M'),
                    'schedules': self.get_scheduled_start(
                        datetime.datetime.strptime(r.check_in, '%Y-%m-%d %H:%M:%S').date().weekday(),
                        h1.calendar_id.id),
                    'dated': datetime.datetime.strptime(r.check_in, '%Y-%m-%d %H:%M:%S').strftime('%d-%m-%Y'),
                    'time_out': datetime.datetime.strptime(
                        str(datetime.datetime.strptime(r.check_out, '%Y-%m-%d %H:%M:%S') + relativedelta(hours=5)),
                        '%Y-%m-%d %H:%M:%S').strftime('%d-%m-%Y %H:%M'),
                    'work': r.worked_hours,
                    'overtime': r.over_time_hr,
                    'late_in': r.late_in_time,
                    'early_out': r.early_time_out,
                    'remarks': r.status,
                    'on_time_arrival': r.in_status
                }
                records.append(vals)
        return records

    def get_leaves_count(self, employee_id, from_date, to_date):
        count_days = self.env['hr.attendance'].search(
            [('employee_id', '=', employee_id), ('check_in', '>=', from_date),
             ('check_in', '<=', to_date), ('on_leave', '=', True)])
        if count_days:
            return len(count_days)
        else:
            return 0

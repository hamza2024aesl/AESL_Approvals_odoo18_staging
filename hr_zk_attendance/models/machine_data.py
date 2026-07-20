from odoo import fields, models


class MachineData(models.Model):
    _name = 'machine.data'
    _description = 'Machine Data'
    _rec_name = 'employee_code'

    machine_code = fields.Char('Machine Code')
    employee_name = fields.Many2one('hr.employee', 'Employee Name', index=True)
    department_id = fields.Many2one('hr.department', 'Department', related='employee_name.department_id')
    employee_code = fields.Char('Employee Code')
    date = fields.Date('Date', index=True)
    time = fields.Datetime('Time', index=True)
    type = fields.Selection([('in', 'In'), ('out', 'Out')])
    status = fields.Selection([('unprocessed', 'Unprocessed'), ('processed', 'Processed')], default='unprocessed')
    shift = fields.Selection([('day', 'Day'), ('night', 'Night')], compute="_get_shift", string="Shift", store=True)

    def scheduled_attendance_check(self):
        EmployeeObj = self.env["hr.employee"]
        AttendacneObj = self.env["hr.attendance"]
        MachineObj = self.env["machine.data"]

        for employee in EmployeeObj.search([]):
            if employee.name == 'Muhammad Azzam Jamali':
                print(employee.name)
            self.process_employee_attendance(employee, AttendacneObj, MachineObj)

    def checkin_min(self, machine_data_in):
        # Extracting unique dates from machine_data_in
        unique_dates = set(machine_data_in.mapped('date'))

        machine_data = []
        for date in unique_dates:
            # Filtering machine_data_in for a particular date
            records_for_date = machine_data_in.filtered(lambda x: x.date == date)

            # Finding the record with minimum time for the current date
            min_time_record = min(records_for_date, key=lambda x: x.time)

            # Adding the minimum time record for the current date to machine_data
            machine_data.append(min_time_record)
        return machine_data

    def checkout_max(self, machine_data_out, attendance_id):
        unique_dates = set(machine_data_out.mapped('date'))

        for date in unique_dates:
            # Filtering machine_data_out for a particular date
            records_for_date = machine_data_out.filtered(lambda x: x.date == date)

            # Finding the record with maximum time for the current date
            max_time_record = max(records_for_date, key=lambda x: x.time)

            if attendance_id.check_in > max_time_record.time:
                attendance_id.check_out = attendance_id.check_in
                attendance_id.check_in = max_time_record.time
            else:
                attendance_id.check_out = max_time_record.time
            attendance_id.status = 'OK'
            max_time_record.status = 'processed'

    def get_checkout_max(self, machine_data_out):
        # Extracting unique dates from machine_data_in
        unique_dates = set(machine_data_out.mapped('date'))

        machine_data = []
        for date in unique_dates:
            # Filtering machine_data_in for a particular date
            records_for_date = machine_data_out.filtered(lambda x: x.date == date)

            # Finding the record with minimum time for the current date
            min_time_record = max(records_for_date, key=lambda x: x.time)

            # Adding the minimum time record for the current date to machine_data
            machine_data.append(min_time_record)
        return machine_data

    def process_employee_attendance(self, employee, AttendacneObj, MachineObj):
        attendance_id = AttendacneObj.search([("employee_id", "=", employee.id)], limit=1)
        if attendance_id:
            if not attendance_id.check_out:
                machine_data_out = MachineObj.search([("employee_name", '=', employee.id),
                                                      ("type", "=", "out"),
                                                      ('status', '=', 'unprocessed'),
                                                      ('date', '=', attendance_id.check_in.date())])

                if machine_data_out:
                    self.checkout_max(machine_data_out, attendance_id)
                else:
                    attendance_id.check_out = attendance_id.check_in
                    attendance_id.status = 'Missed Check Out'
            else:
                machine_data_in = MachineObj.search([("employee_name", '=', employee.id),
                                                     ("type", "=", "in"),
                                                     ("time", ">", attendance_id.check_in),
                                                     ('status', '=', 'unprocessed')])
                if machine_data_in:
                    machine_data = self.checkin_min(machine_data_in)
                    sorted_machine_data_in = sorted(machine_data, key=lambda x: x.id)
                    for in_data in sorted_machine_data_in:
                        same_date_atten = AttendacneObj.search([('employee_id', '=', employee.id)])
                        if same_date_atten.filtered(lambda x: x.check_in.date() == in_data.time.date()):
                            continue
                        attendance_id = AttendacneObj.create({
                            'employee_id': employee.id,
                            'check_in': in_data.time,
                        })
                        in_data.status = 'processed'
                        machine_data_out = MachineObj.search([("employee_name", '=', employee.id),
                                                              ("type", "=", "out"),
                                                              ('status', '=', 'unprocessed'),
                                                              ('date', '=', in_data.date)])
                        if machine_data_out:
                            self.checkout_max(machine_data_out, attendance_id)
                        else:
                            attendance_id.check_out = in_data.time
                            attendance_id.status = 'Missed Check Out'

                    # process only check out records
                    machine_data_out = MachineObj.search([("employee_name", '=', employee.id),
                                                          ("type", "=", "out"),
                                                          ("time", ">", attendance_id.check_in),
                                                          ('status', '=', 'unprocessed')])
                    if machine_data_out:
                        machine_data_out = self.get_checkout_max(machine_data_out)
                        sorted_machine_data_out = sorted(machine_data_out, key=lambda x: x.id)

                        for out_data in sorted_machine_data_out:
                            attendance_id = AttendacneObj.search([('employee_id', '=', employee.id)])
                            if not attendance_id.filtered(lambda x: x.check_in.date() == out_data.time.date()):
                                attendance_id = AttendacneObj.create({
                                    'employee_id': employee.id,
                                    'check_in': out_data.time,
                                    'check_out': out_data.time,
                                    'status': 'Missed Check In'
                                })
                                out_data.status = 'processed'

        else:
            machine_data_in = MachineObj.search([("employee_name", '=', employee.id),
                                                 ("type", "=", "in"),
                                                 ('status', '=', 'unprocessed')])
            if machine_data_in:
                machine_data = self.checkin_min(machine_data_in)

                sorted_machine_data_in = sorted(machine_data, key=lambda x: x.id)
                for in_data in sorted_machine_data_in:
                    attendance_id = AttendacneObj.create({
                        'employee_id': employee.id,
                        'check_in': in_data.time,
                    })
                    in_data.status = 'processed'
                    machine_data_out = MachineObj.search([("employee_name", '=', employee.id),
                                                          ("type", "=", "out"),
                                                          ('status', '=', 'unprocessed'), ('date', '=', in_data.date)])
                    if machine_data_out:
                        self.checkout_max(machine_data_out, attendance_id)
                    else:
                        attendance_id.check_out = in_data.time
                        attendance_id.status = 'Missed Check Out'

                # process only check out records
                machine_data_out = MachineObj.search([("employee_name", '=', employee.id),
                                                     ("type", "=", "out"),
                                                     ('status', '=', 'unprocessed')])
                if machine_data_out:
                    machine_data_out = self.get_checkout_max(machine_data_out)
                    sorted_machine_data_out = sorted(machine_data_out, key=lambda x: x.id)

                    for out_data in sorted_machine_data_out:
                        attendance_id = AttendacneObj.search([('employee_id', '=', employee.id)])
                        if not attendance_id.filtered(lambda x: x.check_in.date() == out_data.time.date()):
                            attendance_id = AttendacneObj.create({
                                'employee_id': employee.id,
                                'check_in': out_data.time,
                                'check_out': out_data.time,
                                'status': 'Missed Check In'
                            })
                            out_data.status = 'processed'

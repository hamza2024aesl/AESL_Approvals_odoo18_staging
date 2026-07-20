from odoo import fields, models, api


class Machinedata(models.Model):
    _name = 'machine.data'
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

    @api.depends('employee_name')
    def _get_shift(self):
        self.shift = self.employee_name.resource_calendar_id.shift

    @api.model
    def _CRON_Attendance(self):
        # Import Machines's Data to Temporary Table (Machine Attendance)    # Obsolete
        machines = self.env['zk.machine'].search([])
        for machine in machines:
            machine.download_attendance()

    @api.model
    def _CRON_fetch_attendance(self):
        # Import Machines's Data to Temporary Table (Machine Attendance)        
        machines = self.env['zk.machine'].search([])
        for machine in machines:
            machine.download_attendance_in_odoo()

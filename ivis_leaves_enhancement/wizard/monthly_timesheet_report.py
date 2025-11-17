from odoo import fields, models


class MonthlyTimesheetReport(models.TransientModel):
    _name = 'monthly.timesheet.report'
    _description = 'Monthly Timesheet Report'

    from_date = fields.Date(string="Start Date")
    to_date = fields.Date(string="End Date")

    def monthly_time_sheet_report(self):
        data = {}
        data['form'] = self.read(['from_date', 'to_date'])[0]
        data['form'].update({'employee': self._context.get('active_id')})
        return self.env['report'].get_action(self, 'ivis_leaves_enhancement.report_emp_time_sheet', data=data)

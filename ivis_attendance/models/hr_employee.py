import pytz
from odoo import models, fields, _


class HrEmployeeInherit(models.Model):
    _inherit = 'hr.employee'

    off_day_1 = fields.Selection(
        [('0', 'Saturday'), ('1', 'Sunday'), ('2', 'Monday'),
         ('3', 'Tuesday'), ('4', 'Wednesday'), ('5', 'Thursday'),
         ('6', 'Friday')],
        default='0'
    )
    off_day_2 = fields.Selection(
        [('0', 'Saturday'), ('1', 'Sunday'), ('2', 'Monday'),
         ('3', 'Tuesday'), ('4', 'Wednesday'), ('5', 'Thursday'),
         ('6', 'Friday')],
        default='1'
    )

    def _compute_hours_last_month(self):
        """
        Compute hours in the current month, if we are the 15th of october, will compute hours from 1 oct to 15 oct
        """
        now = fields.Datetime.now()
        now_utc = pytz.utc.localize(now)
        for employee in self:
            tz = pytz.timezone(employee.tz or 'UTC')
            now_tz = now_utc.astimezone(tz)
            start_tz = now_tz.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            start_naive = start_tz.astimezone(pytz.utc).replace(tzinfo=None)
            end_tz = now_tz
            end_naive = end_tz.astimezone(pytz.utc).replace(tzinfo=None)

            hours = sum(
                att.worked_hours or 0
                for att in employee.attendance_ids.filtered(
                    lambda att: att.check_in and att.check_in >= start_naive and att.check_out and att.check_out <= end_naive
                )
            )

            employee.hours_last_month = round(hours, 2)
            employee.hours_last_month_display = "%g" % employee.hours_last_month

    def action_open_last_month_attendances(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Attendances This Month"),
            "res_model": "hr.attendance",
            "views": [[self.env.ref('hr_attendance.view_attendance_tree').id, "list"]],
            "context": {
                "create": 0
            },
            "domain": [
                ('employee_id', '=', self.id),
                ('check_in', ">=", fields.datetime.today().replace(day=1, hour=0, minute=0)),
            ],
        }

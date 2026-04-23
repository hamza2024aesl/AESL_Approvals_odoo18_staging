from odoo import models, api, fields

class HrWorkEntry(models.Model):
    _inherit = "hr.work.entry"

    @api.model_create_multi
    def create(self, vals_list):
        """
        Override create:
        - If work entry type is 'Leave' on Saturday or Sunday
        - Replace with 'Attendance' type
        """
        attendance_type = self.env.ref("hr_work_entry.work_entry_type_attendance", raise_if_not_found=False)
        for vals in vals_list:
            if "date_start" in vals and vals.get("work_entry_type_id"):
                start_date = vals["date_start"]
                if isinstance(start_date, str):
                    start_date = fields.Datetime.from_string(start_date)
                # Check if weekend
                if start_date.weekday() in (5, 6):  # Saturday=5, Sunday=6
                    if attendance_type:
                        vals["work_entry_type_id"] = attendance_type.id
                        vals["name"] = f"{attendance_type.name}: {self.env['hr.employee'].browse(vals['employee_id']).name}"

        return super().create(vals_list)

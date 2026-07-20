from datetime import datetime, timedelta
from odoo import models, fields, api


class MachineDataInherit(models.Model):
    _inherit = 'zk.machine.attendance'

    date_convert = fields.Char(string='RDate')
    time_convert = fields.Char(string='RTime')
    type_convert = fields.Char(string='Status')
    employee_code = fields.Char(string='Employeeno')

    @api.model_create_multi
    def create(self, vals_list):
        valid_vals = []

        all_employee_codes = list(set(val.get('employee_code') for val in vals_list if val.get('employee_code')))
        employee_map = {
            emp.identification_id: emp.id
            for emp in self.env['hr.employee'].search([('identification_id', 'in', all_employee_codes)])
        }

        for vals in vals_list:
            employee_code = vals.get('employee_code')
            employee_id = employee_map.get(employee_code)
            if employee_id:
                vals['employee_id'] = employee_id

                time_str = vals.get('time_convert') or ''
                if len(time_str) == 3:
                    hour = '0' + time_str[:1]
                    minute = time_str[1:]
                else:
                    hour = time_str[:2]
                    minute = time_str[2:]

                date_str = vals.get('date_convert') or ''
                date = datetime.strptime(date_str, "%Y%m%d").date()
                dt_str = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]} {hour}:{minute}:00"
                dt = datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S') + timedelta(hours=-5)

                vals['punching_date'] = date
                vals['punching_time'] = dt

                type_code = vals.get('type_convert')
                if type_code in ['01', '1']:
                    vals['punch_type'] = '0'
                    # vals['check_in_date'] = date
                    # vals['check_in_time'] = dt
                elif type_code in ['02', '2']:
                    vals['punch_type'] = '1'
                    # vals['check_out_date'] = date
                    # vals['check_out_time'] = dt

                valid_vals.append(vals)

        return super().create(valid_vals)

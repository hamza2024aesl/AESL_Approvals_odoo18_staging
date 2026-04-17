from odoo import models, fields, api,_

import datetime
from datetime import date
from odoo.exceptions import ValidationError


class EmployeeBonusWizard(models.TransientModel):
    _name = 'employee.bonus.wizard'
    _description = 'Department-wise Employee Bonus Allocation'

    line_ids = fields.One2many('employee.bonus.wizard.line', 'wizard_id', string="Department Bonus Lines")


    def apply_bonus(self):
        leave_points_dict = {
            # First Table
            "CU": 1, "CO": 4, "CP": 1, "CS": 1, "CM": 1, "CE": 1, "OE": 1,
            "ID": 1, "IS": 1, "NP": 1, "DD": 1,"SS":1, "SM":1,

            # Second Table
            "GA": 2, "GF": 2, "GI": 2, "GU": 3, "GP": 4, "GS": 4,
            "GE": 3, "GH": 3, "GN": 3
        }
        given_points_dict = {
            # First Table (Department-wise Activity and Given Points)
            "CU": 20, "CO": 120, "CP": 30, "CS": 30, "CM": 10,"SS":30, "SM":30,
            "CE": 20, "OE": 20, "ID": 30, "IS": 30, "NP": 30,"DD": 30,

            # Second Table
            "GA": 100, "GF": 100, "GI": 100, "GU": 60, "GP": 120,
            "GS": 120, "GE": 60, "GH": 60, "GN": 60
        }
        region_mapping = {
            545: 9,
            622: 7,
            411: 8
        }

        for line in self.line_ids:
            domain = [('state', '=', 'done'),('grade','!=',6), ('department_id', '=', line.department_id.id)]

            if line.region_id.name:
                domain.append(('location', '=', line.region_id.name))

            employees = self.env['appraisal.system'].search(domain)

            for employee in employees:
                bonus_record = self.env['employee.bonus'].search([
                    ('employee_id', '=', employee.employee_id.id),
                    ('date_effective', 'ilike', datetime.datetime.now().year)
                ], limit=1)

                # Activity-wise leave points fetch karna
                leave_points = leave_points_dict.get(employee.department_id.name, 0)  # Default 0 if not found
                net_points = given_points_dict.get(employee.department_id.name, 0)  # Default 0 if not found

                total_sl_cl_leave = self._leaves_count(employee)
                total_sl_cl_leave = leave_points if total_sl_cl_leave < 7.5 else 0
                dept_bonus_calc = int(line.bonus_points + total_sl_cl_leave)/net_points
                year_end_date = datetime.date(2024, 12, 31)
                year_start_date = datetime.date(2024, 1, 1)
                cutoff_date = datetime.date(2024, 6, 30)
                if year_start_date <= employee.appointment_date <= cutoff_date:
                    prop_points_days = (year_end_date - employee.appointment_date).days
                    # prop_points = prop_points_days / 365
                    prop_points = round(prop_points_days / 365, 3)
                elif employee.appointment_date > cutoff_date:
                    prop_points = 0
                else:
                    prop_points = 1
                if bonus_record:
                    raise ValidationError(_('Bonus already created for the selected department'))
                else:
                    self.env['employee.bonus'].create({
                        'appraisal_id': employee.id,
                        'emp_name': employee.employee_id.sudo().name,
                        'grade': employee.grade,
                        'employee_code': employee.employee_id.sudo().registration_number,
                        'department_id': employee.department_id.id,
                        'region_id': region_mapping.get(employee.employee_id.sudo().id, employee.employee_id.sudo().location_id.id),                      
                        #'region_id': employee.employee_id.location_id.id,
                        'total_points': net_points,
                        'given_points': line.bonus_points,
                        'leave_points': total_sl_cl_leave,
                        'proportional_points': prop_points,  # Assuming this is a placeholder
                        'availed_points': line.bonus_points + total_sl_cl_leave,
                        'bonus_amount': int(employee.gross_salary) * dept_bonus_calc * 3 * prop_points,
                        'date_effective': datetime.date.today(),
                        'prev_gross_salary': employee.gross_salary
                    })
                    employee.write({
                        'total_points': net_points,
                        'given_points': line.bonus_points,
                        'leave_points': total_sl_cl_leave,
                        'proportional_points': prop_points,  # Assuming this is a placeholder
                        'availed_points': line.bonus_points + total_sl_cl_leave,
                        'bonus_amount': int(employee.gross_salary) * dept_bonus_calc * 3 * prop_points,
                        'date_effective': datetime.date.today()
                    })
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def _leaves_count(self, employee):
        first = date(2024, 1, 1)
        last = date(2024, 12, 31)
        sl_type_id = self.env['hr.leave.type'].search([('id', '=', 20)], limit=1).id
        cl_type_id = self.env['hr.leave.type'].search([('id', '=', 21)], limit=1).id

        employee_leaves = self.env['hr.leave'].search([
            ('employee_id', '=', employee.employee_id.id),
            ('date_from', '>=', first),
            ('date_to', '<=', last),
            ('state', '=', 'validate')
        ])
        sick_leaves_count = sum(
            employee_leaves.filtered(lambda x: x.holiday_status_id.id == sl_type_id).mapped('number_of_days'))
        casual_leaves_count = sum(
            employee_leaves.filtered(lambda x: x.holiday_status_id.id == cl_type_id).mapped('number_of_days'))
        return sick_leaves_count + casual_leaves_count

class EmployeeBonusWizardLine(models.TransientModel):
    _name = 'employee.bonus.wizard.line'
    _description = 'Department Bonus Line'

    wizard_id = fields.Many2one('employee.bonus.wizard', string="Wizard Reference")
    department_id = fields.Many2one('hr.department', string="Department", required=True)
    bonus_points = fields.Float(string="Bonus Points", required=True)
    region_id = fields.Many2one('hr.work.location', "Region")
    ttl_points = fields.Integer(string="Total Points")

    @api.onchange('department_id','bonus_points')
    def on_change_dept(self):
        given_points_dict = {
            # First Table (Department-wise Activity and Given Points)
            "CU": 20, "CO": 120, "CP": 30, "CS": 30, "CM": 10, "SS":30, "SM":30,
            "CE": 20, "OE": 20, "ID": 30, "IS": 30, "NP": 30, "DD": 30,

            # Second Table
            "GA": 100, "GF": 100, "GI": 100, "GU": 60, "GP": 120,
            "GS": 120, "GE": 60, "GH": 60, "GN": 60
        }
        dept_list = []
        net_list = []
        bonus_list = []
        for val in self:
            if val.department_id:
                net_points = given_points_dict.get(val.department_id.name, 0)  # Default 0 if not found
                val.ttl_points = net_points
                if val.bonus_points and val.bonus_points > net_points:
                    if len(self) >1:
                        dept_list.append(val.department_id.name)
                        net_list.append(net_points)
                        bonus_list.append(val.bonus_points)

                    else:
                        raise ValidationError(_(
                            "Bonus points cannot exceed the recommended points for the department.\n\n"
                            "Department: %s\nRecommended Points: %d\nGiven Points: %d"
                        ) % (val.department_id.name, net_points, val.bonus_points))

        if dept_list:
            raise ValidationError(_(
                "Bonus points cannot exceed the recommended points for the department.\n\n"
                "Department: %s\nRecommended Points: %s\nGiven Points: %d"
            ) % (', '.join(map(str, dept_list)), ', '.join(map(str, net_list)), ', '.join(map(int, bonus_list))))

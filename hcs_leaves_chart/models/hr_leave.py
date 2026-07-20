from datetime import datetime
from odoo import models, fields, api


class HrLeaveInherited(models.Model):
    _inherit = 'hr.leave'

    hr_leave_lines_id = fields.One2many('hr.leave.lines', 'hr_leaves_id', string='HR Leaves Lines',
                                        required=True, index=True, ondelete='cascade')

    @api.onchange('employee_id', '.holiday_status_id')
    @api.depends('employee_id', 'holiday_status_id')
    def CheckRemainingLeaves1(self):
        self.hr_leave_lines_id = [(5, 0, 0)]  # Clear existing lines
        if not self.employee_id:
            emp = self.env['hr.employee'].search([('user_id', '=', self.env.uid)])
        else:
            emp = self.employee_id
        if emp and self.holiday_status_id:
            records = self.env['hr.leave'].search([('employee_id', '=', emp.id)])

            vals = {}
            groupby_leave_type = {}
            groupby_leaveS_type = []
            ttl_available_leave_PL = 0
            ttl_available_leave_CL = 0
            ttl_available_leave_SL = 0
            ttl_available_leave_OV = 0
            ttl_available_leave = 0

            ttl_availed_leave_PL = 0
            ttl_availed_leave_CL = 0
            ttl_availed_leave_SL = 0
            ttl_availed_leave_OV = 0
            ttl_availed_leave = 0
            max_leaves = 0
            leaves_taken = 0
            # Convert the current date string to a datetime.date object
            current_date_str = datetime.now().strftime('%Y-%m-%d')
            current_date = datetime.strptime(current_date_str, '%Y-%m-%d').date()
            refused_leave_PL = 0.00
            refused_leave_CL = 0.00
            refused_leave_SL = 0.00
            refused_leave_OV = 0.00
            for rec in records:
                records_max_leaves = self.env['hr.leave.allocation'].search(
                    [('employee_id', '=', rec.employee_id.id),
                     ('holiday_status_id', '=', rec.holiday_status_id.id)])
                holiday_type_name = rec.holiday_status_id.display_name
                code = rec.holiday_status_id.code

                # leave_type = rec.holiday_status_id.with_context(employee_id=rec.employee_id.id)
                # rec.max_leaves = leave_type.max_leaves
                # rec.leaves_taken = leave_type.leaves_taken

                if code not in groupby_leave_type:
                    groupby_leave_type[code] = holiday_type_name
                    groupby_leaveS_type.append(code)

                if code == 'PL' and (rec.state == 'validate' or rec.state == 'refuse' or rec.state == 'confirm'):
                    if rec.holiday_status_id.validity_start:
                        if rec.holiday_status_id.validity_start <= current_date and rec.holiday_status_id.validity_stop >= current_date:
                            ttl_available_leave_PL = records_max_leaves[0].max_leaves
                            ttl_availed_leave_PL += rec.number_of_days
                            vals.update({
                                code: [{
                                    'code': code,
                                    'available': ttl_available_leave_PL,
                                    'availed': ttl_availed_leave_PL
                                }]
                            })
                    else:
                        if not records_max_leaves:
                            ttl_available_leave_PL += rec.number_of_days
                            ttl_availed_leave_PL = 0.0
                            vals.update({
                                code: [{
                                    'code': code,
                                    'available': ttl_available_leave_PL,
                                    'availed': ttl_availed_leave_PL
                                }]
                            })
                        else:
                            # if rec.state == 'refuse':
                            #     if not refused_leave_PL:
                            #         refused_leave_PL += rec.number_of_days
                            ttl_available_leave_PL = records_max_leaves[0].max_leaves  # - refused_leave_PL
                            ttl_availed_leave_PL += rec.number_of_days  # if not rec.state == 'refuse' else 0.00
                            vals.update({
                                code: [{
                                    'code': code,
                                    'available': ttl_available_leave_PL,
                                    'availed': ttl_availed_leave_PL
                                }]
                            })
                elif (rec.holiday_status_id.name == 'CL (AESL) 2023' or code == 'CL') and (
                        rec.state == 'validate' or rec.state == 'refuse' or rec.state == 'confirm'):
                    if rec.holiday_status_id.validity_start:
                        if rec.holiday_status_id.validity_start <= current_date and rec.holiday_status_id.validity_stop >= current_date:
                            # if rec.state == 'refuse':
                            #     if not refused_leave_CL:
                            #         refused_leave_CL += rec.number_of_days
                            ttl_available_leave_CL = records_max_leaves[0].max_leaves  # - refused_leave_CL
                            ttl_availed_leave_CL += rec.number_of_days  # if not rec.state == 'refuse' else 0.00 #rec.leaves_taken
                            vals.update({
                                code: [{
                                    'code': code,
                                    'available': ttl_available_leave_CL,
                                    'availed': ttl_availed_leave_CL
                                }]
                            })
                    else:
                        if not records_max_leaves:
                            ttl_available_leave_CL = rec.number_of_days
                            ttl_availed_leave_CL += 0.00  # rec.leaves_taken
                            vals.update({
                                code: [{
                                    'code': code,
                                    'available': ttl_available_leave_CL,
                                    'availed': ttl_availed_leave_CL
                                }]
                            })
                        else:

                            ttl_available_leave_CL = records_max_leaves[0].max_leaves
                            ttl_availed_leave_CL += rec.number_of_days  # rec.leaves_taken
                            vals.update({
                                code: [{
                                    'code': code,
                                    'available': ttl_available_leave_CL,
                                    'availed': ttl_availed_leave_CL
                                }]
                            })


                elif (rec.holiday_status_id.name == 'SL (AESL) 2023' or code == 'SL') and (
                        rec.state == 'validate' or rec.state == 'refuse' or rec.state == 'confirm'):
                    if rec.holiday_status_id.validity_start:
                        if rec.holiday_status_id.validity_start <= current_date and rec.holiday_status_id.validity_stop >= current_date:
                            # if rec.state == 'refuse':
                            #     if not refused_leave_SL:
                            #         refused_leave_SL += rec.number_of_days
                            ttl_available_leave_SL = records_max_leaves[0].max_leaves  # - refused_leave_SL
                            ttl_availed_leave_SL += rec.number_of_days  # if not rec.state == 'refuse' else 0.00 #rec.leaves_taken
                            vals.update({
                                code: [{
                                    'code': code,
                                    'available': ttl_available_leave_SL,
                                    'availed': ttl_availed_leave_SL
                                }]
                            })
                    else:
                        if not records_max_leaves:
                            ttl_available_leave_SL += rec.number_of_days
                            ttl_availed_leave_SL = 0.00  # rec.leaves_taken
                            vals.update({
                                code: [{
                                    'code': code,
                                    'available': ttl_available_leave_SL,
                                    'availed': ttl_availed_leave_SL
                                }]
                            })
                        else:

                            ttl_available_leave_SL = records_max_leaves[0].max_leaves
                            ttl_availed_leave_SL += rec.number_of_days  # rec.leaves_taken
                            vals.update({
                                code: [{
                                    'code': code,
                                    'available': ttl_available_leave_SL,
                                    'availed': ttl_availed_leave_SL
                                }]
                            })


                elif (rec.holiday_status_id.name == 'Official Visit (AESL)' or code == 'Official Visit') and (
                        rec.state == 'validate' or rec.state == 'refuse' or rec.state == 'confirm'):
                    if rec.holiday_status_id.validity_start:
                        if rec.holiday_status_id.validity_start <= current_date and rec.holiday_status_id.validity_stop >= current_date:
                            ttl_available_leave_OV = records_max_leaves[0].max_leaves
                            ttl_availed_leave_OV += rec.number_of_days  # rec.leaves_taken
                            vals.update({
                                code: [{
                                    'code': code,
                                    # 'available':ttl_available_leave_OV,
                                    'available': 0.00,
                                    'availed': ttl_availed_leave_OV
                                    # 'availed':ttl_available_leave_OV
                                }]
                            })
                    else:
                        if not records_max_leaves:
                            ttl_available_leave_OV = 0.00
                            ttl_availed_leave_OV += rec.number_of_days
                            vals.update({
                                code: [{
                                    'code': code,
                                    # 'available': ttl_available_leave_OV,
                                    'available': 0.00,
                                    'availed': ttl_availed_leave_OV
                                    # 'availed': ttl_available_leave_OV
                                }]
                            })
                        else:
                            # ttl_balance_leave_OV = records_max_leaves[0].max_leaves
                            ttl_available_leave_OV = records_max_leaves[0].number_of_hours_display
                            ttl_availed_leave_OV += rec.number_of_days  # rec.leaves_taken
                            vals.update({
                                code: [{
                                    'code': code,
                                    # 'available': ttl_available_leave_OV,
                                    'available': 0.00,
                                    'availed': ttl_availed_leave_OV
                                    # 'availed': ttl_available_leave_OV
                                }]
                            })

                else:
                    pass

            code_keys = vals.keys()
            # code_keys = ['PL','CL','SL','Official Visit']
            records_leaves_type = self.env['hr.leave.type'].search(
                [('validity_start', '<=', current_date), ('validity_stop', '>=', current_date)])
            for categ in groupby_leaveS_type:
                if categ in code_keys:
                    for i in vals.get(categ):
                        self.hr_leave_lines_id = [(0, 0, {
                            'leave_type': i['code'],
                            'balance_leave': float(i['available']) - float(i['availed']),
                            'availed_leave': i['availed'],
                            'available_leave': i['available']
                        })]

                        if i['code'] != 'PL':
                            for rec in records_leaves_type:
                                if rec.code == 'PL':
                                    if not ttl_available_leave_PL:
                                        ttl_available_leave_PL = rec.leaves_quantity
                                        self.hr_leave_lines_id = [(0, 0, {
                                            'leave_type': 'CL',
                                            'balance_leave': ttl_available_leave_PL,
                                            'availed_leave': 0.00,
                                            'available_leave': ttl_available_leave_PL
                                        })]

                        if i['code'] != 'CL':
                            for rec in records_leaves_type:
                                if rec.code == 'CL':
                                    if not ttl_available_leave_CL:
                                        ttl_available_leave_CL = rec.leaves_quantity
                                        self.hr_leave_lines_id = [(0, 0, {
                                            'leave_type': 'CL',
                                            'balance_leave': ttl_available_leave_CL,
                                            'availed_leave': 0.00,
                                            'available_leave': ttl_available_leave_CL
                                        })]

                        if i['code'] != 'SL':
                            for rec in records_leaves_type:
                                if rec.code == 'SL':
                                    if not ttl_available_leave_SL:
                                        ttl_available_leave_SL = rec.leaves_quantity
                                        self.hr_leave_lines_id = [(0, 0, {
                                            'leave_type': 'SL',
                                            'balance_leave': ttl_available_leave_SL,
                                            'availed_leave': 0.00,
                                            'available_leave': ttl_available_leave_SL
                                        })]

                        if i['code'] != 'Official Visit':
                            for rec in records_leaves_type:
                                if rec.code == 'Official Visit':
                                    if not ttl_availed_leave_OV:
                                        ttl_availed_leave_OV = rec.leaves_quantity
                                        self.hr_leave_lines_id = [(0, 0, {
                                            'leave_type': 'Official Visit',
                                            'balance_leave': ttl_availed_leave_OV,
                                            'availed_leave': ttl_availed_leave_OV,
                                            'available_leave': 0.00
                                        })]

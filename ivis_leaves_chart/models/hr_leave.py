from odoo import api, models, fields


class HrLeaveInherited(models.Model):
    _inherit = 'hr.leave'

    hr_leave_lines_id = fields.One2many(
        'hr.leave.lines',
        'hr_leaves_id',
        string='HR Leaves Lines',
        required=True,
        index=True
    )
    
    @api.onchange('employee_id', 'request_date_from', 'request_date_to')
    def PopulateLeaveLines(self):
        self.hr_leave_lines_id = [(5, 0, 0)]

        if not self.employee_id or not self.request_date_from or not self.request_date_to:
            return

        leave_types = self.env['hr.leave.type'].search([])
        fiscal_start = self.employee_id.contract_id.get_fiscal_date_start(self.request_date_from)
        fiscal_end = self.employee_id.contract_id.get_fiscal_date_end(self.request_date_from)

        leave_lines = []
        for leave_type in leave_types:
            is_pl_aesl = (leave_type.name == "PL (AESL)")
            availed_domain = [
                ('employee_id', '=', self.employee_id.id),
                ('holiday_status_id', '=', leave_type.id),
                ('state', '=', 'validate'),
                ('id', '!=', self.id),
            ]
            if not is_pl_aesl:
                availed_domain += [
                    ('request_date_from', '>=', fiscal_start),
                    ('request_date_to', '<=', fiscal_end),
                ]

            availed = self.env['hr.leave'].search(availed_domain)
            availed_leave = sum(availed.mapped('number_of_days')) or 0.0

            if leave_type.requires_allocation == 'yes':
                alloc_domain = [
                    ('employee_id', '=', self.employee_id.id),
                    ('holiday_status_id', '=', leave_type.id),
                    ('state', '=', 'validate'),
                ]
                if not is_pl_aesl:
                    alloc_domain += [
                        ('date_from', '<=', fiscal_end),
                        ('date_to', '>=', fiscal_start),
                    ]
                allocated = self.env['hr.leave.allocation'].search(alloc_domain)
                available_leave = sum(allocated.mapped('number_of_days_display')) or 0.0
                balance_leave = available_leave - availed_leave
            else:
                available_leave = 0.0
                balance_leave = 0.0

            leave_lines.append((0, 0, {
                'leave_type': leave_type.name,
                'available_leave': available_leave,
                'availed_leave': availed_leave,
                'balance_leave': balance_leave,
            }))

        self.hr_leave_lines_id = leave_lines

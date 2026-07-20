from odoo import fields, models


class LeaveReport(models.TransientModel):
    _name = 'leave.report'
    _description = 'Leave Report'

    employee_id = fields.Many2one('hr.employee', string='Employee')
    leave_type_id = fields.Many2one('hr.leave.type', string='Leave Type')
    total = fields.Float(string='Total')
    used = fields.Float(string='Used')
    remaining = fields.Float(string='Remaining')

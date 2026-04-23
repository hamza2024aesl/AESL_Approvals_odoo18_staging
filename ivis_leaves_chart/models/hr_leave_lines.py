from odoo import models, fields


class HrLeaveLines(models.Model):
    _name = 'hr.leave.lines'
    _description = 'HR Leave Lines'

    hr_leaves_id = fields.Many2one('hr.leave', string='Leave', ondelete='cascade', required=True)
    # holiday_status_id = fields.Many2one("hr.leave.type")
    leave_type = fields.Char(string="Leave Type", store=True)
    available_leave = fields.Float(string="Entitled", store=True)
    availed_leave = fields.Float(string="Availed", store=True)
    balance_leave = fields.Float(string="Balance", store=True)

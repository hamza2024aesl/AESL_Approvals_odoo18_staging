from odoo import fields, models


class HrLeaveTypeInherit(models.Model):
    _inherit = 'hr.leave.type'

    isunpaid = fields.Boolean('Unpaid?')

from odoo import models, fields, _
from odoo.exceptions import ValidationError

class HrLeaveInherit(models.Model):
    _inherit = "hr.leave"

    refuse_reason = fields.Text(string="Refuse Reason")

    def action_refuse(self):
        for leave in self:
            if not leave.refuse_reason:
                raise ValidationError(_("Please provide a reason for refusing this leave."))

        res = super(HrLeaveInherit, self).action_refuse()
        return res
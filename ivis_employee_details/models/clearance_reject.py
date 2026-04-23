from odoo import models, fields


class ClearanceReject(models.TransientModel):
    _name = 'clearance.reject'
    _description = "Clearance Reason"

    clearance_reject_reason = fields.Char(string='Comments')

    def reject_clearance(self):
        rec = self.env['employee.clearance'].search([('id', '=', self._context['active_id'])])
        rec.state = 'draft'
        rec.note = self.clearance_reject_reason

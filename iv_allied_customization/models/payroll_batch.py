from odoo import models, _
from odoo.exceptions import UserError


class PayrollBatchInherit(models.Model):
    _inherit = 'hr.payslip.run'

    def unlink(self):
        if any(self.filtered(lambda payslip_run: payslip_run.state not in ('draft', 'verify'))):
            raise UserError(_('You cannot delete a payslip batch which is not draft or verify!'))
        if any(self.mapped('slip_ids').filtered(lambda payslip: payslip.state not in ('draft', 'verify', 'cancel'))):
            raise UserError(_('You cannot delete a payslip which is not draft or cancelled!'))

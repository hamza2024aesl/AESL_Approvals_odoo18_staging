from odoo import models, _
from odoo.exceptions import UserError


class PayrollBatchInherit(models.Model):
    _inherit = 'hr.payslip.run'

    def unlink(self):
        if any(self.filtered(lambda payslip_run: payslip_run.state not in ('draft', 'verify'))):
            raise UserError(_('You cannot delete a payslip batch which is not draft or verify!'))
        if any(self.mapped('slip_ids').filtered(lambda payslip: payslip.state not in ('draft', 'verify', 'cancel'))):
            raise UserError(_('You cannot delete a payslip which is not draft or cancelled!'))
        if self.state != 'close':
            self.env.cr.execute("""UPDATE hr_payslip SET state='draft' WHERE id in %s""", (tuple(self.slip_ids.ids),))
            self.state = 'draft'
        return super(PayrollBatchInherit, self).unlink()

from odoo import fields, models


class HrSettlement(models.Model):
    _name = 'hr.settlement'
    _description = 'HR Settlement'

    name = fields.Char(required=True, readonly=True)
    slip_ids = fields.One2many('hr.payslip', 'payslip_run_id', string='Payslips', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('close', 'Close'),
    ], string='Status', index=True, readonly=True, copy=False, default='draft')
    # date_start = fields.Date(string='Date From', required=True, readonly=True,
    #                          states={'draft': [('readonly', False)]},
    #                          default=lambda self: fields.Date.to_string(date.today().replace(day=1)))
    # date_end = fields.Date(string='Date To', required=True, readonly=True,
    #                        states={'draft': [('readonly', False)]},
    #                        default=lambda self: fields.Date.to_string(
    #                            (datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()))
    credit_note = fields.Boolean(string='Credit Note', readonly=True,
                                 help="If its checked, indicates that all payslips generated from here are refund payslips.")

    def draft_payslip_run(self):
        return self.write({'state': 'draft'})

    def close_payslip_run(self):
        return self.write({'state': 'close'})
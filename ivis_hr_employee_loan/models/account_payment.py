from odoo import models, fields, _


class AccountPayment(models.Model):
    _inherit = 'account.payment'
    _description = 'account.payment'

    loan_id = fields.Many2one('employee.loan.details', string='Loan')
    employee_loan_account = fields.Many2one('account.account')
    pay_ref = fields.Char('Ref', store=True)

    def tick_loan_assign(self, employee_loan_account):
        self.loan_assign = True
        self.employee_loan_account = employee_loan_account.id

    def post(self):
        res = super(AccountPayment, self).post()
        # todo: check the if amount is less then installment amount then it could not be applicable to pay installment
        for payment in self:
            if payment.installment:
                payment.installment.write({'state': 'paid'})
        return res

    def _get_counterpart_move_line_vals(self, invoice=False):
        if self.payment_type == 'transfer':
            name = self.name
        else:
            name = ''
            if self.partner_type == 'customer':
                if self.payment_type == 'inbound':
                    name += _("Customer Payment")
                elif self.payment_type == 'outbound':
                    name += _("Customer Refund")
            elif self.partner_type == 'supplier':
                if self.payment_type == 'inbound':
                    name += _("Vendor Refund")
                elif self.payment_type == 'outbound':
                    name += _("Vendor Payment")
            if invoice:
                name += ': '
                for inv in invoice:
                    if inv.move_id:
                        name += inv.number + ', '
                name = name[:len(name) - 2]

        if self.loan_assign and not self.employee_loan_account:
            account = self.partner_id.property_account_receivable_id.id
        elif self.loan_assign and self.employee_loan_account:
            account = self.employee_loan_account.id
        else:
            account = self.destination_account_id.id
        return {
            'name': name,
            'account_id': account,
            'journal_id': self.journal_id.id,
            'currency_id': self.currency_id != self.company_id.currency_id and self.currency_id.id or False,
            'payment_id': self.id,
        }

    installment = fields.Many2one(
        'loan.installment.details',
        string='Loan Installment',
        readonly=False,
        copy=False,
    )

    loan_assign = fields.Boolean('Loan Assign')
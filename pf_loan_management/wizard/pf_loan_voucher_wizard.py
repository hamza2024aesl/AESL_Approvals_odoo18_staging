# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class PFLoanVoucherWizard(models.TransientModel):
    _name = 'pf.loan.voucher.wizard'
    _description = 'Create GP Voucher Wizard'

    loan_id = fields.Many2one('pf.loan.application', string='PF Loan Application', required=True, readonly=True)
    employee_id = fields.Many2one('hr.employee', related='loan_id.employee_id', string='Employee', readonly=True)
    loan_amount = fields.Float(related='loan_id.loan_amount', string='Amount (Rs.)', readonly=True)
    loan_amount_words = fields.Char(related='loan_id.loan_amount_words', string='Amount in Words', readonly=True)

    audit_trail_code = fields.Char(string='Audit Trail Code', required=True)
    voucher_date = fields.Date(string='Date', default=fields.Date.context_today, required=True)
    journal_entry_no = fields.Char(string='Journal Entry No.', required=True)
    posting_date = fields.Date(string='Posting Date', default=fields.Date.context_today, required=True)
    check_book_id = fields.Char(string='Check Book ID', required=True)
    cheque_number = fields.Char(string='Cheque Number', required=True)
    paid_to_rcvd_from = fields.Char(string='Paid To / Received From', required=True)
    description = fields.Char(string='Description', required=True)

    @api.model
    def default_get(self, fields_list):
        res = super(PFLoanVoucherWizard, self).default_get(fields_list)
        active_id = self.env.context.get('active_id')
        if active_id:
            loan = self.env['pf.loan.application'].browse(active_id)
            res['loan_id'] = loan.id
            res['paid_to_rcvd_from'] = f"{loan.employee_id.name} CHQ#" if loan.employee_id else ""
            res['description'] = f"{loan.employee_id.name} PF LOAN {loan.employee_reg_no or ''}"
            if loan.gp_audit_trail_code:
                res['audit_trail_code'] = loan.gp_audit_trail_code
            if loan.gp_date:
                res['voucher_date'] = loan.gp_date
            if loan.gp_journal_entry_no:
                res['journal_entry_no'] = loan.gp_journal_entry_no
            if loan.gp_posting_date:
                res['posting_date'] = loan.gp_posting_date
            if loan.gp_check_book_id:
                res['check_book_id'] = loan.gp_check_book_id
            if loan.gp_cheque_number:
                res['cheque_number'] = loan.gp_cheque_number
            if loan.gp_paid_to_rcvd_from:
                res['paid_to_rcvd_from'] = loan.gp_paid_to_rcvd_from
            if loan.gp_description:
                res['description'] = loan.gp_description
        return res

    def action_save_voucher_and_approve(self):
        self.ensure_one()
        loan = self.loan_id
        if not loan:
            raise UserError(_("No active loan application found."))

        loan.write({
            'is_voucher_created': True,
            'gp_audit_trail_code': self.audit_trail_code,
            'gp_date': self.voucher_date,
            'gp_journal_entry_no': self.journal_entry_no,
            'gp_posting_date': self.posting_date,
            'gp_check_book_id': self.check_book_id,
            'gp_cheque_number': self.cheque_number,
            'gp_paid_to_rcvd_from': self.paid_to_rcvd_from,
            'gp_description': self.description,
        })

        # Forward to Trustee
        loan.action_approve_finance()
        return {'type': 'ir.actions.act_window_close'}

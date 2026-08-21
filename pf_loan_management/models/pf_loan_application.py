# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class PFLoanApplication(models.Model):
    _name = 'pf.loan.application'
    _description = 'Provident Fund Loan Application'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc, id desc'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, default=lambda self: self.env.user.employee_id)
    employee_reg_no = fields.Char(related='employee_id.identification_id', string='Employee No.', readonly=True)
    department_id = fields.Many2one('hr.department', related='employee_id.department_id', string='Department', readonly=True)
    job_id = fields.Many2one('hr.job', related='employee_id.job_id', string='Designation', readonly=True)
    
    application_date = fields.Date(string='Application Date', default=fields.Date.context_today, required=True)
    loan_amount = fields.Float(string='Loan Amount (Rs.)', required=True, tracking=True)
    loan_amount_words = fields.Char(string='Amount in Words')
    installments_count = fields.Integer(string='Installments Count', default=1, required=True)
    is_interest_free = fields.Boolean(string='Type of PF Interest Free', default=True)
    loan_purpose = fields.Text(string='Loan Purpose', required=True)
    remarks = fields.Text(string='Remarks / Approval Notes', tracking=True)

    # For Accounts Use Only Fields
    gross_salary = fields.Float(string='Gross Salary')
    less_pf = fields.Float(string='Less P.F.')
    income_tax = fields.Float(string='I. Tax')
    other_deductions = fields.Float(string='Other Deductions')
    net_pay = fields.Float(string='Net Pay Rs.')

    max_ded_allowed = fields.Float(string='Maximum Ded. Allowed')
    loan_outstanding = fields.Float(string='Loan Outstanding')
    loan_required = fields.Float(string='Loan Required')
    total_loan_calc = fields.Float(string='Total Rs.')
    pf_balance_dues = fields.Float(string='DUES: Provident Fund Balance')

    # Sanction Statement Fields
    sanctioned_amount = fields.Float(string='Loan Recommended / Sanctioned Amount', compute='_compute_sanctioned_loan_details', store=True, readonly=False)
    total_sanctioned_loan = fields.Float(string='Total Sanctioned Loan', compute='_compute_sanctioned_loan_details', store=True, readonly=False)
    repay_installments = fields.Integer(string='Repay Installments', default=1, tracking=True)
    per_installment_amount = fields.Float(string='Per Installment Amount', compute='_compute_sanctioned_loan_details', store=True, readonly=False)

    @api.depends('employee_id', 'loan_amount', 'repay_installments')
    def _compute_sanctioned_loan_details(self):
        for rec in self:
            rec.sanctioned_amount = rec.loan_amount or 0.0

            prev_total = 0.0
            if rec.employee_id:
                applicant = rec.employee_id
                loan_records = applicant.loan_ids.filtered(lambda l: l.state != 'cancel') if hasattr(applicant, 'loan_ids') and applicant.loan_ids else []
                if not loan_records and "hr.loan" in self.env:
                    loan_records = self.env["hr.loan"].sudo().search([
                        ('employee_id', '=', applicant.id),
                        ('state', '!=', 'cancel'),
                    ], order='id desc')

                if loan_records:
                    latest = loan_records[0]  # Option 1: Latest active loan Total Loan
                    prev_total = latest.final_total or getattr(latest, 'total_loan', 0.0) or getattr(latest, 'loan_amount', 0.0) or getattr(latest, 'principal_amount', 0.0)

            rec.total_sanctioned_loan = prev_total + rec.sanctioned_amount
            inst_cnt = rec.repay_installments if rec.repay_installments and rec.repay_installments > 0 else 1
            rec.per_installment_amount = round(rec.total_sanctioned_loan / float(inst_cnt), 2)

    previous_loan_notice_html = fields.Html(string="Previous Loan Notice", compute="_compute_previous_loan_notice_html")

    @api.depends('employee_id', 'state')
    def _compute_previous_loan_notice_html(self):
        for rec in self:
            # Strictly show ONLY during 'draft' (Waiting HR Approval) step
            if rec.state == 'draft' and rec.employee_id:
                applicant = rec.employee_id
                t_amt = 0.0
                p_amt = 0.0
                d_amt = 0.0

                loan_records = applicant.loan_ids.filtered(lambda l: l.state != 'cancel') if hasattr(applicant, 'loan_ids') and applicant.loan_ids else []
                if not loan_records and "hr.loan" in self.env:
                    loan_records = self.env["hr.loan"].sudo().search([
                        ('employee_id', '=', applicant.id),
                        ('state', '!=', 'cancel'),
                    ], order='id desc')

                if loan_records:
                    latest = loan_records[0]
                    t_amt = latest.final_total or getattr(latest, 'total_loan', 0.0) or getattr(latest, 'loan_amount', 0.0) or getattr(latest, 'principal_amount', 0.0)
                    p_amt = latest.total_amount_paid or getattr(latest, 'total_paid', 0.0)
                    d_amt = latest.total_amount_due or getattr(latest, 'balance_on_loan', 0.0) or getattr(latest, 'balance_amount', 0.0)
                    if not d_amt and t_amt:
                        d_amt = t_amt - p_amt if t_amt > p_amt else t_amt

                if t_amt > 0.0:
                    rec.previous_loan_notice_html = f"""
                    <div style="background-color: #e0f2fe; border-left: 5px solid #0284c7; padding: 12px 16px; border-radius: 6px; margin-bottom: 15px;">
                        <div style="font-weight: bold; color: #0369a1; font-size: 14px; margin-bottom: 6px;">
                            <i class="fa fa-info-circle"></i> HR Review Notice: Previous Active Loan Balance ({applicant.name})
                        </div>
                        <div style="display: flex; justify-content: space-between; font-size: 13px; color: #334155;">
                            <span><strong>Total Loan:</strong> Rs. {t_amt:,.2f}</span>
                            <span style="color: #15803d;"><strong>Received From Employee:</strong> Rs. {p_amt:,.2f}</span>
                            <span style="color: #0369a1;"><strong>Balance on Loan:</strong> Rs. {d_amt:,.2f}</span>
                        </div>
                    </div>
                    """
                else:
                    rec.previous_loan_notice_html = False
            else:
                rec.previous_loan_notice_html = False

    # GP Voucher Details (Created by Finance Officer)
    is_voucher_created = fields.Boolean(string='Voucher Created', default=False, tracking=True)
    gp_audit_trail_code = fields.Char(string='Audit Trail Code', tracking=True)
    gp_date = fields.Date(string='Voucher Date', tracking=True)
    gp_journal_entry_no = fields.Char(string='Journal Entry No.', tracking=True)
    gp_posting_date = fields.Date(string='Posting Date', tracking=True)
    gp_check_book_id = fields.Char(string='Check Book ID', tracking=True)
    gp_cheque_number = fields.Char(string='Cheque Number', tracking=True)
    gp_paid_to_rcvd_from = fields.Char(string='Paid To / Received From', tracking=True)
    gp_description = fields.Char(string='Description', tracking=True)

    state = fields.Selection([
        ('draft', 'Waiting HR Approval'),
        ('returned', 'Returned to Employee'),
        ('waiting_hod', 'Waiting HOD Approval'),
        ('waiting_finance', 'Waiting Finance Approval'),
        ('waiting_trustee', 'Waiting Trustee Approval'),
        ('approved', 'Fully Approved'),
        ('rejected', 'Rejected'),
        ('cancel', 'Cancelled'),
    ], string='Status', default='draft', tracking=True, index=True)

    # Approvers (snapshot from config)
    hr_approver_id = fields.Many2one('hr.employee', string='1st Approver (HR)', readonly=True)
    hod_approver_id = fields.Many2one('hr.employee', string='2nd Approver (HOD)', readonly=True)
    finance_approver_id = fields.Many2one('hr.employee', string='3rd Approver (Finance)', readonly=True)
    trustee_approver_id = fields.Many2one('hr.employee', string='4th Approver (Trustee)', readonly=True)

    @api.onchange('net_pay')
    def _onchange_net_pay(self):
        if self.net_pay:
            self.max_ded_allowed = round(self.net_pay / 3.0, 2)

    @api.model
    def create(self, vals):
        if vals.get('employee_id'):
            existing_active = self.search([
                ('employee_id', '=', vals['employee_id']),
                ('state', 'in', ['draft', 'returned', 'waiting_hod', 'waiting_finance', 'waiting_trustee']),
            ], limit=1)
            if existing_active:
                raise UserError(_(
                    "You already have an active/pending Provident Fund Loan Application (Ref: %s). "
                    "You cannot submit a new loan request while an existing application is active."
                ) % existing_active.name)

        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('pf.loan.application') or _('New')
        
        if vals.get('net_pay') and not vals.get('max_ded_allowed'):
            vals['max_ded_allowed'] = round(float(vals['net_pay']) / 3.0, 2)

        config = self.env['pf.loan.config'].sudo().get_config()
        if config:
            vals['hr_approver_id'] = config.hr_id.id if config.hr_id else False
            vals['hod_approver_id'] = config.hod_id.id if config.hod_id else False
            vals['finance_approver_id'] = config.finance_id.id if config.finance_id else False
            vals['trustee_approver_id'] = config.trustee_id.id if config.trustee_id else False

        res = super(PFLoanApplication, self).create(vals)
        res._send_approver_email()
        return res

    def _send_approver_email(self):
        """Send email notification strictly and exclusively to the configured approver for current state."""
        for rec in self:
            recipient_emp = False
            step_name = ""

            if rec.state == 'draft':
                recipient_emp = rec.hr_approver_id
                step_name = "1st Step: HR Approval"
            elif rec.state == 'waiting_hod':
                recipient_emp = rec.hod_approver_id
                step_name = "2nd Step: Head of Department (HOD) Approval"
            elif rec.state == 'waiting_finance':
                recipient_emp = rec.finance_approver_id
                step_name = "3rd Step: Finance Officer Approval"
            elif rec.state == 'waiting_trustee':
                recipient_emp = rec.trustee_approver_id
                step_name = "4th Step: Trustee Approval"

            if recipient_emp and recipient_emp.work_email:
                subject = f"PF Loan Approval Needed ({step_name}): {rec.name}"
                body = f"""
                <div style="font-family: Arial, sans-serif; font-size: 14px;">
                    <h2 style="color: #8D0000;">PF Loan Application Pending Approval</h2>
                    <p>Dear {recipient_emp.name},</p>
                    <p>A new Provident Fund Loan Application (Ref: <strong>{rec.name}</strong>) submitted by <strong>{rec.employee_id.name}</strong> is awaiting your approval at: <strong>{step_name}</strong>.</p>
                    <table style="width: 100%; border-collapse: collapse; margin-top: 15px; margin-bottom: 15px;">
                        <tr><td style="padding: 5px; font-weight: bold; width: 30%;">Employee:</td><td style="padding: 5px;">{rec.employee_id.name} ({rec.employee_reg_no})</td></tr>
                        <tr><td style="padding: 5px; font-weight: bold;">Requested Loan Amount:</td><td style="padding: 5px;">Rs. {rec.loan_amount:,.2f}</td></tr>
                        <tr><td style="padding: 5px; font-weight: bold;">Loan Purpose:</td><td style="padding: 5px;">{rec.loan_purpose or 'N/A'}</td></tr>
                        <tr><td style="padding: 5px; font-weight: bold;">Application Date:</td><td style="padding: 5px;">{rec.application_date}</td></tr>
                    </table>
                    <p>Please log in to the system to review and process this application.</p>
                    <p>Best Regards,<br/>AESL PF Loan System</p>
                </div>
                """
                mail_values = {
                    'subject': subject,
                    'body_html': body,
                    'email_to': recipient_emp.work_email,
                    'email_from': rec.env.company.email or rec.env.user.email_formatted,
                    'state': 'outgoing',
                }
                rec.env['mail.mail'].sudo().create(mail_values).send()

    def action_approve_hr(self):
        for rec in self:
            if rec.state == 'draft':
                requester_dept = rec.employee_id.department_id if rec.employee_id else False
                hod_emp = rec.hod_approver_id
                hod_dept = hod_emp.department_id if hod_emp else False

                if not requester_dept or not hod_dept or requester_dept != hod_dept:
                    req_dept_name = requester_dept.name if requester_dept else _("No Department")
                    hod_dept_name = hod_dept.name if hod_dept else _("No Department")
                    hod_name = hod_emp.name if hod_emp else _("Configured HOD")
                    raise UserError(_(
                        "Approval Blocked! Requester's Department (%s) does not match the configured HOD's Department (%s for HOD %s). "
                        "Please ensure the HOD in Configuration belongs to the same department as the requester before approving."
                    ) % (req_dept_name, hod_dept_name, hod_name))

                rec.state = 'waiting_hod'
                rec._send_approver_email()

    def action_approve_hod(self):
        for rec in self:
            if rec.state == 'waiting_hod':
                rec.state = 'waiting_finance'
                rec._send_approver_email()

    def action_approve_finance(self):
        for rec in self:
            if rec.state == 'waiting_finance':
                rec.state = 'waiting_trustee'
                rec._send_approver_email()

    def action_open_voucher_wizard(self):
        self.ensure_one()
        return {
            'name': _('Create GP Voucher'),
            'type': 'ir.actions.act_window',
            'res_model': 'pf.loan.voucher.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_id': self.id,
            }
        }

    def action_approve_trustee(self):
        for rec in self:
            if rec.state == 'waiting_trustee':
                rec.state = 'approved'

    def action_reject(self):
        for rec in self:
            current_stage = 'hr'
            if rec.state == 'waiting_hod':
                current_stage = 'hod'
            elif rec.state == 'waiting_finance':
                current_stage = 'finance'
            elif rec.state == 'waiting_trustee':
                current_stage = 'trustee'

            rec.state = 'rejected'
            rec._send_rejection_email(current_stage)

    def _send_rejection_email(self, rejected_by_stage):
        for rec in self:
            recipients = []
            if rejected_by_stage in ['hr', 'hod', 'finance']:
                if rec.employee_id.work_email:
                    recipients.append(rec.employee_id.work_email)
            elif rejected_by_stage == 'trustee':
                for emp in [rec.employee_id, rec.hr_approver_id, rec.hod_approver_id, rec.finance_approver_id]:
                    if emp and emp.work_email and emp.work_email not in recipients:
                        recipients.append(emp.work_email)

            if recipients:
                subject = f"PF Loan Application REJECTED: {rec.name}"
                body = f"""
                <div style="font-family: Arial, sans-serif; font-size: 14px;">
                    <h2 style="color: #d9534f;">Provident Fund Loan Application Rejected</h2>
                    <p>The PF Loan Application (Ref: <strong>{rec.name}</strong>) submitted by <strong>{rec.employee_id.name}</strong> has been <strong>REJECTED</strong>.</p>
                    <p><strong>Remarks / Reason:</strong> {rec.remarks or 'N/A'}</p>
                </div>
                """
                mail_values = {
                    'subject': subject,
                    'body_html': body,
                    'email_to': ','.join(recipients),
                    'email_from': rec.env.company.email or rec.env.user.email_formatted,
                    'state': 'outgoing',
                }
                rec.env['mail.mail'].sudo().create(mail_values).send()

    def action_return(self):
        """Cascading reverse step-back flow for Return action."""
        for rec in self:
            if rec.state == 'draft':
                rec.state = 'returned'
                rec._send_return_email(rec.employee_id, "Returned to Employee")
            elif rec.state == 'waiting_hod':
                rec.state = 'draft'
                rec._send_return_email(rec.hr_approver_id, "Returned to HR")
            elif rec.state == 'waiting_finance':
                rec.state = 'waiting_hod'
                rec._send_return_email(rec.hod_approver_id, "Returned to HOD")
            elif rec.state == 'waiting_trustee':
                rec.state = 'waiting_finance'
                rec._send_return_email(rec.finance_approver_id, "Returned to Finance Officer")

    def _send_return_email(self, recipient_emp, stage_label):
        for rec in self:
            if recipient_emp and recipient_emp.work_email:
                subject = f"PF Loan Application RETURNED ({stage_label}): {rec.name}"
                body = f"""
                <div style="font-family: Arial, sans-serif; font-size: 14px;">
                    <h2 style="color: #f0ad4e;">Provident Fund Loan Application Returned</h2>
                    <p>Dear {recipient_emp.name},</p>
                    <p>The PF Loan Application (Ref: <strong>{rec.name}</strong>) submitted by <strong>{rec.employee_id.name}</strong> has been <strong>RETURNED</strong> ({stage_label}).</p>
                    <p><strong>Remarks / Instructions:</strong> {rec.remarks or 'N/A'}</p>
                    <p>Please log in to review and process the application.</p>
                </div>
                """
                mail_values = {
                    'subject': subject,
                    'body_html': body,
                    'email_to': recipient_emp.work_email,
                    'email_from': rec.env.company.email or rec.env.user.email_formatted,
                    'state': 'outgoing',
                }
                rec.env['mail.mail'].sudo().create(mail_values).send()

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancel'

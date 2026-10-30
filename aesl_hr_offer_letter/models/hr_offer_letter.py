# -*- coding: utf-8 -*-

import uuid
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class HrOfferLetter(models.Model):
    _name = 'hr.offer.letter'
    _description = 'AESL Employment Offer Letter'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    def _default_notify_users(self):
        manager_group = self.env.ref('hr.group_hr_manager', raise_if_not_found=False)
        if manager_group and manager_group.users:
            return manager_group.users
        return self.env.user

    # Core Identifiers & State
    name = fields.Char(
        string='Offer Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
        tracking=True
    )
    revision = fields.Integer(
        string='Revision',
        default=0,
        readonly=True,
        tracking=True
    )
    date = fields.Date(
        string='Offer Date',
        default=fields.Date.context_today,
        required=True,
        tracking=True
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Offer Sent'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('done', 'Employee Created'),
        ('cancel', 'Cancelled'),
    ], string='Status', default='draft', tracking=True, copy=False)

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        string='Currency',
        readonly=True
    )

    # Candidate Link (Recruitment Integration)
    applicant_id = fields.Many2one(
        'hr.applicant',
        string='Accepted Applicant / Candidate',
        tracking=True,
        help="Select the candidate who has been selected for this position."
    )
    candidate_id = fields.Many2one(
        'hr.candidate',
        related='applicant_id.candidate_id',
        string='Candidate Record',
        store=True,
        readonly=True
    )

    # Candidate Personal Details (Image 1 - Application Form)
    candidate_name = fields.Char(string='Candidate Name', required=True, tracking=True)
    father_name = fields.Char(string="Father's Name", tracking=True)
    present_address = fields.Text(string='Present Address')
    cnic = fields.Char(string='CNIC No.', tracking=True, help="National Identity Card Number")
    religion = fields.Selection([
        ('Islam', 'Islam'),
        ('Christainity', 'Christainity'),
        ('Hinduism', 'Hinduism'),
        ('None', 'None'),
        ('Other', 'Other'),
    ], string='Religion', default='Islam')
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ], string='Sex / Gender', default='male')
    phone = fields.Char(string='Phone / Mobile No.', tracking=True)
    email = fields.Char(string='Candidate Email', required=True, tracking=True)
    date_of_birth = fields.Date(string='Date of Birth')
    place_of_birth = fields.Char(string='Place of Birth')
    marital_status = fields.Selection([
        ('single', 'Single'),
        ('married', 'Married'),
        ('cohabitant', 'Legal Cohabitant'),
        ('widower', 'Widower'),
        ('divorced', 'Divorced'),
    ], string='Marital Status', default='single')
    no_of_dependents = fields.Integer(string='No of Dependents', default=0)
    last_salary = fields.Float(string='Last Drawn Salary')
    earliest_joining_date = fields.Date(string='Candidate Availability Date')

    # Employment Details (Image 2)
    job_id = fields.Many2one('hr.job', string='Designation', required=True, tracking=True)
    department_id = fields.Many2one('hr.department', string='Department', required=True, tracking=True)
    joining_date = fields.Date(string='Joining Date', required=True, tracking=True)
    probation_period = fields.Char(string='Probation Period', default='3 Months')
    posting_location = fields.Char(string='Place of Posting', default='Head Office', help="e.g. Multan, Karachi, Lahore")

    # Salary Structure (Image 2 - Breakdown)
    basic_salary = fields.Monetary(string='Basic Pay', currency_field='currency_id', tracking=True)
    house_rent = fields.Monetary(string='House Rent', currency_field='currency_id')
    conveyance_allowance = fields.Monetary(string='Conveyance Allowance', currency_field='currency_id')
    utilities_allowance = fields.Monetary(string='Utilities', currency_field='currency_id')
    other_allowance = fields.Monetary(string='Other Allowance', currency_field='currency_id')
    gross_salary = fields.Monetary(
        string='Gross Salary',
        currency_field='currency_id',
        compute='_compute_gross_salary',
        store=True,
        readonly=False,
        tracking=True
    )

    # Standard AESL Medical Terms & Benefits (Image 2)
    medical_outpatient = fields.Text(
        string='Out-Patient Treatment',
        default="You will be entitled to reimbursement of money actually spent on medical treatment for self, wife and dependent children subject to a maximum of one Gross salary per annum."
    )
    medical_hospitalisation = fields.Text(
        string='Group Hospitalisation Insurance',
        default="You will be entitled to reimbursement as per Company Rules in case of hospitalisation for self, wife and two dependent children."
    )
    additional_terms = fields.Html(string='Additional Terms & Conditions')

    # Authorized Signatory & Report Parameters
    hr_manager_id = fields.Many2one('res.users', string='HR Responsible', default=lambda self: self.env.user)
    signatory_name = fields.Char(string='Signatory Name', default='KHWAJA AHAD RAHMAN')
    signatory_title = fields.Char(string='Signatory Title', default='DIRECTOR')
    drafter_initials = fields.Char(string='Drafter Initials', default='HS')
    validity_days = fields.Integer(string='Offer Validity (Days)', default=45)

    # Security Token for Candidate Action without login
    access_token = fields.Char(string='Security Token', copy=False, readonly=True)
    response_date = fields.Datetime(string='Response Received At', readonly=True)
    rejection_reason = fields.Text(string='Rejection Reason / Feedback', readonly=True)

    # Onboarding Links & Notification Targets
    employee_id = fields.Many2one('hr.employee', string='Created Employee', readonly=True, copy=False)
    contract_id = fields.Many2one('hr.contract', string='Created Contract', readonly=True, copy=False)
    notify_user_ids = fields.Many2many(
        'res.users',
        'hr_offer_letter_notify_user_rel',
        'offer_id',
        'user_id',
        string='Notify Onboarding Users',
        default=_default_notify_users,
        help="These users will automatically receive an email alert as soon as the candidate is onboarded as an Employee."
    )

    # ---------------------------------------------------------
    # Computes & Onchanges
    # ---------------------------------------------------------
    @api.depends('basic_salary', 'house_rent', 'conveyance_allowance', 'utilities_allowance', 'other_allowance')
    def _compute_gross_salary(self):
        for rec in self:
            rec.gross_salary = (
                (rec.basic_salary or 0.0) +
                (rec.house_rent or 0.0) +
                (rec.conveyance_allowance or 0.0) +
                (rec.utilities_allowance or 0.0) +
                (rec.other_allowance or 0.0)
            )

    @api.onchange('applicant_id')
    def _onchange_applicant_id(self):
        """Auto-populate fields from the selected applicant / candidate."""
        if not self.applicant_id:
            return

        applicant = self.applicant_id
        candidate = applicant.candidate_id

        self.candidate_name = applicant.partner_name or (candidate and candidate.partner_name) or ''
        self.email = applicant.email_from or (candidate and candidate.email_from) or ''
        self.phone = applicant.partner_phone or (candidate and candidate.partner_phone) or ''
        if applicant.job_id:
            self.job_id = applicant.job_id
        if applicant.department_id:
            self.department_id = applicant.department_id
        if applicant.availability:
            self.earliest_joining_date = applicant.availability
            if not self.joining_date:
                self.joining_date = applicant.availability

        # Auto-fill salary if proposed in recruitment
        if applicant.salary_proposed:
            self.gross_salary = applicant.salary_proposed
            self.action_calculate_aesl_breakdown()
        elif applicant.salary_expected:
            self.gross_salary = applicant.salary_expected
            self.action_calculate_aesl_breakdown()

    def action_calculate_aesl_breakdown(self):
        """
        Auto-calculates standard AESL Pakistan salary structure:
        - Basic Pay: ~60.606%
        - House Rent: ~27.272%
        - Conveyance Allowance: ~6.061%
        - Utilities: ~6.061%
        Matches exact proportions shown on Image 2:
        Gross: 100,000 -> Basic: 60,606 | HR: 27,272 | Conv: 6,061 | Util: 6,061
        """
        for rec in self:
            if not rec.gross_salary:
                continue
            gross = rec.gross_salary
            basic = round(gross * 0.60606, 2)
            house = round(gross * 0.27272, 2)
            conv = round(gross * 0.06061, 2)
            # Adjust remainder to utilities so sum matches gross exactly
            util = round(gross - (basic + house + conv), 2)

            rec.basic_salary = basic
            rec.house_rent = house
            rec.conveyance_allowance = conv
            rec.utilities_allowance = util
            rec.other_allowance = 0.0

    # ---------------------------------------------------------
    # CRUD / Lifecycle
    # ---------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('hr.offer.letter') or _('New')
            if not vals.get('access_token'):
                vals['access_token'] = str(uuid.uuid4())
        return super().create(vals_list)

    def write(self, vals):
        # Prevent editing restricted fields once sent or accepted, unless revising
        restricted_states = ['sent', 'accepted', 'done']
        if any(rec.state in restricted_states for rec in self):
            allowed_fields = {
                'state', 'employee_id', 'contract_id', 'access_token',
                'response_date', 'rejection_reason', 'message_follower_ids',
                'activity_ids', 'message_ids', 'revision'
            }
            updating_restricted = set(vals.keys()) - allowed_fields
            if updating_restricted:
                for rec in self:
                    if rec.state in restricted_states:
                        raise UserError(_(
                            "You cannot modify the offer letter details while in '%s' status. "
                            "If the candidate rejected the offer, click 'Revise Offer' to make changes.",
                            dict(self._fields['state'].selection).get(rec.state)
                        ))
        return super().write(vals)

    # ---------------------------------------------------------
    # Helper URLs for Portal / Email
    # ---------------------------------------------------------
    def _ensure_token(self):
        for rec in self:
            if not rec.access_token:
                rec.access_token = str(uuid.uuid4())

    def get_accept_url(self):
        self.ensure_one()
        self._ensure_token()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return f"{base_url}/offer/respond/{self.access_token}?action=accept"

    def get_reject_url(self):
        self.ensure_one()
        self._ensure_token()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return f"{base_url}/offer/respond/{self.access_token}?action=reject"

    # ---------------------------------------------------------
    # Actions & Workflows
    # ---------------------------------------------------------
    def action_send_offer(self):
        """Generates PDF report, attaches it to email, and sends it to candidate with Accept/Reject buttons."""
        self.ensure_one()
        if not self.email:
            raise UserError(_("Candidate email address is required to send the offer letter."))
        if not self.gross_salary:
            raise UserError(_("Please define the salary package before sending the offer letter."))

        self._ensure_token()

        # 1. Generate PDF Report Attachment
        pdf_content, _report_type = self.env['ir.actions.report']._render_qweb_pdf('aesl_hr_offer_letter.action_report_hr_offer_letter', [self.id])

        filename = f"Offer_Letter_{self.candidate_name.replace(' ', '_')}_{self.name.replace('/', '_')}.pdf"
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'raw': pdf_content,
            'res_model': 'hr.offer.letter',
            'res_id': self.id,
            'mimetype': 'application/pdf',
        })

        # 2. Get and send Email Template
        mail_template = self.env.ref('aesl_hr_offer_letter.mail_template_candidate_offer_letter')
        email_values = {
            'attachment_ids': [(4, attachment.id)],
            'email_to': self.email,
        }
        mail_template.send_mail(self.id, email_values=email_values, force_send=True)

        self.state = 'sent'
        self.message_post(
            body=_(
                "<strong>Employment Offer Letter Sent:</strong><br/>"
                "- Recipient: %s (%s)<br/>"
                "- Gross Salary: %s %s<br/>"
                "- Joining Date: %s<br/>"
                "- Attachment: %s"
            ) % (
                self.candidate_name, self.email,
                self.currency_id.symbol or '', "{:,.2f}".format(self.gross_salary),
                self.joining_date, filename
            ),
            attachment_ids=[attachment.id]
        )

    def action_revise_offer(self):
        """Allows HR to revise the offer if rejected by candidate."""
        self.ensure_one()
        if self.state not in ['rejected', 'sent']:
            raise UserError(_("You can only revise offers that are in 'Rejected' or 'Offer Sent' state."))

        self.revision += 1
        self.state = 'draft'
        self.message_post(body=_("Offer letter has been reopened for Revision #%s by %s.") % (self.revision, self.env.user.name))

    def action_create_employee(self):
        """Automatically creates hr.employee and hr.contract from accepted offer details."""
        self.ensure_one()
        if self.state != 'accepted':
            raise UserError(_("Employee can only be created once the candidate has accepted the offer."))
        if self.employee_id:
            raise UserError(_("Employee has already been created for this offer (%s).") % self.employee_id.name)

        # 1. Create hr.employee
        employee_vals = {
            'name': self.candidate_name,
            'father_name': self.father_name,
            'ssnid': self.cnic,
            'private_street': self.present_address,
            'mobile_phone': self.phone,
            'work_email': self.email,
            'private_email': self.email,
            'birthday': self.date_of_birth,
            'gender': self.gender,
            'religion': self.religion,
            'marital': self.marital_status,
            'job_id': self.job_id.id,
            'department_id': self.department_id.id,
            'company_id': self.company_id.id,
        }
        employee = self.env['hr.employee'].create(employee_vals)

        # 2. Create hr.contract
        contract_vals = {
            'name': f"Contract - {self.candidate_name}",
            'employee_id': employee.id,
            'wage': self.gross_salary or self.basic_salary,
            'date_start': self.joining_date,
            'job_id': self.job_id.id,
            'department_id': self.department_id.id,
            'company_id': self.company_id.id,
            'state': 'draft',
        }
        contract = self.env['hr.contract'].create(contract_vals)

        # 3. Link back and update Recruitment Applicant/Candidate if present
        self.employee_id = employee.id
        self.contract_id = contract.id
        self.state = 'done'

        if self.applicant_id:
            if self.applicant_id.candidate_id:
                self.applicant_id.candidate_id.employee_id = employee.id
            # Move to Contract Signed / Hired stage if found
            hired_stage = self.env['hr.recruitment.stage'].search([('hired_stage', '=', True)], limit=1)
            if hired_stage:
                self.applicant_id.stage_id = hired_stage.id

        # 4. Notify predefined group (HR, Managers, Admins)
        self._send_onboarding_notification(employee)

        self.message_post(body=_(
            "<strong>Employee Record Created Successfully:</strong><br/>"
            "- Employee: <a href='#' data-oe-model='hr.employee' data-oe-id='%s'>%s</a><br/>"
            "- Contract: <a href='#' data-oe-model='hr.contract' data-oe-id='%s'>%s</a><br/>"
            "- Onboarding notification sent to designated team."
        ) % (employee.id, employee.name, contract.id, contract.name))

        # Return action to view new Employee
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.employee',
            'res_id': employee.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _send_onboarding_notification(self, employee):
        """Sends onboarding email alert to the predefined notification group."""
        self.ensure_one()
        recipients = self.notify_user_ids.filtered(lambda u: u.email)
        if not recipients:
            return

        mail_template = self.env.ref('aesl_hr_offer_letter.mail_template_onboarding_notification', raise_if_not_found=False)
        if mail_template:
            for user in recipients:
                mail_template.with_context(notify_user=user).send_mail(
                    self.id,
                    email_values={'email_to': user.email},
                    force_send=True
                )

    def action_print_offer_letter(self):
        """Direct action to print the PDF Offer Letter."""
        self.ensure_one()
        return self.env.ref('aesl_hr_offer_letter.action_report_hr_offer_letter').report_action(self)

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_reset_to_draft(self):
        self.write({'state': 'draft'})

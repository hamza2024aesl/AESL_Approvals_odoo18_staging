# -*- coding: utf-8 -*-

import uuid
from markupsafe import Markup
from odoo import api, fields, models, http, _
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
        ('accepted', 'Candidate Accepted'),
        ('pending_director', 'Pending Director Approval'),
        ('approved_director', 'Approved by Director'),
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

    # Intimate Directors & Multi-Director Approval Flow
    intimate_director_ids = fields.Many2many(
        'res.users',
        'hr_offer_letter_intimate_director_rel',
        'offer_id',
        'user_id',
        string='Intimate Directors',
        tracking=True,
        help="Directors who will receive notification to review candidate profile and compensation in their portal, and provide approval before employee creation."
    )
    approved_director_ids = fields.Many2many(
        'res.users',
        'hr_offer_letter_approved_director_rel',
        'offer_id',
        'user_id',
        string='Approved Directors',
        readonly=True,
        copy=False,
        tracking=True,
        help="Directors who have approved this onboarding request."
    )
    all_directors_approved = fields.Boolean(
        string='All Directors Approved',
        compute='_compute_all_directors_approved',
        store=True
    )
    director_approval_status = fields.Char(
        string='Director Approval Progress',
        compute='_compute_director_approval_status',
        store=True
    )
    director_approval_date = fields.Datetime(
        string='Director Approval Date',
        readonly=True,
        copy=False,
        tracking=True
    )

    # ---------------------------------------------------------
    # Auto-Generated Onboarding Documents Collection (6 Types)
    # ---------------------------------------------------------
    # 1. Picture (1)
    doc_picture = fields.Binary(string='Candidate Picture / Photo', attachment=True)
    doc_picture_filename = fields.Char(string='Picture Filename')
    has_doc_picture = fields.Boolean(string='Picture Received', compute='_compute_document_statuses', store=True)

    # 2. CNIC (1)
    doc_cnic = fields.Binary(string='CNIC Copy', attachment=True)
    doc_cnic_filename = fields.Char(string='CNIC Filename')
    has_doc_cnic = fields.Boolean(string='CNIC Received', compute='_compute_document_statuses', store=True)

    # 3. Resignation Acceptance Letter
    doc_resignation = fields.Binary(string='Resignation Acceptance Letter', attachment=True)
    doc_resignation_filename = fields.Char(string='Resignation Filename')
    has_doc_resignation = fields.Boolean(string='Resignation Received', compute='_compute_document_statuses', store=True)

    # 4. Educational Documents
    doc_education = fields.Binary(string='Educational Documents', attachment=True)
    doc_education_filename = fields.Char(string='Educational Docs Filename')
    has_doc_education = fields.Boolean(string='Education Received', compute='_compute_document_statuses', store=True)

    # 5. Certification Documents
    doc_certification = fields.Binary(string='Certification Documents', attachment=True)
    doc_certification_filename = fields.Char(string='Certifications Filename')
    has_doc_certification = fields.Boolean(string='Certifications Received', compute='_compute_document_statuses', store=True)

    # 6. Professional Documents
    doc_professional = fields.Binary(string='Professional Documents', attachment=True)
    doc_professional_filename = fields.Char(string='Professional Docs Filename')
    has_doc_professional = fields.Boolean(string='Professional Received', compute='_compute_document_statuses', store=True)

    # Tracking & Summary
    docs_received_count = fields.Integer(string='Received Docs Count', compute='_compute_document_statuses', store=True)
    docs_missing_count = fields.Integer(string='Missing Docs Count', compute='_compute_document_statuses', store=True)
    docs_status = fields.Selection([
        ('pending', 'Awaiting Documents'),
        ('partial', 'Partially Received'),
        ('complete', 'All Documents Uploaded'),
    ], string='Documents Status', compute='_compute_document_statuses', store=True, default='pending')
    docs_request_date = fields.Datetime(string='Documents Requested On', readonly=True, copy=False)
    docs_received_date = fields.Datetime(string='Documents Received On', readonly=True, copy=False)

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

    @api.depends('intimate_director_ids', 'approved_director_ids')
    def _compute_all_directors_approved(self):
        for rec in self:
            if not rec.intimate_director_ids:
                rec.all_directors_approved = False
            else:
                rec.all_directors_approved = all(d in rec.approved_director_ids for d in rec.intimate_director_ids)

    @api.depends('intimate_director_ids', 'approved_director_ids')
    def _compute_director_approval_status(self):
        for rec in self:
            total = len(rec.intimate_director_ids)
            approved = len(rec.approved_director_ids)
            if total == 0:
                rec.director_approval_status = _("No Directors Assigned")
            elif approved == total:
                rec.director_approval_status = _("Fully Approved (%s/%s)") % (approved, total)
            else:
                rec.director_approval_status = _("Pending (%s/%s Approved)") % (approved, total)

    @api.depends('doc_picture', 'doc_cnic', 'doc_resignation', 'doc_education', 'doc_certification', 'doc_professional')
    def _compute_document_statuses(self):
        for rec in self:
            rec.has_doc_picture = bool(rec.doc_picture)
            rec.has_doc_cnic = bool(rec.doc_cnic)
            rec.has_doc_resignation = bool(rec.doc_resignation)
            rec.has_doc_education = bool(rec.doc_education)
            rec.has_doc_certification = bool(rec.doc_certification)
            rec.has_doc_professional = bool(rec.doc_professional)

            count = sum([
                1 if rec.doc_picture else 0,
                1 if rec.doc_cnic else 0,
                1 if rec.doc_resignation else 0,
                1 if rec.doc_education else 0,
                1 if rec.doc_certification else 0,
                1 if rec.doc_professional else 0,
            ])
            rec.docs_received_count = count
            rec.docs_missing_count = 6 - count

            if count == 0:
                rec.docs_status = 'pending'
            elif count == 6:
                rec.docs_status = 'complete'
            else:
                rec.docs_status = 'partial'

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
        restricted_states = ['sent', 'accepted', 'pending_director', 'approved_director', 'done']
        if any(rec.state in restricted_states for rec in self):
            allowed_fields = {
                'state', 'employee_id', 'contract_id', 'access_token',
                'response_date', 'rejection_reason', 'message_follower_ids',
                'activity_ids', 'message_ids', 'revision',
                'intimate_director_ids', 'approved_director_ids',
                'director_approval_date', 'director_approval_status',
                'all_directors_approved',
                'doc_picture', 'doc_picture_filename', 'has_doc_picture',
                'doc_cnic', 'doc_cnic_filename', 'has_doc_cnic',
                'doc_resignation', 'doc_resignation_filename', 'has_doc_resignation',
                'doc_education', 'doc_education_filename', 'has_doc_education',
                'doc_certification', 'doc_certification_filename', 'has_doc_certification',
                'doc_professional', 'doc_professional_filename', 'has_doc_professional',
                'docs_received_count', 'docs_missing_count', 'docs_status',
                'docs_request_date', 'docs_received_date'
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

    def _get_clean_base_url(self):
        """Returns the actual accessible base URL, preferring the active HTTP request host over localhost."""
        try:
            if http.request and hasattr(http.request, 'httprequest') and http.request.httprequest:
                host_url = http.request.httprequest.host_url.rstrip('/')
                if host_url and 'localhost' not in host_url and '127.0.0.1' not in host_url:
                    return host_url
        except Exception:
            pass

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url') or ''
        base_url = base_url.rstrip('/')
        if not base_url or 'localhost' in base_url or '127.0.0.1' in base_url:
            base_url = 'http://test.aesl.com.pk:8017'
        return base_url

    def get_accept_url(self):
        self.ensure_one()
        self._ensure_token()
        base_url = self._get_clean_base_url()
        return f"{base_url}/offer/respond/{self.access_token}?action=accept"

    def get_reject_url(self):
        self.ensure_one()
        self._ensure_token()
        base_url = self._get_clean_base_url()
        return f"{base_url}/offer/respond/{self.access_token}?action=reject"

    def get_director_portal_url(self):
        self.ensure_one()
        base_url = self._get_clean_base_url()
        return f"{base_url}/my/director-offers/{self.id}"

    def get_document_upload_url(self):
        self.ensure_one()
        self._ensure_token()
        base_url = self._get_clean_base_url()
        return f"{base_url}/offer/documents/{self.access_token}"

    # ---------------------------------------------------------
    # Auto-Categorization & Documents App Sync
    # ---------------------------------------------------------
    def _classify_and_store_attachment(self, attachment):
        """
        Auto-categorizes an incoming ir.attachment into one of the 6 onboarding document fields
        based on filenames and keywords, and creates corresponding entry in Documents module.
        """
        self.ensure_one()
        if not attachment or not attachment.datas:
            return None

        filename = (attachment.name or '').lower().strip()
        mimetype = (attachment.mimetype or '').lower().strip()

        # Skip system-generated offer letter attachments
        if filename.startswith('offer_letter') or 'appointment_letter' in filename:
            return None

        classified_category = None

        # 1. Picture (1)
        pic_keywords = ['picture', 'photo', 'image', 'pic', 'avatar', 'dp', 'photograph', 'passport', 'profile_pic', 'headshot']
        # 2. CNIC (1)
        cnic_keywords = ['cnic', 'nic', 'id_card', 'identity', 'national_id', 'nadra', 'b_form', 'smart_card']
        # 3. Resignation Acceptance Letter
        resign_keywords = ['resignation', 'resign', 'relieving', 'clearance', 'acceptance', 'separation', 'leaving']
        # 4. Educational Documents
        edu_keywords = ['degree', 'education', 'transcript', 'academic', 'matric', 'inter', 'bachelor', 'master', 'university', 'college', 'school', 'diploma', 'hec', 'fsc', 'fa', 'dae', 'bs', 'ms', 'phd']
        # 5. Certification Documents
        cert_keywords = ['certif', 'pec', 'cisco', 'ccna', 'ccnp', 'microsoft', 'pmp', 'itil', 'aws', 'azure', 'course', 'license', 'training']
        # 6. Professional Documents
        prof_keywords = ['professional', 'experience', 'payslip', 'salary_slip', 'employment', 'recommendation', 'service_certificate', 'appraisal', 'appointment']

        # Keyword Matching Priority
        if any(kw in filename for kw in cnic_keywords):
            self.sudo().write({'doc_cnic': attachment.datas, 'doc_cnic_filename': attachment.name})
            classified_category = 'CNIC'
        elif any(kw in filename for kw in resign_keywords):
            self.sudo().write({'doc_resignation': attachment.datas, 'doc_resignation_filename': attachment.name})
            classified_category = 'Resignation Acceptance Letter'
        elif any(kw in filename for kw in edu_keywords):
            self.sudo().write({'doc_education': attachment.datas, 'doc_education_filename': attachment.name})
            classified_category = 'Educational Documents'
        elif any(kw in filename for kw in cert_keywords):
            self.sudo().write({'doc_certification': attachment.datas, 'doc_certification_filename': attachment.name})
            classified_category = 'Certification Documents'
        elif any(kw in filename for kw in prof_keywords):
            self.sudo().write({'doc_professional': attachment.datas, 'doc_professional_filename': attachment.name})
            classified_category = 'Professional Documents'
        elif any(kw in filename for kw in pic_keywords) or (mimetype.startswith('image/') and not self.doc_picture):
            self.sudo().write({'doc_picture': attachment.datas, 'doc_picture_filename': attachment.name})
            classified_category = 'Picture'
        else:
            # Fallback based on missing slot if mimetype is image
            if mimetype.startswith('image/') and not self.doc_picture:
                self.sudo().write({'doc_picture': attachment.datas, 'doc_picture_filename': attachment.name})
                classified_category = 'Picture'
            elif not self.doc_professional:
                self.sudo().write({'doc_professional': attachment.datas, 'doc_professional_filename': attachment.name})
                classified_category = 'Professional Documents'

        # Sync to Documents Module (Odoo Documents App)
        self._sync_attachment_to_documents_app(attachment, classified_category or 'Onboarding Document')
        return classified_category

    def _sync_attachment_to_documents_app(self, attachment, category_name):
        """Uploads and categorizes the attachment in Odoo Documents module safely."""
        if 'documents.document' not in self.env:
            return

        try:
            Doc = self.env['documents.document'].sudo()
            # In Odoo 18, folders are documents with type='folder'
            folder = Doc.search([('name', '=', 'HR Onboarding'), ('type', '=', 'folder')], limit=1)
            if not folder:
                folder = Doc.search([('name', 'ilike', 'Recruitment'), ('type', '=', 'folder')], limit=1)
            if not folder:
                folder = Doc.search([('name', 'ilike', 'HR'), ('type', '=', 'folder')], limit=1)
            if not folder:
                folder = Doc.create({
                    'name': 'HR Onboarding',
                    'type': 'folder',
                })

            tag_ids = []
            if 'documents.tag' in self.env:
                Tag = self.env['documents.tag'].sudo()
                tag = Tag.search([('name', '=', category_name)], limit=1)
                if not tag:
                    tag = Tag.create({'name': category_name})
                tag_ids = [(4, tag.id)]

            existing_doc = Doc.search([('attachment_id', '=', attachment.id)], limit=1)
            doc_vals = {
                'name': f"{self.candidate_name} - {category_name} ({attachment.name})",
                'attachment_id': attachment.id,
                'folder_id': folder.id if folder else False,
                'partner_id': self.applicant_id.partner_id.id if self.applicant_id and self.applicant_id.partner_id else False,
                'owner_id': self.hr_manager_id.id if self.hr_manager_id else self.env.user.id,
                'res_model': 'hr.offer.letter',
                'res_id': self.id,
                'type': 'binary',
            }
            if tag_ids:
                doc_vals['tag_ids'] = tag_ids

            if existing_doc:
                existing_doc.write(doc_vals)
            else:
                Doc.create(doc_vals)
        except Exception as e:
            # Safe failover so email sending or chatter posting is NEVER blocked by document sync
            import logging
            logging.getLogger(__name__).warning("Could not sync attachment %s to Documents app: %s", attachment.name, e)

    def _message_post_after_hook(self, message, msg_vals):
        """Intercepts incoming email replies from candidate and classifies attachments."""
        res = super()._message_post_after_hook(message, msg_vals)
        candidate_attachments = message.attachment_ids.filtered(
            lambda a: not (a.name and (a.name.lower().startswith('offer_letter') or 'appointment_letter' in a.name.lower()))
        )
        if candidate_attachments:
            classified = []
            for att in candidate_attachments:
                cat = self._classify_and_store_attachment(att)
                if cat:
                    classified.append(f"{att.name} ➔ <strong>{cat}</strong>")

            if classified:
                self.sudo().write({'docs_received_date': fields.Datetime.now()})
                self.sudo().message_post(body=Markup(
                    "<p style='color: #198754;'><strong>📥 Candidate Onboarding Documents Received &amp; Processed:</strong></p>"
                    "<ul>" + "".join([f"<li>{item}</li>" for item in classified]) + "</ul>"
                    "<p>Documents checklist status: <strong>%s (%s/6 Received)</strong>. Saved to Documents module.</p>"
                ) % (dict(self._fields['docs_status'].selection).get(self.docs_status), self.docs_received_count))
        return res

    # ---------------------------------------------------------
    # Actions & Workflows
    # ---------------------------------------------------------
    def action_submit_for_director_approval(self):
        """Allows HR to manually submit or resubmit onboarding request for Director Approval."""
        self.ensure_one()
        if not self.intimate_director_ids:
            raise UserError(_("Please select at least one Director in 'Intimate Directors' before requesting approval."))
        if self.state not in ['draft', 'sent', 'accepted', 'pending_director']:
            raise UserError(_("You cannot submit for director approval in '%s' status.") % dict(self._fields['state'].selection).get(self.state))

        self.write({
            'state': 'pending_director',
            'approved_director_ids': [(5, 0, 0)],
            'director_approval_date': False,
        })
        self._send_director_notification()
        self.message_post(body=Markup(
            "<p style='color: #0d6efd;'><strong>Onboarding Request Submitted for Director Approval</strong></p>"
            "<p>Request submitted by %s. Notification emails sent to intimate directors: <strong>%s</strong>.</p>"
        ) % (self.env.user.name, ', '.join(self.intimate_director_ids.mapped('name'))))

    def action_director_approve(self, director_user=None):
        """Processes approval from an intimate director."""
        self.ensure_one()
        user = director_user or self.env.user
        if user not in self.intimate_director_ids:
            raise UserError(_("User %s is not assigned as an intimating director for this request.") % user.name)
        if user in self.approved_director_ids:
            raise UserError(_("Director %s has already approved this request.") % user.name)

        # Record approval
        self.sudo().write({
            'approved_director_ids': [(4, user.id)],
        })

        # Check remaining directors
        remaining = self.intimate_director_ids - self.approved_director_ids
        if not remaining:
            # All directors approved!
            self.sudo().write({
                'state': 'approved_director',
                'director_approval_date': fields.Datetime.now(),
            })
            self.sudo().message_post(body=Markup(
                "<p style='color: green;'><strong>🎉 All Director Approvals Received!</strong></p>"
                "<p>Final approval recorded from Director <strong>%s</strong> on %s.</p>"
                "<p>The onboarding request is now <strong>Approved by Director</strong>. HR can now proceed with <strong>Create Employee</strong>.</p>"
            ) % (user.name, fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            # Send notification to HR
            self._send_hr_director_approved_notification(user)
        else:
            remaining_names = ', '.join(remaining.mapped('name'))
            self.sudo().message_post(body=Markup(
                "<p style='color: #0d6efd;'><strong>Director Approval Recorded:</strong></p>"
                "<p>Director <strong>%s</strong> has approved.</p>"
                "<p>Awaiting approval from remaining director(s): <strong>%s</strong>.</p>"
            ) % (user.name, remaining_names))

    def _send_director_notification(self):
        """Sends director approval request email to all users in intimate_director_ids."""
        self.ensure_one()
        directors = self.intimate_director_ids.filtered(lambda u: u.email)
        if not directors:
            return

        mail_template = self.env.ref('aesl_hr_offer_letter.mail_template_director_approval_request', raise_if_not_found=False)
        if mail_template:
            for director in directors:
                mail_template.with_context(director_user=director).send_mail(
                    self.id,
                    email_values={'email_to': director.email},
                    force_send=True
                )

    def _send_hr_director_approved_notification(self, approving_director):
        """Sends alert email to HR when all directors have approved."""
        self.ensure_one()
        recipients = set()
        if self.hr_manager_id and self.hr_manager_id.email:
            recipients.add(self.hr_manager_id.email)
        for u in self.notify_user_ids:
            if u.email:
                recipients.add(u.email)

        if not recipients:
            return

        mail_template = self.env.ref('aesl_hr_offer_letter.mail_template_director_approved_notification', raise_if_not_found=False)
        if mail_template:
            for email in recipients:
                mail_template.with_context(approving_director=approving_director).send_mail(
                    self.id,
                    email_values={'email_to': email},
                    force_send=True
                )
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
            body=Markup(
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

    def action_send_document_request(self):
        """Sends the document request email with the 6 mandatory documents to the candidate."""
        self.ensure_one()
        if not self.email:
            raise UserError(_("Candidate email is required to send document request."))

        self._ensure_token()
        mail_template = self.env.ref('aesl_hr_offer_letter.mail_template_candidate_document_request', raise_if_not_found=False)
        if mail_template:
            mail_template.send_mail(self.id, email_values={'email_to': self.email}, force_send=True)
            self.write({'docs_request_date': fields.Datetime.now()})
            self.message_post(body=Markup(
                "<p style='color: #0d6efd;'><strong>📧 Onboarding Document Request Email Dispatched:</strong></p>"
                "<p>Sent to: <strong>%s</strong> (%s)</p>"
                "<p>6 Mandatory Documents Requested: Picture, CNIC, Resignation Letter, Educational, Certification, Professional.</p>"
            ) % (self.candidate_name, self.email))

    def action_revise_offer(self):
        """Allows HR to revise the offer if rejected by candidate or awaiting changes."""
        self.ensure_one()
        if self.state not in ['rejected', 'sent', 'pending_director', 'approved_director', 'accepted']:
            raise UserError(_("You can only revise offers that are in 'Rejected', 'Offer Sent', or 'Director Approval' state."))

        self.revision += 1
        self.state = 'draft'
        self.approved_director_ids = [(5, 0, 0)]
        self.director_approval_date = False
        self.message_post(body=_("Offer letter has been reopened for Revision #%s by %s. Director approvals have been reset.") % (self.revision, self.env.user.name))

    def action_create_employee(self):
        """Automatically creates hr.employee and hr.contract from approved offer details."""
        self.ensure_one()
        if self.state != 'approved_director':
            raise UserError(_("Employee can only be created once the onboarding request is approved by Director(s)."))
        if self.intimate_director_ids and not self.all_directors_approved:
            raise UserError(_("All intimate directors must approve before an employee record can be created."))
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
        # Auto-set Picture as profile image if received
        if self.doc_picture:
            employee_vals['image_1920'] = self.doc_picture

        employee = self.env['hr.employee'].create(employee_vals)

        # Attach received onboarding documents to the created Employee record
        for doc_field, doc_fname in [
            (self.doc_picture, self.doc_picture_filename or 'Profile_Picture.jpg'),
            (self.doc_cnic, self.doc_cnic_filename or 'CNIC.pdf'),
            (self.doc_resignation, self.doc_resignation_filename or 'Resignation_Letter.pdf'),
            (self.doc_education, self.doc_education_filename or 'Educational_Docs.pdf'),
            (self.doc_certification, self.doc_certification_filename or 'Certifications.pdf'),
            (self.doc_professional, self.doc_professional_filename or 'Professional_Docs.pdf'),
        ]:
            if doc_field:
                self.env['ir.attachment'].sudo().create({
                    'name': doc_fname,
                    'datas': doc_field,
                    'res_model': 'hr.employee',
                    'res_id': employee.id,
                })

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

        self.message_post(body=Markup(
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

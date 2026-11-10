# -*- coding: utf-8 -*-

from markupsafe import Markup
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, http, _
from odoo.exceptions import ValidationError, UserError


class EmployeeResignation(models.Model):
    _name = 'employee.resignation'
    _inherit = ['employee.resignation', 'mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Reference', readonly=True, copy=False, default='New', tracking=True)
    
    # Store user relations for fast portal & record rule lookups
    employee_user_id = fields.Many2one(
        related='emp_name.user_id', string="Employee Portal User", store=True, readonly=True
    )
    manager_user_id = fields.Many2one(
        related='immediate_boss.user_id', string="Manager User", store=True, readonly=True
    )

    # Resignation date default to today
    resignation_date = fields.Date(string="Resignation Date", default=fields.Date.context_today, tracking=True)

    # Notice Period Fields
    notice_period_duration = fields.Selection([
        ('15_days', '15 Days'),
        ('1_month', '1 Month'),
        ('2_month', '2 Months'),
        ('3_month', '3 Months'),
        ('custom', 'Custom Days'),
    ], string='Proposed Notice Period', default='1_month', required=True, tracking=True)
    notice_period_custom_days = fields.Integer(string='Custom Notice Period (Days)', default=30)
    notice_period_display = fields.Char(string='Notice Period', compute='_compute_notice_period_display', store=True)

    # Expected Exit Date
    expected_exit_date = fields.Date(
        string='Calculated Exit Date',
        compute='_compute_expected_exit_date',
        store=True,
        readonly=False,
        tracking=True
    )

    # Reason & Manager remarks
    reason = fields.Text(string='Resignation Reason / Remarks', tracking=True)
    manager_remarks = fields.Text(string='Manager Acceptance Remarks', tracking=True)
    rejection_reason = fields.Text(string='Rejection Remarks', tracking=True)
    acceptance_date = fields.Date(string='Acceptance Date', readonly=True, tracking=True)

    # Revoke Workflow Fields
    is_revoked = fields.Boolean(string='Is Revoked', default=False, tracking=True)
    revoke_reason = fields.Text(string='Revoke Reason / Remarks', tracking=True)
    revoke_date = fields.Date(string='Revoke Request Date', readonly=True, tracking=True)
    revoke_response_remarks = fields.Text(string='Manager Revoke Remarks', tracking=True)

    # Departmental Clearance Fields (Admin, IT, HSE)
    clearance_ids = fields.One2many(
        'employee.resignation.clearance',
        'resignation_id',
        string='Departmental Clearances'
    )
    clearance_admin_status = fields.Selection([
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
    ], string='Admin Clearance', compute='_compute_department_statuses', store=True)

    clearance_it_status = fields.Selection([
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
    ], string='IT Clearance', compute='_compute_department_statuses', store=True)

    clearance_hse_status = fields.Selection([
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
    ], string='HSE Clearance', compute='_compute_department_statuses', store=True)

    # Exit Interview Fields (Conducted by HR)
    exit_interview_conducted_by = fields.Many2one(
        'res.users', string='Interview Conducted By', tracking=True
    )
    exit_interview_date = fields.Date(
        string='Exit Interview Date', default=fields.Date.context_today, tracking=True
    )
    exit_interview_reason_for_leaving = fields.Selection([
        ('better_opportunity', 'Better Opportunity / Career Growth'),
        ('higher_compensation', 'Higher Compensation / Salary Package'),
        ('relocation', 'Relocation / Personal / Family Reasons'),
        ('work_environment', 'Work Environment / Culture'),
        ('further_education', 'Higher Studies / Education'),
        ('health', 'Health Reasons'),
        ('other', 'Other Reasons'),
    ], string='Primary Reason for Leaving', tracking=True)
    exit_interview_feedback = fields.Text(
        string='Employee Feedback & Suggestions',
        help="Employee's thoughts regarding organizational culture, team, and suggestions for improvement.",
        tracking=True
    )
    exit_interview_notes = fields.Text(
        string='HR Interview Assessment & Notes',
        help="Confidential notes and assessment from HR officer.",
        tracking=True
    )

    # Employee Archive Fields
    is_employee_archived = fields.Boolean(string='Archived in Odoo', default=False, readonly=True, tracking=True)
    archived_date = fields.Datetime(string='Archived On', readonly=True)
    archived_by_id = fields.Many2one('res.users', string='Archived By', readonly=True)

    # Default leaving status to resignation as per requirement
    leaving_status = fields.Selection([
        ('resignation', 'Resignation'),
        ('termination', 'Termination')
    ], string='Leaving type', default='resignation', required=True)

    state = fields.Selection(
        selection_add=[
            ('pending_manager', 'Pending Manager Approval'),
            ('serving_notice', 'Forwarded to HR / Serving Notice Period'),
            ('clearance_in_progress', 'Clearance In Progress'),
            ('clearance_complete', 'Clearance Complete'),
            ('exit_interview_pending', 'Exit Interview Pending'),
            ('exit_interview_done', 'Exit Interview Completed'),
            ('archived', 'Employee Archived / Completed'),
            ('rejected', 'Resignation Rejected'),
            ('revoke_pending', 'Revoke Pending'),
            ('revoked', 'Resignation Revoked / Employment Continues'),
        ],
        ondelete={
            'pending_manager': 'set default',
            'serving_notice': 'set default',
            'clearance_in_progress': 'set default',
            'clearance_complete': 'set default',
            'exit_interview_pending': 'set default',
            'exit_interview_done': 'set default',
            'archived': 'set default',
            'rejected': 'set default',
            'revoke_pending': 'set default',
            'revoked': 'set default',
        },
        default='draft',
        tracking=True
    )

    @api.depends('clearance_ids.state', 'clearance_ids.department_type')
    def _compute_department_statuses(self):
        for rec in self:
            admin_cl = rec.clearance_ids.filtered(lambda c: c.department_type == 'admin')
            it_cl = rec.clearance_ids.filtered(lambda c: c.department_type == 'it')
            hse_cl = rec.clearance_ids.filtered(lambda c: c.department_type == 'hse')
            rec.clearance_admin_status = admin_cl.state if admin_cl else 'pending'
            rec.clearance_it_status = it_cl.state if it_cl else 'pending'
            rec.clearance_hse_status = hse_cl.state if hse_cl else 'pending'

    @api.depends('notice_period_duration', 'notice_period_custom_days')
    def _compute_notice_period_display(self):
        duration_labels = {
            '15_days': '15 Days',
            '1_month': '1 Month',
            '2_month': '2 Months',
            '3_month': '3 Months',
        }
        for rec in self:
            if rec.notice_period_duration == 'custom':
                days = rec.notice_period_custom_days or 0
                rec.notice_period_display = f"{days} Days (Custom)"
            else:
                rec.notice_period_display = duration_labels.get(rec.notice_period_duration, '1 Month')

    @api.depends('resignation_date', 'notice_period_duration', 'notice_period_custom_days')
    def _compute_expected_exit_date(self):
        for rec in self:
            start_date = rec.resignation_date or fields.Date.today()
            if rec.notice_period_duration == '15_days':
                target = start_date + relativedelta(days=15)
            elif rec.notice_period_duration == '1_month':
                target = start_date + relativedelta(months=1)
            elif rec.notice_period_duration == '2_month':
                target = start_date + relativedelta(months=2)
            elif rec.notice_period_duration == '3_month':
                target = start_date + relativedelta(months=3)
            elif rec.notice_period_duration == 'custom':
                days = rec.notice_period_custom_days or 30
                target = start_date + relativedelta(days=days)
            else:
                target = start_date + relativedelta(months=1)

            rec.expected_exit_date = target
            rec.exit_date = str(target)

    @api.onchange('resignation_date', 'notice_period_duration', 'notice_period_custom_days')
    def calculate_exit_date(self):
        for rec in self:
            start_date = rec.resignation_date or fields.Date.today()
            if rec.notice_period_duration == '15_days':
                target = start_date + relativedelta(days=15)
            elif rec.notice_period_duration == '1_month':
                target = start_date + relativedelta(months=1)
            elif rec.notice_period_duration == '2_month':
                target = start_date + relativedelta(months=2)
            elif rec.notice_period_duration == '3_month':
                target = start_date + relativedelta(months=3)
            elif rec.notice_period_duration == 'custom':
                days = rec.notice_period_custom_days or 30
                target = start_date + relativedelta(days=days)
            else:
                target = start_date + relativedelta(months=1)

            rec.exit_date = str(target)
            rec.expected_exit_date = target

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                seq = self.env['ir.sequence'].next_by_code('employee.resignation') or 'New'
                vals['name'] = seq
            if not vals.get('leaving_status'):
                vals['leaving_status'] = 'resignation'
        return super().create(vals_list)

    def _compute_display_name(self):
        for rec in self:
            ref = rec.name if rec.name and rec.name != 'New' else ''
            emp = rec.emp_name.name if rec.emp_name else 'Draft'
            rec.display_name = f"{ref} - {emp}" if ref else f"Resignation: {emp}"

    def _get_clean_base_url(self):
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

    def get_portal_url(self):
        self.ensure_one()
        base_url = self._get_clean_base_url()
        return f"{base_url}/my/resignation/{self.id}"

    # ----------------------------------------------------
    # WORKFLOW ACTIONS
    # ----------------------------------------------------

    def action_submit(self):
        """Called when employee submits resignation form."""
        for rec in self:
            if not rec.reason:
                raise ValidationError(_("Please provide a reason/remarks for your resignation."))
            if not rec.resignation_date:
                rec.resignation_date = fields.Date.today()

            # Ensure exit date is computed
            if not rec.expected_exit_date:
                rec._compute_expected_exit_date()

            rec.state = 'pending_manager'

            # Notify reporting manager
            rec._notify_manager_on_submission()
            rec.message_post(
                body=_("Resignation request submitted by %s. Awaiting Reporting Manager approval.") % (rec.emp_name.name),
                subtype_xmlid="mail.mt_comment"
            )

    def action_manager_accept(self, remarks=None):
        """Manager accepts resignation. Starts notice period, sends official Allied CAT memo email, initiates Admin/IT/HSE clearances."""
        for rec in self:
            if rec.state != 'pending_manager':
                raise UserError(_("Only pending resignation requests can be accepted."))

            if remarks:
                rec.manager_remarks = remarks
                rec.boss_remarks = remarks

            rec.acceptance_date = fields.Date.today()
            rec.state = 'clearance_in_progress'

            # Update Employee record
            if rec.emp_name:
                rec.emp_name.resignation_date = rec.resignation_date
                if rec.expected_exit_date:
                    rec.emp_name.exit_date = rec.expected_exit_date
                elif rec.exit_date:
                    try:
                        rec.emp_name.exit_date = fields.Date.from_string(rec.exit_date)
                    except Exception:
                        pass

            # Send official Allied CAT acceptance memorandum email to employee
            rec._send_acceptance_cat_memo()

            # Trigger departmental clearance for Admin, IT, and HSE (Requirement 1)
            rec._initiate_departmental_clearances()

            rec.message_post(
                body=_("Resignation accepted by Manager %s. Status updated to 'Clearance In Progress'. Notice period active until %s. Clearances dispatched to Admin, IT, and HSE heads.")
                % (self.env.user.name, rec.expected_exit_date or rec.exit_date),
                subtype_xmlid="mail.mt_note"
            )

    def _initiate_departmental_clearances(self):
        """Creates or links Admin, IT, and HSE clearance checklists upon resignation acceptance."""
        Clearance = self.env['employee.resignation.clearance'].sudo()
        Template = self.env['hr.asset.item.template'].sudo()

        for rec in self:
            emp = rec.emp_name
            company = rec.company_id or self.env.company

            dept_configs = [
                ('admin', company.asset_admin_head_id),
                ('it', company.asset_it_head_id),
                ('hse', company.asset_hse_head_id),
            ]

            for dept_type, head in dept_configs:
                clearance = Clearance.search([
                    ('resignation_id', '=', rec.id),
                    ('department_type', '=', dept_type),
                ], limit=1)

                if not clearance:
                    clearance = Clearance.create({
                        'resignation_id': rec.id,
                        'department_type': dept_type,
                        'department_head_id': head.id if head else False,
                        'state': 'pending',
                    })
                else:
                    clearance.write({
                        'department_head_id': head.id if head else False,
                        'state': 'pending',
                    })

                if not clearance.line_ids:
                    alloc = self.env['hr.asset.allocation'].sudo().search([
                        ('employee_id', '=', emp.id),
                        ('department_type', '=', dept_type),
                    ], limit=1)

                    lines_vals = []
                    if alloc and alloc.line_ids:
                        allocated_lines = alloc.line_ids.filtered('is_allocated')
                        for l in allocated_lines:
                            lines_vals.append((0, 0, {
                                'sequence': l.sequence,
                                'asset_allocation_line_id': l.id,
                                'name': l.name,
                                'asset_details': l.asset_details or '',
                                'is_allocated': True,
                                'remarks': l.remarks or '',
                            }))
                    elif not alloc:
                        templates = Template.search([
                            ('department_type', '=', dept_type),
                            ('active', '=', True),
                        ], order='sequence, id')
                        for tmpl in templates:
                            lines_vals.append((0, 0, {
                                'sequence': tmpl.sequence,
                                'name': tmpl.name,
                                'asset_details': tmpl.placeholder_hint or '',
                                'is_allocated': True,
                                'remarks': '',
                            }))

                    if lines_vals:
                        clearance.write({'line_ids': lines_vals})

                # Notify department head
                rec._notify_department_head_clearance(clearance)

    def _notify_department_head_clearance(self, clearance):
        template = self.env.ref('aesl_hr_resignation.mail_template_resignation_clearance_head', raise_if_not_found=False)
        if template and clearance.department_head_id:
            try:
                template.sudo().send_mail(clearance.id, force_send=True)
            except Exception:
                pass

    def action_check_clearance_completion(self):
        """Verifies if Admin, IT, and HSE have all approved clearance. If so, advances to Exit Interview."""
        for rec in self:
            clearances = rec.clearance_ids
            # Must have at least 3 clearances and all of them approved
            if len(clearances) >= 3 and all(c.state == 'approved' for c in clearances):
                rec.state = 'exit_interview_pending'

                # Remove returned assets from HR employee asset allocations (Requirement 1.5)
                rec._process_asset_removal()

                rec.message_post(
                    body=Markup(
                        "<b>🎉 Departmental Clearance Completed!</b><br/>"
                        "Admin, IT, and HSE departments have all approved the asset clearance.<br/>"
                        "Next Stage: <b>Exit Interview Pending</b> (to be conducted by HR)."
                    ),
                    subtype_xmlid="mail.mt_comment"
                )

    def _process_asset_removal(self):
        """Once clearance is complete, returned assets (is_allocated == False) are unallocated in HR asset records,
        and employee's asset allocations are archived from the active HR Asset Allocations menu (Requirement 1.5)."""
        for rec in self:
            for cl in rec.clearance_ids:
                for line in cl.line_ids:
                    if not line.is_allocated and line.asset_allocation_line_id:
                        line.asset_allocation_line_id.write({
                            'is_allocated': False,
                            'remarks': f"Returned during resignation clearance on {fields.Date.today()}: {line.remarks or ''}".strip()
                        })
            # Remove from HR asset menu: Archive employee's asset allocations (Requirement 1.5)
            if rec.emp_name:
                allocs = self.env['hr.asset.allocation'].sudo().search([('employee_id', '=', rec.emp_name.id)])
                if allocs:
                    allocs.write({'active': False})

    def action_done_exit_interview(self):
        """HR marks the Exit Interview as Completed."""
        for rec in self:
            if not self.env.user.has_group('hr.group_hr_user'):
                raise UserError(_("Only HR personnel can complete the Exit Interview."))
            if rec.state != 'exit_interview_pending':
                raise UserError(_("Exit Interview can only be completed when stage is 'Exit Interview Pending'."))

            rec.write({
                'state': 'exit_interview_done',
                'exit_interview_conducted_by': self.env.user.id,
                'exit_interview_date': rec.exit_interview_date or fields.Date.today(),
            })
            rec.message_post(
                body=Markup("<b>Exit Interview Completed</b> by HR %s.") % (self.env.user.name),
                subtype_xmlid="mail.mt_comment"
            )

    def action_archive_employee_and_user(self):
        """HR archives the Employee record and Portal User account in Odoo."""
        for rec in self:
            if not self.env.user.has_group('hr.group_hr_user'):
                raise UserError(_("Only HR personnel can archive the employee."))
            if rec.state != 'exit_interview_done':
                raise UserError(_("Archive is only available after Exit Interview is completed."))

            emp = rec.emp_name
            user = emp.user_id if emp else False

            # 1. Archive User (Permanently blocks portal & system login)
            if user:
                user.sudo().write({'active': False})

            # 2. Archive Employee record
            if emp:
                emp.sudo().write({'active': False})

            rec.write({
                'state': 'archived',
                'is_employee_archived': True,
                'archived_date': fields.Datetime.now(),
                'archived_by_id': self.env.user.id,
            })

            rec.message_post(
                body=Markup(
                    "<b>🔒 Offboarding Complete: Employee & User Archived</b><br/>"
                    "Employee: %s (Archived)<br/>"
                    "Portal User: %s (Deactivated - Login Disabled)<br/>"
                    "Actioned by: %s on %s"
                ) % (
                    emp.name if emp else '-',
                    user.login if user else 'None',
                    self.env.user.name,
                    fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                ),
                subtype_xmlid="mail.mt_comment"
            )

    def action_manager_reject(self, remarks):
        """Manager rejects resignation. Rejection remarks are mandatory."""
        for rec in self:
            if rec.state != 'pending_manager':
                raise UserError(_("Only pending resignation requests can be rejected."))

            if not remarks or not remarks.strip():
                raise ValidationError(_("Manager remarks are mandatory when rejecting a resignation request."))

            rec.rejection_reason = remarks.strip()
            rec.boss_remarks = remarks.strip()
            rec.state = 'rejected'

            # Revert any employee dates if set
            if rec.emp_name:
                rec.emp_name.resignation_date = False
                rec.emp_name.exit_date = False

            # Notify employee with rejection remarks
            rec._notify_employee_on_rejection()

            rec.message_post(
                body=_("Resignation rejected by Manager %s. Remarks: %s") % (self.env.user.name, remarks),
                subtype_xmlid="mail.mt_comment"
            )

    def action_request_revoke(self, reason):
        """Employee requests to revoke resignation during notice period."""
        for rec in self:
            if rec.state not in ['serving_notice', 'clearance_in_progress']:
                raise UserError(_("Revocation can only be requested while serving notice period or clearance in progress."))

            if not reason or not reason.strip():
                raise ValidationError(_("Please enter a reason for revoking your resignation."))

            rec.revoke_reason = reason.strip()
            rec.revoke_date = fields.Date.today()
            rec.state = 'revoke_pending'

            # Notify reporting manager
            rec._notify_manager_on_revoke_request()

            rec.message_post(
                body=_("Revoke request submitted by %s. Reason: %s. Awaiting Manager decision.") % (rec.emp_name.name, reason),
                subtype_xmlid="mail.mt_comment"
            )

    def action_manager_accept_revoke(self, remarks=None):
        """Manager accepts revoke. Resignation is cancelled, notice period stopped, employment continues."""
        for rec in self:
            if rec.state != 'revoke_pending':
                raise UserError(_("Only pending revoke requests can be accepted."))

            if remarks:
                rec.revoke_response_remarks = remarks.strip()

            rec.is_revoked = True
            rec.state = 'revoked'

            # Restore normal employment on employee record
            if rec.emp_name:
                rec.emp_name.resignation_date = False
                rec.emp_name.exit_date = False

            # Notify employee and HR
            rec._notify_revoke_accepted()

            rec.message_post(
                body=_("Revoke accepted by Manager %s. Resignation cancelled and regular employment restored.") % (self.env.user.name),
                subtype_xmlid="mail.mt_comment"
            )

    def action_manager_reject_revoke(self, remarks=None):
        """Manager rejects revoke. Resignation stays active and notice period continues."""
        for rec in self:
            if rec.state != 'revoke_pending':
                raise UserError(_("Only pending revoke requests can be rejected."))

            if remarks:
                rec.revoke_response_remarks = remarks.strip()

            rec.state = 'serving_notice'

            # Notify employee
            rec._notify_revoke_rejected()

            rec.message_post(
                body=_("Revoke rejected by Manager %s. Notice period continues until %s.")
                % (self.env.user.name, rec.expected_exit_date or rec.exit_date),
                subtype_xmlid="mail.mt_comment"
            )

    # ----------------------------------------------------
    # NOTIFICATION HELPERS
    # ----------------------------------------------------

    def _send_acceptance_cat_memo(self):
        """Generates the official Resignation Acceptance Memorandum PDF, attaches it to the resignation record and the email, and dispatches to the employee."""
        template = self.env.ref('aesl_hr_resignation.mail_template_resignation_accepted_cat_memo', raise_if_not_found=False)
        if not template:
            return

        for rec in self:
            attachments = []
            report = self.env.ref('aesl_hr_resignation.action_report_resignation_acceptance', raise_if_not_found=False)
            if report:
                try:
                    pdf_content, _report_type = self.env['ir.actions.report']._render_qweb_pdf(report.id, [rec.id])
                    safe_name = (rec.emp_name.name or 'Employee').replace(' ', '_').replace('/', '_')
                    safe_ref = (rec.name or 'MEMO').replace('/', '_').replace(' ', '_')
                    filename = f"Acceptance_Memorandum_{safe_name}_{safe_ref}.pdf"

                    attachment = self.env['ir.attachment'].sudo().create({
                        'name': filename,
                        'type': 'binary',
                        'raw': pdf_content,
                        'res_model': 'employee.resignation',
                        'res_id': rec.id,
                        'mimetype': 'application/pdf',
                    })
                    attachments.append(attachment.id)
                except Exception as e:
                    rec.message_post(body=f"Notice: Could not render Acceptance PDF: {e}", subtype_xmlid="mail.mt_note")

            # Determine recipient partner and email robustly
            emp = rec.emp_name
            partner = (
                emp.work_contact_id
                or (emp.user_id.partner_id if emp.user_id else False)
                or (rec.employee_user_id.partner_id if rec.employee_user_id else False)
                or (emp.user_partner_id if hasattr(emp, 'user_partner_id') else False)
            )
            if not partner and emp:
                partner = self.env['res.partner'].search([('name', '=', emp.name)], limit=1)

            recipient_email = (
                emp.work_email
                or (partner.email if partner else False)
                or (emp.user_id.email if emp.user_id else False)
                or (emp.private_email if hasattr(emp, 'private_email') else False)
            )

            email_values = {}
            if recipient_email:
                email_values['email_to'] = recipient_email
            if partner:
                email_values['recipient_ids'] = [(4, partner.id)]
                email_values['partner_ids'] = [(4, partner.id)]
            if attachments:
                email_values['attachment_ids'] = [(4, att_id) for att_id in attachments]

            template.sudo().send_mail(rec.id, email_values=email_values, force_send=True)

    def _notify_manager_on_submission(self):
        template = self.env.ref('aesl_hr_resignation.mail_template_resignation_submitted_manager', raise_if_not_found=False)
        if template:
            for rec in self:
                if rec.immediate_boss:
                    template.sudo().send_mail(rec.id, force_send=True)

    def _notify_employee_on_rejection(self):
        template = self.env.ref('aesl_hr_resignation.mail_template_resignation_rejected_employee', raise_if_not_found=False)
        if template:
            for rec in self:
                template.sudo().send_mail(rec.id, force_send=True)

    def _notify_manager_on_revoke_request(self):
        template = self.env.ref('aesl_hr_resignation.mail_template_resignation_revoke_requested_manager', raise_if_not_found=False)
        if template:
            for rec in self:
                if rec.immediate_boss:
                    template.sudo().send_mail(rec.id, force_send=True)

    def _notify_revoke_accepted(self):
        template = self.env.ref('aesl_hr_resignation.mail_template_resignation_revoke_accepted_employee', raise_if_not_found=False)
        if template:
            for rec in self:
                template.sudo().send_mail(rec.id, force_send=True)

    def _notify_revoke_rejected(self):
        template = self.env.ref('aesl_hr_resignation.mail_template_resignation_revoke_rejected_employee', raise_if_not_found=False)
        if template:
            for rec in self:
                template.sudo().send_mail(rec.id, force_send=True)


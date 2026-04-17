# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class ApprovalRequest(models.Model):
    _inherit = 'approval.request'

    # Employee Section Fields
    employee_id = fields.Many2one('hr.employee', string='Employee')
    employee_reg_no = fields.Char(string='Employee Reg No', related='employee_id.identification_id', readonly=True)
    employee_location_id = fields.Many2one('hr.work.location', string='Region', related='employee_id.work_location_id', readonly=True)
    employee_department_id = fields.Many2one('hr.department', string='Department', related='employee_id.department_id', readonly=True)
    employee_cnic = fields.Char(string='CNIC', related='employee_id.identification_id', readonly=True)
    employee_dob = fields.Date(string='DOB', related='employee_id.birthday', readonly=True)
    employee_designation_id = fields.Many2one('hr.job', string='Designation', related='employee_id.job_id', readonly=True)
    employee_mobile = fields.Char(string='Mobile No', related='employee_id.mobile_phone', readonly=True)

    # Track Time Off
    time_off_id = fields.Many2one('hr.leave', string='Linked Time Off', readonly=True)

    # Travel Section
    travel_mode = fields.Selection([
        ('air', 'Air'),
        ('train', 'Train'),
        ('car', 'Car'),
        ('bus', 'Bus')
    ], string='Travel Mode')
    
    travel_request_type = fields.Selection([
        ('domestic', 'Domestic'),
        ('international', 'International')
    ], string='Travel Request Type')

    # Administration Section
    admin_remarks = fields.Text(string='Admin Remarks')

    @api.onchange('request_owner_id')
    def _onchange_request_owner_id_set_employee(self):
        if self.request_owner_id:
            employee = self.env['hr.employee'].search([('user_id', '=', self.request_owner_id.id)], limit=1)
            if employee:
                self.employee_id = employee.id

    @api.onchange('employee_id')
    def _onchange_employee_sync_location(self):
        """ Sync standard 'location' field for Odoo's validation """
        if self.employee_id and self.employee_id.work_location_id:
            self.location = self.employee_id.work_location_id.name
    def action_confirm(self):
        """ 
        Simplified approval flow: 
        1. Match Requester's Region & Department with Approval Configuration.
        2. Assign the specific Approver(s) from the configuration.
        3. Only these approvers will have Approve/Refuse access.
        """
        res = super(ApprovalRequest, self).action_confirm()

        for rec in self:
            if not rec.employee_id or not rec.employee_id.work_location_id or not rec.employee_id.department_id:
                continue
            
            # Determine Config Type
            c_type = rec.travel_request_type or 'domestic'
            
            # Find matching approver lines (1st and 2nd approvers)
            approver_lines = self.env['approval.config.line'].sudo().search([
                ('config_id.config_type', '=', c_type),
                ('work_location_id', '=', rec.employee_id.work_location_id.id),
                ('department_id', '=', rec.employee_id.department_id.id),
                ('line_type', 'in', ['first_approver', 'second_approver']),
            ])

            if not approver_lines:
                raise UserError(_("No approver found in %s configuration for Region '%s' and Department '%s'.") % (
                    dict(self._fields['travel_request_type'].selection).get(c_type, c_type).capitalize(),
                    rec.employee_id.work_location_id.name,
                    rec.employee_id.department_id.name
                ))

            # 1. Clear default approvers and set custom ones
            rec.sudo().approver_ids.unlink()
            for line in approver_lines:
                if line.employee_id.user_id:
                    self.env['approval.approver'].sudo().create({
                        'request_id': rec.id,
                        'user_id': line.employee_id.user_id.id,
                        'status': 'pending',
                        'required': True
                    })

            # 2. Force status to 'pending' to activate workflow for approvers
            rec.sudo().write({'request_status': 'pending'})

            # 3. Notify matched approvers
            self._notify_matched_approvers(rec, approver_lines)

            # 4. Manage linked Time Off
            self._create_travel_time_off(rec)

        return res

    def _notify_matched_approvers(self, request, approver_lines):
        """ Send internal message and notification to mapped approvers. """
        approver_partners = approver_lines.mapped('employee_id.user_id.partner_id')
        if approver_partners:
            subject = _("Approval Required: %s") % request.name
            body = _(
                "<p>Hello,</p>"
                "<p>A new travel request <b>%s</b> has been submitted by <b>%s</b> and requires your approval.</p>"
                "<p><b>Region:</b> %s<br/>"
                "<b>Department:</b> %s</p>"
                "<p>Please review and take action.</p>"
            ) % (
                request.name,
                request.employee_id.name,
                request.employee_id.work_location_id.name,
                request.employee_id.department_id.name
            )
            request.message_post(
                body=body,
                subject=subject,
                partner_ids=approver_partners.ids,
                subtype_xmlid='mail.mt_comment'
            )

    def _create_travel_time_off(self, request):
        """ Create a pending time off record linked to this travel request. """
        if request.date_start and request.date_end:
            leave_type = self.env['hr.leave.type'].search([], limit=1)
            if leave_type:
                leave_vals = {
                    'name': f"Travel Approval: {request.name}",
                    'employee_id': request.employee_id.id,
                    'holiday_status_id': leave_type.id,
                    'request_date_from': request.date_start.date(),
                    'request_date_to': request.date_end.date(),
                    'date_from': request.date_start,
                    'date_to': request.date_end,
                    'number_of_days': (request.date_end - request.date_start).days + 1,
                }
                leave = self.env['hr.leave'].sudo().create(leave_vals)
                request.sudo().write({'time_off_id': leave.id})

    def action_approve(self, approver=None):
        """ When approved, approve Time Off and send emails to Finance & HR. """
        res = super(ApprovalRequest, self).action_approve(approver=approver)
        for request in self:
            if request.request_status == 'approved' and request.time_off_id:
                request.time_off_id.sudo().action_approve()
                self._send_workflow_notification_emails(request)
        return res

    def action_refuse(self, approver=None):
        """ When refused, refuse/unlink Time Off. """
        res = super(ApprovalRequest, self).action_refuse(approver=approver)
        for request in self:
            if request.time_off_id:
                request.time_off_id.sudo().action_refuse()
                # Optional: request.time_off_id.sudo().unlink() 
        return res

    def _send_workflow_notification_emails(self, request):
        """ Logic to find recipients from approval.config and send notification. """
        config_type = 'domestic' if request.travel_request_type == 'domestic' else 'international'
        
        config_lines = self.env['approval.config.line'].search([
            ('config_id.config_type', '=', config_type),
            ('line_type', 'in', ['finance', 'hr']),
            ('work_location_id', '=', request.employee_id.work_location_id.id),
            ('department_id', '=', request.employee_id.department_id.id),
        ])
        
        recipients = config_lines.mapped('employee_id.work_contact_id') or config_lines.mapped('employee_id.user_id.partner_id')
        
        if recipients:
            subject = f"Approved: {request.name} - {request.employee_id.name}"
            body = f"<p>The travel request for <b>{request.employee_id.name}</b> has been approved.</p>"
            body += f"<p>Dates: {request.date_start} to {request.date_end}</p>"
            
            request.message_post(
                body=body,
                subject=subject,
                partner_ids=recipients.ids,
                subtype_xmlid='mail.mt_comment'
            )

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
    
    tickets_required = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No')
    ], string='Tickets Required?', required=True, default='no')

    travel_schedule_ids = fields.One2many('approval.travel.schedule', 'request_id', string='Traveling Schedule')

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
        # Auto-fill the standard 'location' field so Odoo's built-in
        # required-field validation never blocks submission when 'location'
        # is hidden in our custom form but marked required in the category.
        for rec in self:
            if not rec.location and rec.employee_id and rec.employee_id.work_location_id:
                rec.location = rec.employee_id.work_location_id.name
            if rec.request_status == 'refused':
                rec.sudo().write({'request_status': 'draft'})

        res = super(ApprovalRequest, self).action_confirm()

        for rec in self:
            if not rec.employee_id or not rec.employee_id.work_location_id or not rec.employee_id.department_id:
                continue
            
            # Determine Config Type
            c_type = rec.travel_request_type or 'domestic'
            
            # Find matching approver lines (1st approver only)
            approver_lines = self.env['approval.config.line'].sudo().search([
                ('config_id.config_type', '=', c_type),
                ('work_location_ids', 'in', rec.employee_id.work_location_id.id),
                ('department_id', '=', rec.employee_id.department_id.id),
                ('line_type', '=', 'first_approver'),
            ])

            if not approver_lines:
                raise UserError(_("No 1st approver found in %s configuration for Region '%s' and Department '%s'.") % (
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
            body = _("plz review the request and take action")
            request.message_post(
                body=body,
                subject=subject,
                partner_ids=approver_partners.ids,
                subtype_xmlid='mail.mt_comment'
            )

    def _create_travel_time_off(self, request):
        """ Create or update a pending time off record linked to this travel request. """
        if request.date_start and request.date_end:
            # Search for 'Official Visit' leave type
            leave_type = self.env['hr.leave.type'].sudo().search([('name', 'ilike', 'Official Visit')], limit=1)
            if not leave_type:
                leave_type = self.env['hr.leave.type'].sudo().search([], limit=1)
            
            if leave_type:
                leave_vals = {
                    'name': f"Travel Approval: {request.name}",
                    'employee_id': request.employee_id.id,
                    'holiday_status_id': leave_type.id,
                    'request_date_from': fields.Datetime.context_timestamp(request, request.date_start).date(),
                    'request_date_to': fields.Datetime.context_timestamp(request, request.date_end).date(),
                    'date_from': request.date_start,
                    'date_to': request.date_end,
                    'number_of_days': (request.date_end - request.date_start).days + 1,
                    'state': 'confirm', # Force 'To Approve' state on creation
                }
                
                if request.time_off_id:
                    # Update existing record if it was refused or still pending
                    request.time_off_id.sudo().write(leave_vals)
                    leave = request.time_off_id
                else:
                    leave = self.env['hr.leave'].sudo().create(leave_vals)
                    request.sudo().write({'time_off_id': leave.id})
                
                # Double check it stays in 'To Approve' (confirm) state
                if leave.state in ['refuse', 'cancel']:
                    leave.sudo().action_reset_confirm()
                elif leave.state == 'draft':
                    if hasattr(leave, 'action_confirm'):
                        leave.sudo().action_confirm()
                    else:
                        leave.sudo().write({'state': 'confirm'})
                elif leave.state == 'validate':
                    # If it somehow auto-approved, move it back to confirm
                    leave.sudo().write({'state': 'confirm'})

    def action_approve(self, approver=None):
        """ When approved, handle sequential approver for international, approve Time Off, and send notifications. """
        for rec in self:
            if rec.travel_request_type == 'international':
                # Search for the second approver in the config
                second_approver_line = self.env['approval.config.line'].sudo().search([
                    ('config_id.config_type', '=', 'international'),
                    ('work_location_ids', 'in', rec.employee_id.work_location_id.id),
                    ('department_id', '=', rec.employee_id.department_id.id),
                    ('line_type', '=', 'second_approver'),
                ], limit=1)
                
                if second_approver_line:
                    # Check if second approver record is already created
                    second_approver = rec.approver_ids.filtered(lambda a: a.user_id.id == second_approver_line.employee_id.user_id.id)
                    if not second_approver:
                        # 1st approver approved. Write status for current approver line.
                        curr_approver = approver or rec.approver_ids.filtered(lambda a: a.user_id == self.env.user and a.status == 'pending')
                        if curr_approver:
                            curr_approver.sudo().write({'status': 'approved'})
                        
                        # Create the 2nd approver record
                        self.env['approval.approver'].sudo().create({
                            'request_id': rec.id,
                            'user_id': second_approver_line.employee_id.user_id.id,
                            'status': 'pending',
                            'required': True
                        })
                        
                        # Force request status back to 'pending'
                        rec.sudo().write({'request_status': 'pending'})
                        
                        # Notify the 2nd approver
                        rec._notify_matched_approvers(rec, second_approver_line)
                        
                        # Skip final approval logic for now
                        continue
            
            # Default approve logic for domestic or for final international approval
            super(ApprovalRequest, rec).action_approve(approver=approver)
            
            if rec.request_status == 'approved' and rec.time_off_id:
                leave = rec.time_off_id.sudo()
                if leave.state in ['refuse', 'cancel']:
                    leave.action_reset_confirm()
                elif leave.state == 'draft':
                    if hasattr(leave, 'action_confirm'):
                        leave.action_confirm()
                    else:
                        leave.write({'state': 'confirm'})
                
                if leave.state == 'confirm':
                    leave.action_approve()
                
                rec._send_workflow_notification_emails(rec)
        return True

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
        
        config_lines = self.env['approval.config.line'].sudo().search([
            ('config_id.config_type', '=', config_type),
            ('line_type', 'in', ['finance', 'hr']),
            ('work_location_ids', 'in', request.employee_id.work_location_id.id),
            ('department_id', '=', request.employee_id.department_id.id),
        ])
        
        recipients = config_lines.mapped('employee_id.work_contact_id') or config_lines.mapped('employee_id.user_id.partner_id')
        
        if recipients:
            subject = f"Approved: {request.name} - {request.employee_id.name}"
            if request.travel_request_type == 'international':
                body = _("The request is approved by both approver.")
            else:
                body = _("The request is approved by approver.")
            
            request.message_post(
                body=body,
                subject=subject,
                partner_ids=recipients.ids,
                subtype_xmlid='mail.mt_comment'
            )

    def _send_admin_remarks_notification(self):
        for request in self:
            if request.travel_request_type != 'international':
                continue
            
            # Find the configuration lines for 1st, 2nd approver and HR
            config_lines = self.env['approval.config.line'].sudo().search([
                ('config_id.config_type', '=', 'international'),
                ('line_type', 'in', ['first_approver', 'second_approver', 'hr']),
                ('work_location_ids', 'in', request.employee_id.work_location_id.id),
                ('department_id', '=', request.employee_id.department_id.id),
            ])
            
            # Get partners for approvers and HR
            recipients = config_lines.mapped('employee_id.work_contact_id') or config_lines.mapped('employee_id.user_id.partner_id')
            
            # Add the requester partner
            requester_partner = request.employee_id.work_contact_id or request.request_owner_id.partner_id
            
            all_recipients = recipients + requester_partner
            # Filter out duplicates and empty values
            all_recipients = all_recipients.filtered(lambda r: r)
            
            if all_recipients:
                subject = f"Admin Approved: {request.name} - {request.employee_id.name}"
                body = _("admin also approved the request")
                
                request.message_post(
                    body=body,
                    subject=subject,
                    partner_ids=all_recipients.ids,
                    subtype_xmlid='mail.mt_comment'
                )

    def write(self, vals):
        notified_requests = self.env['approval.request']
        if 'admin_remarks' in vals and vals.get('admin_remarks'):
            for rec in self:
                if rec.request_status == 'approved' and rec.travel_request_type == 'international' and not rec.admin_remarks:
                    notified_requests |= rec
        
        res = super(ApprovalRequest, self).write(vals)
        
        if notified_requests:
            notified_requests._send_admin_remarks_notification()
            
        return res


class ApprovalTravelSchedule(models.Model):
    _name = 'approval.travel.schedule'
    _description = 'Travel Schedule'

    request_id = fields.Many2one('approval.request', string='Request', ondelete='cascade')
    departure_from = fields.Char(string='Departure From', required=True)
    arrival_destination = fields.Char(string='Arrival (Destination)', required=True)
    arrival_date = fields.Date(string='Arrival Date', required=True)
    arrival_time = fields.Char(string='Arrival Time', required=True)

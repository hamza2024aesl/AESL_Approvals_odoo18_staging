# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class HrDocumentRequest(models.Model):
    _name = 'hr.document.request'
    _description = 'HR Employee Document Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Document Title', required=True, tracking=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Partner', compute='_compute_partner_id', store=True)
    user_id = fields.Many2one('res.users', string='Related User', compute='_compute_partner_id', store=True)
    
    instructions = fields.Text(string='Instructions / Description')
    deadline = fields.Date(string='Deadline')
    
    folder_id = fields.Many2one('documents.folder', string='Workspace / Folder', tracking=True)
    tag_ids = fields.Many2many('documents.tag', string='Tags')
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending Upload'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], string='Status', default='draft', tracking=True, required=True)
    
    attachment_id = fields.Many2one('ir.attachment', string='Uploaded Attachment', tracking=True)
    attachment_file = fields.Binary(related='attachment_id.datas', string='Attachment Data', readonly=False)
    attachment_name = fields.Char(related='attachment_id.name', string='Attachment Name', readonly=False)
    
    signature = fields.Binary(string='Digital Signature', attachment=True)
    signed_by = fields.Char(string='Signed By')
    signed_on = fields.Datetime(string='Signed On')
    
    document_id = fields.Many2one('documents.document', string='Created Document', readonly=True)

    @api.depends('employee_id', 'employee_id.user_id', 'employee_id.work_contact_id')
    def _compute_partner_id(self):
        for rec in self:
            if rec.employee_id:
                rec.user_id = rec.employee_id.user_id
                rec.partner_id = rec.employee_id.user_id.partner_id or rec.employee_id.work_contact_id
            else:
                rec.user_id = False
                rec.partner_id = False

    def action_send_request(self):
        for rec in self:
            if rec.state == 'draft':
                rec.state = 'pending'
                if rec.partner_id:
                    rec.message_post(
                        body=_(f"Document request '{rec.name}' has been sent to employee {rec.employee_id.name}."),
                        partner_ids=[rec.partner_id.id]
                    )

    def action_approve(self):
        for rec in self:
            if rec.state in ['submitted', 'pending']:
                rec.state = 'approved'
                # Update or create document in Odoo Documents app
                if rec.attachment_id:
                    if rec.document_id:
                        rec.document_id.sudo().write({
                            'attachment_id': rec.attachment_id.id,
                            'name': rec.name or rec.attachment_id.name,
                        })
                    else:
                        doc = self.env['documents.document'].sudo().create({
                            'name': rec.name or rec.attachment_id.name,
                            'attachment_id': rec.attachment_id.id,
                            'folder_id': rec.folder_id.id if rec.folder_id else False,
                            'tag_ids': [(6, 0, rec.tag_ids.ids)] if rec.tag_ids else False,
                            'owner_id': rec.user_id.id if rec.user_id else self.env.user.id,
                            'partner_id': rec.partner_id.id if rec.partner_id else False,
                            'res_model': rec._name,
                            'res_id': rec.id,
                        })
                        rec.document_id = doc.id

                    # Attach Digital Signature to Documents App Chatter/Attachments
                    if rec.signature and rec.document_id:
                        sig_attachment = self.env['ir.attachment'].sudo().create({
                            'name': f"Digital_Signature_{rec.signed_by or 'Employee'}.png",
                            'datas': rec.signature,
                            'mimetype': 'image/png',
                            'res_model': 'documents.document',
                            'res_id': rec.document_id.id,
                        })
                        signed_by_name = rec.signed_by or (rec.employee_id.name if rec.employee_id else 'Employee')
                        signed_time = fields.Datetime.to_string(rec.signed_on or fields.Datetime.now())
                        rec.document_id.sudo().message_post(
                            body=f"Document digitally signed by {signed_by_name} on {signed_time}.",
                            attachment_ids=[sig_attachment.id]
                        )

    def action_reject(self):
        for rec in self:
            rec.state = 'rejected'

    def action_reset_draft(self):
        for rec in self:
            rec.state = 'draft'

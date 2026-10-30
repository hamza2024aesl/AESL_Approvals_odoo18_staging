# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
import uuid


class HrAssetAllocation(models.Model):
    _name = 'hr.asset.allocation'
    _description = 'Departmental Employee Asset Allocation'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'id desc'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New')
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        ondelete='cascade',
        tracking=True,
        index=True
    )
    department_type = fields.Selection([
        ('admin', 'Admin Department'),
        ('it', 'IT Department'),
        ('hse', 'HSE Department'),
    ], string='Department', required=True, tracking=True, index=True)

    department_name = fields.Char(
        string='Department Name',
        compute='_compute_department_name'
    )

    @api.depends('department_type')
    def _compute_department_name(self):
        selection_dict = dict(self._fields['department_type'].selection)
        for rec in self:
            rec.department_name = selection_dict.get(rec.department_type, '')

    department_head_id = fields.Many2one(
        'res.users',
        string='Responsible Department Head',
        tracking=True,
        index=True
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Head Partner',
        related='department_head_id.partner_id',
        store=True,
        index=True
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True
    )
    state = fields.Selection([
        ('pending', 'Pending Allocation'),
        ('approved', 'Allocated & Approved'),
    ], string='Status', default='pending', tracking=True, copy=False, index=True)

    approved_by_id = fields.Many2one(
        'res.users',
        string='Approved By',
        readonly=True,
        copy=False,
        tracking=True
    )
    approval_date = fields.Datetime(
        string='Approval Date',
        readonly=True,
        copy=False,
        tracking=True
    )
    remarks = fields.Text(string='Department Head Remarks')
    line_ids = fields.One2many(
        'hr.asset.allocation.line',
        'allocation_id',
        string='Checklist Items'
    )

    allocated_count = fields.Integer(
        string='Allocated Count',
        compute='_compute_counts'
    )
    total_count = fields.Integer(
        string='Total Items',
        compute='_compute_counts'
    )

    @api.depends('line_ids.is_allocated')
    def _compute_counts(self):
        for rec in self:
            rec.total_count = len(rec.line_ids)
            rec.allocated_count = len(rec.line_ids.filtered('is_allocated'))

    def _compute_access_url(self):
        super()._compute_access_url()
        for rec in self:
            rec.access_url = f'/my/asset_allocation/{rec.id}'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                dept = vals.get('department_type', 'gen').upper()
                seq_code = f'ASSET/{dept}'
                # Simple unique human-friendly name
                vals['name'] = f"{seq_code}/{self.env['ir.sequence'].next_by_code('hr.asset.allocation') or uuid.uuid4().hex[:6].upper()}"
            if not vals.get('access_token'):
                vals['access_token'] = uuid.uuid4().hex
        return super().create(vals_list)

    def action_approve(self):
        self.ensure_one()
        self.write({
            'state': 'approved',
            'approved_by_id': self.env.user.id,
            'approval_date': fields.Datetime.now(),
        })

        dept_label = dict(self._fields['department_type'].selection).get(self.department_type)
        user_name = self.env.user.name or 'Authorized Head'

        # Post in allocation record chatter
        self.message_post(
            body=_("<b>Asset Allocation Approved</b><br/>Department: %s<br/>Approved By: %s<br/>Allocated Items: %d of %d") % (
                dept_label, user_name, self.allocated_count, self.total_count
            ),
            subtype_xmlid='mail.mt_comment'
        )

        # Post in employee record chatter
        if self.employee_id:
            self.employee_id.message_post(
                body=_("<b>%s Asset Allocation Completed</b><br/>Checklist approved by %s on %s.") % (
                    dept_label,
                    user_name,
                    fields.Datetime.now().strftime('%Y-%m-%d %H:%M')
                ),
                subtype_xmlid='mail.mt_comment'
            )
        return True

    def action_reset_draft(self):
        for rec in self:
            rec.write({
                'state': 'pending',
                'approved_by_id': False,
                'approval_date': False,
            })
            rec.message_post(body=_("Asset allocation reset to Pending for revision."))

    def action_send_notification(self):
        self.ensure_one()
        template = self.env.ref('aesl_hr_asset_allocation.mail_template_asset_allocation_request', raise_if_not_found=False)
        if template and self.department_head_id and self.department_head_id.email:
            template.send_mail(self.id, force_send=True)
            self.message_post(body=_("Notification email sent to %s (%s)") % (
                self.department_head_id.name, self.department_head_id.email
            ))
        else:
            raise UserError(_("Cannot send email: Assigned department head has no email configured or template is missing."))

    def get_portal_url(self):
        self.ensure_one()
        return f'/my/asset_allocation/{self.id}'


class HrAssetAllocationLine(models.Model):
    _name = 'hr.asset.allocation.line'
    _description = 'Asset Allocation Checklist Item'
    _order = 'sequence, id'

    allocation_id = fields.Many2one(
        'hr.asset.allocation',
        string='Asset Allocation',
        required=True,
        ondelete='cascade',
        index=True
    )
    sequence = fields.Integer(string='Sequence', default=10)
    name = fields.Char(string='Asset / Item Description', required=True)
    placeholder_hint = fields.Char(string='Details Placeholder / Hint')
    is_allocated = fields.Boolean(string='Allocated', default=False)
    asset_details = fields.Char(string='Serial # / Reg # / Details')
    remarks = fields.Char(string='Remarks')

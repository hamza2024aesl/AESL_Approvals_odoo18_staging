# -*- coding: utf-8 -*-

from markupsafe import Markup
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class EmployeeResignationClearance(models.Model):
    _name = 'employee.resignation.clearance'
    _description = 'Departmental Resignation Asset Clearance'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id asc'

    resignation_id = fields.Many2one(
        'employee.resignation',
        string='Resignation Request',
        required=True,
        ondelete='cascade',
        index=True
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        related='resignation_id.emp_name',
        store=True,
        index=True
    )
    department_type = fields.Selection([
        ('admin', 'Admin Department'),
        ('it', 'IT Department'),
        ('hse', 'HSE Department'),
    ], string='Department', required=True, index=True)

    department_name = fields.Char(
        string='Department Name',
        compute='_compute_department_name',
        store=True
    )

    @api.depends('department_type')
    def _compute_department_name(self):
        selection_dict = dict(self._fields['department_type'].selection)
        for rec in self:
            rec.department_name = selection_dict.get(rec.department_type, '')

    department_head_id = fields.Many2one(
        'res.users',
        string='Responsible Department Head',
        index=True
    )

    state = fields.Selection([
        ('pending', 'Clearance In Progress'),
        ('approved', 'Clearance Approved'),
    ], string='Status', default='pending', tracking=True)

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
        'employee.resignation.clearance.line',
        'clearance_id',
        string='Asset Checklist'
    )

    total_count = fields.Integer(string='Total Assets', compute='_compute_counts')
    returned_count = fields.Integer(string='Returned Assets', compute='_compute_counts')
    pending_count = fields.Integer(string='Pending Assets', compute='_compute_counts')

    @api.depends('line_ids', 'line_ids.is_allocated')
    def _compute_counts(self):
        for rec in self:
            rec.total_count = len(rec.line_ids)
            # is_allocated == False means the asset has been returned by employee
            rec.returned_count = len(rec.line_ids.filtered(lambda l: not l.is_allocated))
            rec.pending_count = len(rec.line_ids.filtered('is_allocated'))

    def action_approve(self, remarks=None):
        """Approve department clearance. Unchecked items are confirmed as returned."""
        for rec in self:
            if rec.state == 'approved':
                continue
            if remarks:
                rec.remarks = remarks

            rec.write({
                'state': 'approved',
                'approved_by_id': self.env.user.id,
                'approval_date': fields.Datetime.now(),
            })

            rec.message_post(
                body=Markup("<b>%s Clearance Approved</b><br/>Approved by: %s<br/>Returned Assets: %d of %d<br/>Remarks: %s") % (
                    rec.department_name,
                    self.env.user.name,
                    rec.returned_count,
                    rec.total_count,
                    rec.remarks or 'None'
                ),
                subtype_xmlid='mail.mt_comment'
            )

            # Trigger resignation-level verification
            rec.resignation_id.action_check_clearance_completion()
        return True

    def get_portal_url(self):
        self.ensure_one()
        base_url = self.resignation_id._get_clean_base_url() if self.resignation_id else ''
        if not base_url:
            base_url = 'http://test.aesl.com.pk:8017'
        return f'{base_url}/my/clearance/{self.id}'


class EmployeeResignationClearanceLine(models.Model):
    _name = 'employee.resignation.clearance.line'
    _description = 'Resignation Clearance Asset Item'
    _order = 'sequence, id'

    clearance_id = fields.Many2one(
        'employee.resignation.clearance',
        string='Clearance Reference',
        required=True,
        ondelete='cascade',
        index=True
    )
    sequence = fields.Integer(string='Sequence', default=10)
    asset_allocation_line_id = fields.Many2one(
        'hr.asset.allocation.line',
        string='Original Asset Line',
        ondelete='set null'
    )
    name = fields.Char(string='Asset / Item Description', required=True)
    asset_details = fields.Char(string='Serial # / Reg # / Details')
    # is_allocated: True = Employee still has it; Unchecked (False) = Returned!
    is_allocated = fields.Boolean(
        string='Still in Possession',
        default=True,
        help="Check if employee still holds this item. Uncheck when the item is returned to the company."
    )
    is_returned = fields.Boolean(
        string='Returned to Company',
        compute='_compute_is_returned',
        store=True,
        help="Automatically computed as the inverse of is_allocated."
    )
    remarks = fields.Char(string='Remarks (Missing / Damaged)')

    @api.depends('is_allocated')
    def _compute_is_returned(self):
        for line in self:
            line.is_returned = not line.is_allocated


# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    asset_allocation_ids = fields.One2many(
        'hr.asset.allocation',
        'employee_id',
        string='Asset Allocations'
    )
    asset_allocation_count = fields.Integer(
        string='Allocations Count',
        compute='_compute_asset_allocation_count'
    )
    asset_status = fields.Selection([
        ('none', 'Not Initiated'),
        ('pending', 'Pending Approval'),
        ('approved', 'All Approved'),
    ], string='Asset Allocation Status', compute='_compute_asset_status', store=True)

    @api.depends('asset_allocation_ids', 'asset_allocation_ids.state')
    def _compute_asset_status(self):
        for emp in self:
            if not emp.asset_allocation_ids:
                emp.asset_status = 'none'
            elif all(alloc.state == 'approved' for alloc in emp.asset_allocation_ids):
                emp.asset_status = 'approved'
            else:
                emp.asset_status = 'pending'

    @api.depends('asset_allocation_ids')
    def _compute_asset_allocation_count(self):
        for emp in self:
            emp.asset_allocation_count = len(emp.asset_allocation_ids)

    @api.model_create_multi
    def create(self, vals_list):
        employees = super().create(vals_list)
        for emp in employees:
            emp._create_department_asset_allocations()
        return employees

    def _create_department_asset_allocations(self):
        """Automatically spawns Admin, IT, and HSE asset allocations upon employee creation."""
        Allocation = self.env['hr.asset.allocation'].sudo()
        Template = self.env['hr.asset.item.template'].sudo()
        MailTemplate = self.env.ref('aesl_hr_asset_allocation.mail_template_asset_allocation_request', raise_if_not_found=False)

        for emp in self:
            company = emp.company_id or self.env.company
            dept_configs = [
                ('admin', company.asset_admin_head_id),
                ('it', company.asset_it_head_id),
                ('hse', company.asset_hse_head_id),
            ]

            for dept_type, head in dept_configs:
                # Check if an allocation already exists for this department
                existing = Allocation.search([
                    ('employee_id', '=', emp.id),
                    ('department_type', '=', dept_type),
                ], limit=1)

                if not existing:
                    templates = Template.search([
                        ('department_type', '=', dept_type),
                        ('active', '=', True),
                    ], order='sequence, id')

                    lines = [(0, 0, {
                        'name': tmpl.name,
                        'sequence': tmpl.sequence,
                        'placeholder_hint': tmpl.placeholder_hint,
                    }) for tmpl in templates]

                    allocation = Allocation.create({
                        'employee_id': emp.id,
                        'department_type': dept_type,
                        'department_head_id': head.id if head else False,
                        'company_id': company.id,
                        'line_ids': lines,
                    })

                    # Dispatch notification email to department head
                    if MailTemplate and head and head.email:
                        try:
                            MailTemplate.send_mail(allocation.id, force_send=True)
                        except Exception as e:
                            # Log error without blocking employee creation
                            allocation.message_post(body=_("Could not send automated email to %s: %s") % (head.name, str(e)))

    def action_generate_asset_allocations(self):
        """Manual trigger to generate checklists (useful for existing employees or testing)."""
        self._create_department_asset_allocations()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Asset Checklists Generated'),
                'message': _('Departmental asset checklists have been successfully prepared for %s.') % self.name,
                'sticky': False,
                'type': 'success',
            }
        }

    def action_view_asset_allocations(self):
        self.ensure_one()
        return {
            'name': _('Asset Allocations - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'hr.asset.allocation',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }

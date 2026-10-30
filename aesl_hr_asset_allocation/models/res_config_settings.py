# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    asset_admin_head_id = fields.Many2one(
        'res.users',
        string='Admin Department Head',
        help="Designated head responsible for Admin asset allocations and approvals."
    )
    asset_it_head_id = fields.Many2one(
        'res.users',
        string='IT Department Head',
        help="Designated head responsible for IT asset allocations and approvals."
    )
    asset_hse_head_id = fields.Many2one(
        'res.users',
        string='HSE Department Head',
        help="Designated head responsible for HSE asset allocations and approvals."
    )


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    asset_admin_head_id = fields.Many2one(
        'res.users',
        related='company_id.asset_admin_head_id',
        readonly=False,
        string='Admin Department Head',
        help="Head responsible for Admin asset allocations and approvals."
    )
    asset_it_head_id = fields.Many2one(
        'res.users',
        related='company_id.asset_it_head_id',
        readonly=False,
        string='IT Department Head',
        help="Head responsible for IT asset allocations and approvals."
    )
    asset_hse_head_id = fields.Many2one(
        'res.users',
        related='company_id.asset_hse_head_id',
        readonly=False,
        string='HSE Department Head',
        help="Head responsible for HSE asset allocations and approvals."
    )

    def set_values(self):
        super().set_values()
        # When a department head is changed, update pending allocations to reflect the new head immediately
        Allocation = self.env['hr.asset.allocation'].sudo()
        for company in self.env['res.company'].search([]):
            head_map = {
                'admin': company.asset_admin_head_id,
                'it': company.asset_it_head_id,
                'hse': company.asset_hse_head_id,
            }
            for dept_type, new_head in head_map.items():
                if new_head:
                    pending_allocs = Allocation.search([
                        ('company_id', '=', company.id),
                        ('department_type', '=', dept_type),
                        ('state', '=', 'pending'),
                        ('department_head_id', '!=', new_head.id),
                    ])
                    if pending_allocs:
                        pending_allocs.write({
                            'department_head_id': new_head.id,
                            'partner_id': new_head.partner_id.id,
                        })

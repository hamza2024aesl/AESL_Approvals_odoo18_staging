# -*- coding: utf-8 -*-

from odoo import http, fields, _
from odoo.addons.portal.controllers.portal import CustomerPortal, pager
from odoo.http import request
from werkzeug.exceptions import Forbidden, NotFound


class AssetAllocationPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        user = request.env.user
        partner = user.partner_id

        domain = ['|', ('department_head_id', '=', user.id), ('partner_id', '=', partner.id)]
        Allocation = request.env['hr.asset.allocation'].sudo()

        if 'asset_allocation_count' in counters:
            values['asset_allocation_count'] = Allocation.search_count(domain)

        pending_domain = domain + [('state', '=', 'pending')]
        values['pending_asset_allocation_count'] = Allocation.search_count(pending_domain)
        return values

    @http.route(['/my/asset_allocations', '/my/asset_allocations/page/<int:page>'], type='http', auth='user', website=True)
    def portal_my_asset_allocations(self, page=1, filterby=None, **kw):
        user = request.env.user
        partner = user.partner_id
        Allocation = request.env['hr.asset.allocation'].sudo()

        # If user is HR Manager/Officer, allow seeing all; otherwise restrict to their head assignments
        if user.has_group('hr.group_hr_user'):
            domain = []
        else:
            domain = ['|', ('department_head_id', '=', user.id), ('partner_id', '=', partner.id)]

        if filterby == 'pending':
            domain.append(('state', '=', 'pending'))
        elif filterby == 'approved':
            domain.append(('state', '=', 'approved'))

        total = Allocation.search_count(domain)
        pager_data = pager(
            url="/my/asset_allocations",
            url_args={'filterby': filterby} if filterby else {},
            total=total,
            page=page,
            step=12
        )

        allocations = Allocation.search(
            domain,
            order='state asc, id desc',
            limit=12,
            offset=pager_data['offset']
        )

        values = {
            'allocations': allocations,
            'page_name': 'asset_allocations',
            'pager': pager_data,
            'filterby': filterby or 'all',
            'default_url': '/my/asset_allocations',
        }
        return request.render('aesl_hr_asset_allocation.portal_my_asset_allocations', values)

    @http.route(['/my/asset_allocation/<int:allocation_id>'], type='http', auth='user', website=True)
    def portal_my_asset_allocation_detail(self, allocation_id, **kw):
        user = request.env.user
        partner = user.partner_id
        Allocation = request.env['hr.asset.allocation'].sudo()

        allocation = Allocation.browse(allocation_id)
        if not allocation.exists():
            raise NotFound()

        # Security check: must be assigned head or HR officer
        is_hr = user.has_group('hr.group_hr_user')
        is_assigned = (allocation.department_head_id.id == user.id or allocation.partner_id.id == partner.id)
        if not is_hr and not is_assigned:
            raise Forbidden()

        joining_date = getattr(allocation.employee_id, 'appointment_date', False) or (
            allocation.employee_id.create_date.strftime('%Y-%m-%d') if allocation.employee_id.create_date else '-'
        )

        values = {
            'allocation': allocation,
            'employee': allocation.employee_id,
            'joining_date': str(joining_date) if joining_date else '-',
            'page_name': 'asset_allocation_detail',
            'is_hr': is_hr,
            'is_assigned': is_assigned,
            'saved': kw.get('saved'),
            'approved': kw.get('approved'),
        }
        return request.render('aesl_hr_asset_allocation.portal_asset_allocation_detail', values)

    @http.route(['/my/asset_allocation/<int:allocation_id>/submit'], type='http', auth='user', methods=['POST'], website=True, csrf=True)
    def portal_my_asset_allocation_submit(self, allocation_id, **post):
        user = request.env.user
        partner = user.partner_id
        Allocation = request.env['hr.asset.allocation'].sudo()

        allocation = Allocation.browse(allocation_id)
        if not allocation.exists():
            raise NotFound()

        is_hr = user.has_group('hr.group_hr_user')
        is_assigned = (allocation.department_head_id.id == user.id or allocation.partner_id.id == partner.id)
        if not is_hr and not is_assigned:
            raise Forbidden()

        # Update checklist lines
        for line in allocation.line_ids:
            is_alloc = bool(post.get(f'line_allocated_{line.id}'))
            details = post.get(f'line_details_{line.id}', '').strip()
            line_remarks = post.get(f'line_remarks_{line.id}', '').strip()
            line.write({
                'is_allocated': is_alloc,
                'asset_details': details,
                'remarks': line_remarks,
            })

        # Update overall remarks
        overall_remarks = post.get('remarks', '').strip()
        allocation.write({'remarks': overall_remarks})

        # Process action
        action_type = post.get('action')
        if action_type == 'approve':
            allocation.action_approve()
            return request.redirect(f'/my/asset_allocation/{allocation.id}?approved=1')

        return request.redirect(f'/my/asset_allocation/{allocation.id}?saved=1')

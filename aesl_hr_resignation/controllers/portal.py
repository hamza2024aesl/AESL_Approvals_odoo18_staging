# -*- coding: utf-8 -*-

from odoo import http, fields, _
from odoo.addons.portal.controllers.portal import CustomerPortal, pager
from odoo.http import request
from werkzeug.exceptions import Forbidden, NotFound


class EmployeeResignationPortal(CustomerPortal):

    def _get_current_employee(self):
        user = request.env.user
        return request.env['hr.employee'].sudo().search([('user_id', '=', user.id)], limit=1)

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        user = request.env.user
        employee = self._get_current_employee()

        Resignation = request.env['employee.resignation'].sudo()

        if employee:
            if 'resignation_count' in counters:
                values['resignation_count'] = Resignation.search_count([('emp_name', '=', employee.id)])

            # Check if user is a manager with reporting subordinates
            is_manager = request.env['hr.employee'].sudo().search_count([('parent_id', '=', employee.id)]) > 0
            values['is_resignation_manager'] = is_manager

            if is_manager:
                team_domain = [('immediate_boss', '=', employee.id)]
                if 'team_resignation_count' in counters:
                    values['team_resignation_count'] = Resignation.search_count(team_domain)

                pending_team = Resignation.search([
                    ('immediate_boss', '=', employee.id),
                    ('state', 'in', ['pending_manager', 'revoke_pending'])
                ])
                values['pending_team_resignations'] = pending_team
                values['pending_team_resignation_count'] = len(pending_team)
        else:
            values['resignation_count'] = 0
            values['is_resignation_manager'] = False
            values['pending_team_resignation_count'] = 0

        # Department Head (Admin, IT, HSE) & HR Portal Values (Requirement 1.1)
        company = user.company_id or request.env.company
        is_dept_head = user.id in [
            company.asset_admin_head_id.id,
            company.asset_it_head_id.id,
            company.asset_hse_head_id.id
        ]
        is_hr = user.has_group('hr.group_hr_user')
        values['is_department_head'] = is_dept_head
        values['is_hr_user'] = is_hr

        Clearance = request.env['employee.resignation.clearance'].sudo()
        if is_dept_head or is_hr:
            clearance_domain = [] if is_hr else [('department_head_id', '=', user.id)]
            if 'clearance_count' in counters:
                values['clearance_count'] = Clearance.search_count(clearance_domain)
            pending_domain = clearance_domain + [('state', '=', 'pending')]
            values['pending_clearance_count'] = Clearance.search_count(pending_domain)
        else:
            values['clearance_count'] = 0
            values['pending_clearance_count'] = 0

        return values

    # ----------------------------------------------------
    # 1. RESIGNATIONS LIST VIEW (/my/resignations)
    # ----------------------------------------------------

    @http.route(['/my/resignations', '/my/resignations/page/<int:page>'], type='http', auth='user', website=True)
    def portal_my_resignations(self, page=1, tab='my', **kw):
        user = request.env.user
        employee = self._get_current_employee()
        Resignation = request.env['employee.resignation'].sudo()

        if not employee:
            values = self._prepare_portal_layout_values()
            values.update({
                'no_employee': True,
                'page_name': 'resignations',
            })
            return request.render("aesl_hr_resignation.portal_my_resignations_list", values)

        # Check if current user is a reporting manager
        is_manager = request.env['hr.employee'].sudo().search_count([('parent_id', '=', employee.id)]) > 0

        # Domain based on tab
        if tab == 'team' and is_manager:
            domain = [('immediate_boss', '=', employee.id)]
        else:
            tab = 'my'
            domain = [('emp_name', '=', employee.id)]

        total = Resignation.search_count(domain)
        pager_data = pager(
            url="/my/resignations",
            url_args={'tab': tab},
            total=total,
            page=page,
            step=10
        )

        resignations = Resignation.search(
            domain,
            order="create_date desc",
            limit=10,
            offset=pager_data['offset']
        )

        active_resignation = Resignation.search([
            ('emp_name', '=', employee.id),
            ('state', 'in', ['draft', 'pending_manager', 'serving_notice', 'clearance_in_progress', 'revoke_pending'])
        ], limit=1)

        values = self._prepare_portal_layout_values()
        values.update({
            'resignations': resignations,
            'page_name': 'resignations',
            'pager': pager_data,
            'default_url': '/my/resignations',
            'current_tab': tab,
            'is_manager': is_manager,
            'has_active_resignation': bool(active_resignation),
            'active_resignation_id': active_resignation.id if active_resignation else False,
        })
        return request.render("aesl_hr_resignation.portal_my_resignations_list", values)

    # ----------------------------------------------------
    # 2. NEW RESIGNATION SUBMISSION FORM (/my/resignation/new)
    # ----------------------------------------------------

    @http.route('/my/resignation/new', type='http', auth='user', website=True)
    def portal_my_resignation_new(self, **kw):
        employee = self._get_current_employee()
        if not employee:
            return request.render("aesl_hr_resignation.portal_resignation_error", {
                'error_title': _("No Employee Profile"),
                'error_message': _("Your user account is not linked to an employee profile. Please contact HR.")
            })

        Resignation = request.env['employee.resignation'].sudo()
        active = Resignation.search([
            ('emp_name', '=', employee.id),
            ('state', 'in', ['pending_manager', 'serving_notice', 'clearance_in_progress', 'revoke_pending'])
        ], limit=1)

        if active:
            return request.redirect(f'/my/resignation/{active.id}?warning=active_exists')

        today_date = fields.Date.today()
        values = self._prepare_portal_layout_values()
        values.update({
            'page_name': 'resignation_new',
            'employee': employee,
            'today_date': today_date,
            'error_msg': kw.get('error'),
        })
        return request.render("aesl_hr_resignation.portal_resignation_new_form", values)

    # ----------------------------------------------------
    # 3. SUBMIT FORM HANDLER (/my/resignation/submit)
    # ----------------------------------------------------

    @http.route('/my/resignation/submit', type='http', auth='user', methods=['POST'], website=True, csrf=True)
    def portal_my_resignation_submit(self, **kw):
        employee = self._get_current_employee()
        if not employee:
            raise Forbidden(_("Unauthorized"))

        reason = kw.get('reason', '').strip()
        notice_period_duration = kw.get('notice_period_duration', '1_month')
        notice_period_custom_days = int(kw.get('notice_period_custom_days', 30) or 30)
        resignation_date_str = kw.get('resignation_date')

        if not reason:
            return request.redirect('/my/resignation/new?error=reason_required')

        res_date = fields.Date.from_string(resignation_date_str) if resignation_date_str else fields.Date.today()

        Resignation = request.env['employee.resignation'].sudo()
        existing = Resignation.search([('emp_name', '=', employee.id)], limit=1)

        vals = {
            'resignation_date': res_date,
            'notice_period_duration': notice_period_duration,
            'notice_period_custom_days': notice_period_custom_days,
            'reason': reason,
            'leaving_status': 'resignation',
            'is_revoked': False,
            'revoke_reason': False,
            'revoke_date': False,
            'revoke_response_remarks': False,
            'rejection_reason': False,
            'manager_remarks': False,
        }

        if existing:
            existing.write(vals)
            record = existing
        else:
            vals['emp_name'] = employee.id
            vals['company_id'] = employee.company_id.id
            record = Resignation.create(vals)

        record.action_submit()

        return request.redirect(f'/my/resignation/{record.id}?submitted=1')

    # ----------------------------------------------------
    # 4. RESIGNATION DETAIL VIEW (/my/resignation/<id>)
    # ----------------------------------------------------

    @http.route('/my/resignation/<int:resignation_id>', type='http', auth='user', website=True)
    def portal_my_resignation_detail(self, resignation_id, **kw):
        user = request.env.user
        employee = self._get_current_employee()
        resignation = request.env['employee.resignation'].sudo().browse(resignation_id)

        if not resignation.exists():
            raise NotFound()

        # Authorization: Must be the employee, or immediate boss, or HR user
        is_employee = (employee and resignation.emp_name.id == employee.id) or (resignation.employee_user_id.id == user.id)
        is_manager = (employee and resignation.immediate_boss.id == employee.id) or (resignation.manager_user_id.id == user.id)
        is_hr = user.has_group('hr.group_hr_user')

        if not (is_employee or is_manager or is_hr):
            raise Forbidden(_("You are not authorized to view this resignation request."))

        can_revoke = is_employee and resignation.state in ['serving_notice', 'clearance_in_progress']
        can_review_resignation = (is_manager or is_hr) and resignation.state == 'pending_manager'
        can_review_revoke = (is_manager or is_hr) and resignation.state == 'revoke_pending'
        can_do_exit_interview = is_hr and resignation.state == 'exit_interview_pending'
        can_archive = is_hr and resignation.state == 'exit_interview_done'

        values = self._prepare_portal_layout_values()
        values.update({
            'resignation': resignation,
            'page_name': 'resignation_detail',
            'is_employee': is_employee,
            'is_manager': is_manager,
            'is_hr': is_hr,
            'can_revoke': can_revoke,
            'can_review_resignation': can_review_resignation,
            'can_review_revoke': can_review_revoke,
            'can_do_exit_interview': can_do_exit_interview,
            'can_archive': can_archive,
            'msg_submitted': kw.get('submitted'),
            'msg_warning': kw.get('warning'),
            'msg_success': kw.get('success'),
            'msg_error': kw.get('error'),
        })
        return request.render("aesl_hr_resignation.portal_resignation_detail_view", values)

    # ----------------------------------------------------
    # 5. RESIGNATION ACTION HANDLER (/my/resignation/<id>/action)
    # ----------------------------------------------------

    @http.route('/my/resignation/<int:resignation_id>/action', type='http', auth='user', methods=['POST'], website=True, csrf=True)
    def portal_my_resignation_action(self, resignation_id, **kw):
        user = request.env.user
        employee = self._get_current_employee()
        resignation = request.env['employee.resignation'].sudo().browse(resignation_id)

        if not resignation.exists():
            raise NotFound()

        action = kw.get('action')
        remarks = kw.get('remarks', '').strip()
        revoke_reason = kw.get('revoke_reason', '').strip()

        is_employee = (employee and resignation.emp_name.id == employee.id) or (resignation.employee_user_id.id == user.id)
        is_manager = (employee and resignation.immediate_boss.id == employee.id) or (resignation.manager_user_id.id == user.id)
        is_hr = user.has_group('hr.group_hr_user')

        # 1. Manager Accept
        if action == 'manager_accept':
            if not (is_manager or is_hr):
                raise Forbidden(_("Unauthorized"))
            resignation.action_manager_accept(remarks=remarks)
            return request.redirect(f'/my/resignation/{resignation.id}?success=accepted')

        # 2. Manager Reject (Requires Remarks)
        elif action == 'manager_reject':
            if not (is_manager or is_hr):
                raise Forbidden(_("Unauthorized"))
            if not remarks:
                return request.redirect(f'/my/resignation/{resignation.id}?error=rejection_remarks_required')
            resignation.action_manager_reject(remarks=remarks)
            return request.redirect(f'/my/resignation/{resignation.id}?success=rejected')

        # 3. Employee Request Revoke
        elif action == 'request_revoke':
            if not is_employee:
                raise Forbidden(_("Only the employee can request to revoke their resignation."))
            if not revoke_reason:
                return request.redirect(f'/my/resignation/{resignation.id}?error=revoke_reason_required')
            resignation.action_request_revoke(reason=revoke_reason)
            return request.redirect(f'/my/resignation/{resignation.id}?success=revoke_requested')

        # 4. Manager Accept Revoke
        elif action == 'accept_revoke':
            if not (is_manager or is_hr):
                raise Forbidden(_("Unauthorized"))
            resignation.action_manager_accept_revoke(remarks=remarks)
            return request.redirect(f'/my/resignation/{resignation.id}?success=revoke_accepted')

        # 5. Manager Reject Revoke
        elif action == 'reject_revoke':
            if not (is_manager or is_hr):
                raise Forbidden(_("Unauthorized"))
            resignation.action_manager_reject_revoke(remarks=remarks)
            return request.redirect(f'/my/resignation/{resignation.id}?success=revoke_rejected')

        # 6. HR Complete Exit Interview (Requirement 2)
        elif action == 'done_exit_interview':
            if not is_hr:
                raise Forbidden(_("Only HR personnel can complete the Exit Interview."))
            reason_leaving = kw.get('exit_interview_reason_for_leaving')
            feedback = kw.get('exit_interview_feedback', '').strip()
            notes = kw.get('exit_interview_notes', '').strip()
            resignation.write({
                'exit_interview_reason_for_leaving': reason_leaving,
                'exit_interview_feedback': feedback,
                'exit_interview_notes': notes,
            })
            resignation.action_done_exit_interview()
            return request.redirect(f'/my/resignation/{resignation.id}?success=interview_done')

        # 7. HR Archive Employee & User (Requirement 3)
        elif action == 'archive_employee':
            if not is_hr:
                raise Forbidden(_("Only HR personnel can archive the employee."))
            resignation.action_archive_employee_and_user()
            return request.redirect(f'/my/resignation/{resignation.id}?success=archived')

        return request.redirect(f'/my/resignation/{resignation.id}')

    # ----------------------------------------------------
    # 6. DEPARTMENT CLEARANCES LIST (/my/clearances)
    # Requirement 1.1: Visible only to Admin, IT, HSE heads and HR
    # ----------------------------------------------------

    @http.route(['/my/clearances', '/my/clearances/page/<int:page>'], type='http', auth='user', website=True)
    def portal_my_clearances(self, page=1, **kw):
        user = request.env.user
        company = user.company_id or request.env.company
        is_dept_head = user.id in [
            company.asset_admin_head_id.id,
            company.asset_it_head_id.id,
            company.asset_hse_head_id.id
        ]
        is_hr = user.has_group('hr.group_hr_user')

        if not (is_dept_head or is_hr):
            raise Forbidden(_("Access denied: You are not a designated Admin, IT, or HSE department head."))

        Clearance = request.env['employee.resignation.clearance'].sudo()
        domain = [] if is_hr else [('department_head_id', '=', user.id)]

        total = Clearance.search_count(domain)
        pager_data = pager(
            url="/my/clearances",
            total=total,
            page=page,
            step=10
        )

        clearances = Clearance.search(
            domain,
            order="state asc, id desc",
            limit=10,
            offset=pager_data['offset']
        )

        values = self._prepare_portal_layout_values()
        values.update({
            'clearances': clearances,
            'page_name': 'clearances',
            'pager': pager_data,
            'default_url': '/my/clearances',
        })
        return request.render("aesl_hr_resignation.portal_my_clearances_list", values)

    # ----------------------------------------------------
    # 7. DEPARTMENT CLEARANCE DETAIL & CHECKLIST (/my/clearance/<id>)
    # Requirement 1.2: Department-wise Asset View
    # ----------------------------------------------------

    @http.route('/my/clearance/<int:clearance_id>', type='http', auth='user', website=True)
    def portal_my_clearance_detail(self, clearance_id, **kw):
        user = request.env.user
        Clearance = request.env['employee.resignation.clearance'].sudo()
        clearance = Clearance.browse(clearance_id)

        if not clearance.exists():
            raise NotFound()

        is_assigned = (clearance.department_head_id.id == user.id)
        is_hr = user.has_group('hr.group_hr_user')

        if not (is_assigned or is_hr):
            raise Forbidden(_("Access denied: You can only view your own department's clearance assets."))

        values = self._prepare_portal_layout_values()
        values.update({
            'clearance': clearance,
            'page_name': 'clearance_detail',
            'is_assigned': is_assigned,
            'is_hr': is_hr,
            'msg_approved': kw.get('approved'),
        })
        return request.render("aesl_hr_resignation.portal_clearance_detail_view", values)

    # ----------------------------------------------------
    # 8. SUBMIT DEPARTMENT CLEARANCE (/my/clearance/<id>/submit)
    # Requirement 1.3: Uncheck returned assets + remarks + approve
    # ----------------------------------------------------

    @http.route('/my/clearance/<int:clearance_id>/submit', type='http', auth='user', methods=['POST'], website=True, csrf=True)
    def portal_my_clearance_submit(self, clearance_id, **post):
        user = request.env.user
        Clearance = request.env['employee.resignation.clearance'].sudo()
        clearance = Clearance.browse(clearance_id)

        if not clearance.exists():
            raise NotFound()

        is_assigned = (clearance.department_head_id.id == user.id)
        is_hr = user.has_group('hr.group_hr_user')

        if not (is_assigned or is_hr):
            raise Forbidden(_("Unauthorized"))

        # Update checklist lines: uncheck returned assets, save details & remarks
        for line in clearance.line_ids:
            # Checkbox: if checked, employee still holds it; if unchecked, item is returned!
            still_allocated = bool(post.get(f'line_allocated_{line.id}'))
            details = post.get(f'line_details_{line.id}', '').strip()
            line_remarks = post.get(f'line_remarks_{line.id}', '').strip()
            line.write({
                'is_allocated': still_allocated,
                'asset_details': details,
                'remarks': line_remarks,
            })

        # Save overall department remarks
        overall_remarks = post.get('remarks', '').strip()

        # Approve clearance
        clearance.action_approve(remarks=overall_remarks)

        return request.redirect(f'/my/clearance/{clearance.id}?approved=1')

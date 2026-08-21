# -*- coding: utf-8 -*-

from odoo import http, _
from odoo.addons.portal.controllers.portal import CustomerPortal, pager
from odoo.http import request

class EmployeeSurveyPortal(CustomerPortal):

    @http.route('/survey/open/<string:access_token>', type='http', auth='user', website=True)
    def survey_open_smart_redirect(self, access_token, **kwargs):
        """
        Smart Redirect Route:
        - Ensures user is logged in (auth='user').
        - Binds recipient partner_id to prevent 'answer_wrong_user' access errors.
        - Internal Users (base.group_user) -> opens internal survey fill form.
        - Portal Users -> opens /my/surveys portal menu where form is listed to Fill & Submit.
        """
        user = request.env.user
        partner = user.partner_id
        user_input = request.env['survey.user_input'].sudo().search([('access_token', '=', access_token)], limit=1)

        if not user_input:
            return request.redirect('/my/surveys')

        # Auto-assign partner_id if missing or matching logged-in user to prevent access blocks
        if not user_input.partner_id:
            user_input.sudo().write({'partner_id': partner.id})
        elif user_input.partner_id != partner:
            own_input = request.env['survey.user_input'].sudo().search([
                ('survey_id', '=', user_input.survey_id.id),
                ('partner_id', '=', partner.id),
                ('state', 'in', ['new', 'in_progress'])
            ], limit=1)
            if own_input:
                user_input = own_input
            else:
                user_input.sudo().write({'partner_id': partner.id})

        if user.has_group('base.group_user'):
            # Internal User -> Open internal survey fill form
            return request.redirect(user_input.get_start_url())
        else:
            # Portal User -> Open /my/surveys portal menu where form is listed to Fill & Submit
            return request.redirect('/my/surveys')

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id

        if 'survey_count' in counters:
            values['survey_count'] = request.env['survey.user_input'].sudo().search_count([
                ('partner_id', '=', partner.id)
            ])

        # Add pending surveys for portal notification banner
        if partner:
            pending_surveys = request.env['survey.user_input'].sudo().search([
                ('partner_id', '=', partner.id),
                ('state', 'in', ['new', 'in_progress'])
            ])
            values['pending_surveys'] = pending_surveys
            values['pending_survey_count'] = len(pending_surveys)

        return values

    @http.route(['/my/surveys', '/my/surveys/page/<int:page>'], type='http', auth='user', website=True)
    def portal_my_surveys(self, page=1, **kw):
        partner = request.env.user.partner_id
        SurveyInput = request.env['survey.user_input']
        domain = [('partner_id', '=', partner.id)]

        total_surveys = SurveyInput.sudo().search_count(domain)
        pager_data = pager(
            url="/my/surveys",
            total=total_surveys,
            page=page,
            step=10
        )
        surveys = SurveyInput.sudo().search(
            domain,
            order="create_date desc",
            limit=10,
            offset=pager_data['offset']
        )
        values = self._prepare_portal_layout_values()
        values.update({
            'surveys': surveys,
            'page_name': 'survey',
            'pager': pager_data,
            'default_url': '/my/surveys',
        })
        return request.render("aesl_employee_survey.portal_my_surveys_list", values)

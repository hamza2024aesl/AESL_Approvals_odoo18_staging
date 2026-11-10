# -*- coding: utf-8 -*-

from markupsafe import Markup
from odoo import http, fields, _
from odoo.addons.portal.controllers.portal import CustomerPortal, pager
from odoo.http import request
from werkzeug.exceptions import Forbidden, NotFound


class OfferLetterPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        user = request.env.user
        OfferLetter = request.env['hr.offer.letter'].sudo()

        # Check if the current user is an assigned director on any offer letter
        is_director = OfferLetter.search_count([('intimate_director_ids', 'in', [user.id])]) > 0
        values['is_director_approver'] = is_director

        if is_director:
            total_offers = OfferLetter.search_count([('intimate_director_ids', 'in', [user.id])])
            if 'director_offers_count' in counters:
                values['director_offers_count'] = total_offers

            pending_offers = OfferLetter.search([
                ('intimate_director_ids', 'in', [user.id]),
                ('approved_director_ids', 'not in', [user.id]),
                ('state', '=', 'pending_director'),
            ])
            values['pending_director_offers'] = pending_offers
            values['pending_director_offers_count'] = len(pending_offers)
            values['director_offers_count'] = total_offers
        else:
            values['director_offers_count'] = 0
            values['pending_director_offers_count'] = 0

        return values

    # ---------------------------------------------------------
    # 1. CANDIDATE PORTAL / RESPONSE ROUTES
    # ---------------------------------------------------------

    @http.route('/offer/respond/<string:token>', type='http', auth='public', methods=['GET', 'POST'], csrf=False, website=True)
    def offer_respond(self, token, action=None, **kw):
        """Candidate response route from email buttons (Accept / Reject)."""
        offer = request.env['hr.offer.letter'].sudo().search([('access_token', '=', token)], limit=1)
        if not offer:
            return request.render('aesl_hr_offer_letter.portal_offer_not_found', {})

        # 1. ACTION: ACCEPT
        if action == 'accept':
            if offer.state == 'sent':
                if offer.intimate_director_ids:
                    offer.sudo().write({
                        'state': 'pending_director',
                        'response_date': fields.Datetime.now(),
                    })
                    offer.sudo()._send_director_notification()
                    offer.sudo().message_post(
                        body=Markup(
                            "<p style='color: green;'><strong>🎉 Offer Accepted by Candidate</strong></p>"
                            "<p>The candidate <strong>%s</strong> accepted the employment offer via email link on %s.</p>"
                            "<p>Status updated to <strong>Pending Director Approval</strong>.</p>"
                            "<p>Approval notification emails dispatched to intimate directors: <strong>%s</strong>.</p>"
                        ) % (
                            offer.candidate_name,
                            fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            ', '.join(offer.intimate_director_ids.mapped('name'))
                        )
                    )
                else:
                    offer.sudo().write({
                        'state': 'approved_director',
                        'response_date': fields.Datetime.now(),
                    })
                    offer.sudo().message_post(
                        body=Markup(
                            "<p style='color: green;'><strong>🎉 Offer Accepted by Candidate</strong></p>"
                            "<p>The candidate <strong>%s</strong> accepted the employment offer via email link on %s.</p>"
                            "<p>No intimate directors were assigned. Ready for <strong>Create Employee</strong>.</p>"
                        ) % (offer.candidate_name, fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                    )

                # Automatically send Onboarding Document Request Email to candidate
                offer.sudo().action_send_document_request()
            values = {
                'offer': offer,
                'already_processed': offer.state in ['accepted', 'pending_director', 'approved_director', 'done'] and action != 'accept',
            }
            return request.render('aesl_hr_offer_letter.portal_offer_accepted', values)

        # 2. ACTION: REJECT
        elif action == 'reject':
            if request.httprequest.method == 'POST':
                reason = kw.get('rejection_reason', '').strip()
                if offer.state in ['sent', 'draft']:
                    offer.sudo().write({
                        'state': 'rejected',
                        'rejection_reason': reason,
                        'response_date': fields.Datetime.now(),
                    })
                    offer.sudo().message_post(
                        body=Markup(
                            "<p style='color: #c92a2a;'><strong>❌ Offer Rejected by Candidate</strong></p>"
                            "<p>Candidate <strong>%s</strong> rejected the offer on %s.</p>"
                            "<p><strong>Reason / Feedback provided:</strong><br/>%s</p>"
                            "<p>The offer form is now ready for revision by HR.</p>"
                        ) % (offer.candidate_name, fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S'), reason or 'No specific reason provided.')
                    )
                return request.render('aesl_hr_offer_letter.portal_offer_rejected_done', {'offer': offer})

            # GET request: Show rejection confirmation & feedback form
            return request.render('aesl_hr_offer_letter.portal_offer_reject_form', {'offer': offer, 'token': token})

        # Default fallback view
        return request.render('aesl_hr_offer_letter.portal_offer_summary', {'offer': offer, 'token': token})

    @http.route('/offer/download/<string:token>', type='http', auth='public', website=True)
    def offer_download_pdf(self, token, **kw):
        """Allows candidate to view and download their official PDF Offer Letter."""
        offer = request.env['hr.offer.letter'].sudo().search([('access_token', '=', token)], limit=1)
        if not offer:
            return request.not_found()

        pdf_content, _report_type = request.env['ir.actions.report'].sudo()._render_qweb_pdf('aesl_hr_offer_letter.action_report_hr_offer_letter', [offer.id])

        filename = f"Offer_Letter_{offer.candidate_name.replace(' ', '_')}.pdf"
        pdfhttpheaders = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(pdf_content)),
            ('Content-Disposition', f'inline; filename="{filename}"'),
        ]
        return request.make_response(pdf_content, headers=pdfhttpheaders)

    # ---------------------------------------------------------
    # 2. DIRECTOR PORTAL APPROVAL ROUTES
    # ---------------------------------------------------------

    @http.route(['/my/director-offers', '/my/director-offers/page/<int:page>'], type='http', auth='user', website=True)
    def portal_my_director_offers(self, page=1, filter_status='all', **kw):
        """List view in Director Portal of all candidate onboarding requests assigned to the director."""
        user = request.env.user
        OfferLetter = request.env['hr.offer.letter'].sudo()

        domain = [('intimate_director_ids', 'in', [user.id])]
        if filter_status == 'pending':
            domain += [('approved_director_ids', 'not in', [user.id]), ('state', '=', 'pending_director')]
        elif filter_status == 'approved':
            domain += [('approved_director_ids', 'in', [user.id])]

        total = OfferLetter.search_count(domain)
        page_size = 15
        pager_data = pager(
            url="/my/director-offers",
            url_args={'filter_status': filter_status},
            total=total,
            page=page,
            step=page_size
        )
        offers = OfferLetter.search(domain, limit=page_size, offset=(page - 1) * page_size, order='id desc')

        values = self._prepare_portal_layout_values()
        values.update({
            'offers': offers,
            'page_name': 'director_offers',
            'pager': pager_data,
            'filter_status': filter_status,
            'user': user,
        })
        return request.render('aesl_hr_offer_letter.portal_my_director_offers_list', values)

    @http.route('/my/director-offers/<int:offer_id>', type='http', auth='user', website=True)
    def portal_director_offer_detail(self, offer_id, **kw):
        """
        Restricted Director View:
        Shows ONLY Candidate Profile and Salary & Compensation.
        Read-only, except for the Approve button.
        """
        user = request.env.user
        offer = request.env['hr.offer.letter'].sudo().browse(offer_id)
        if not offer.exists():
            return request.not_found()

        # Security check: User must be an assigned director or HR user
        is_director = user.id in offer.intimate_director_ids.ids
        is_hr = user.has_group('hr.group_hr_user')
        if not (is_director or is_hr):
            raise Forbidden()

        values = self._prepare_portal_layout_values()
        has_approved = user.id in offer.approved_director_ids.ids
        can_approve = is_director and (not has_approved) and (offer.state == 'pending_director')

        values.update({
            'offer': offer,
            'page_name': 'director_offer_detail',
            'user': user,
            'is_director': is_director,
            'has_approved': has_approved,
            'can_approve': can_approve,
            'success_msg': kw.get('approved') == '1',
        })
        return request.render('aesl_hr_offer_letter.portal_director_offer_detail', values)

    @http.route('/my/director-offers/<int:offer_id>/approve', type='http', auth='user', methods=['POST'], website=True)
    def portal_director_offer_approve(self, offer_id, **kw):
        """Director Approval POST Handler."""
        user = request.env.user
        offer = request.env['hr.offer.letter'].sudo().browse(offer_id)
        if not offer.exists():
            return request.not_found()

        if user.id not in offer.intimate_director_ids.ids:
            raise Forbidden()

        if offer.state == 'pending_director' and user.id not in offer.approved_director_ids.ids:
            offer.action_director_approve(director_user=user)

        return request.redirect(f'/my/director-offers/{offer_id}?approved=1')

    @http.route('/offer/director-review/<string:token>', type='http', auth='public', website=True)
    def offer_director_review_token(self, token, **kw):
        """Direct token link from email for Directors to jump straight to their review page."""
        offer = request.env['hr.offer.letter'].sudo().search([('access_token', '=', token)], limit=1)
        if not offer:
            return request.render('aesl_hr_offer_letter.portal_offer_not_found', {})

        # If user is not logged in, redirect to login with redirect back to this offer
        if request.env.user._is_public():
            return request.redirect(f'/web/login?redirect=/my/director-offers/{offer.id}')

        return request.redirect(f'/my/director-offers/{offer.id}')

    # ---------------------------------------------------------
    # 3. CANDIDATE DOCUMENT UPLOAD ROUTES
    # ---------------------------------------------------------

    @http.route('/offer/documents/<string:token>', type='http', auth='public', methods=['GET'], website=True)
    def offer_documents_form(self, token, **kw):
        """Web portal upload page for candidate to upload the 6 mandatory onboarding documents."""
        offer = request.env['hr.offer.letter'].sudo().search([('access_token', '=', token)], limit=1)
        if not offer:
            return request.render('aesl_hr_offer_letter.portal_offer_not_found', {})

        values = {
            'offer': offer,
            'token': token,
            'success_msg': kw.get('submitted') == '1',
        }
        return request.render('aesl_hr_offer_letter.portal_candidate_documents_upload', values)

    @http.route('/offer/documents/<string:token>/submit', type='http', auth='public', methods=['POST'], website=True, csrf=False)
    def offer_documents_submit(self, token, **kw):
        """Processes multipart document uploads from candidate web portal."""
        import base64
        offer = request.env['hr.offer.letter'].sudo().search([('access_token', '=', token)], limit=1)
        if not offer:
            return request.render('aesl_hr_offer_letter.portal_offer_not_found', {})

        files_uploaded = []
        doc_fields_map = [
            ('doc_picture', 'doc_picture_filename', 'Picture'),
            ('doc_cnic', 'doc_cnic_filename', 'CNIC'),
            ('doc_resignation', 'doc_resignation_filename', 'Resignation Acceptance Letter'),
            ('doc_education', 'doc_education_filename', 'Educational Documents'),
            ('doc_certification', 'doc_certification_filename', 'Certification Documents'),
            ('doc_professional', 'doc_professional_filename', 'Professional Documents'),
        ]

        vals = {}
        for field_name, fname_field, cat_name in doc_fields_map:
            file_item = request.httprequest.files.get(field_name)
            if file_item and file_item.filename:
                file_content = file_item.read()
                if file_content:
                    b64_data = base64.b64encode(file_content)
                    vals[field_name] = b64_data
                    vals[fname_field] = file_item.filename

                    # Also create ir.attachment and sync to Documents module
                    attachment = request.env['ir.attachment'].sudo().create({
                        'name': file_item.filename,
                        'datas': b64_data,
                        'mimetype': file_item.content_type,
                        'res_model': 'hr.offer.letter',
                        'res_id': offer.id,
                    })
                    offer._sync_attachment_to_documents_app(attachment, cat_name)
                    files_uploaded.append(f"{cat_name}: {file_item.filename}")

        if vals:
            vals['docs_received_date'] = fields.Datetime.now()
            offer.sudo().write(vals)
            offer.sudo().message_post(body=Markup(
                "<p style='color: #198754;'><strong>📥 Candidate Uploaded Onboarding Documents Online:</strong></p>"
                "<ul>" + "".join([f"<li>{item}</li>" for item in files_uploaded]) + "</ul>"
                "<p>Total Documents: <strong>%s / 6 Received</strong>. Uploaded to Documents module.</p>"
            ) % offer.docs_received_count)

        return request.redirect(f'/offer/documents/{token}?submitted=1')

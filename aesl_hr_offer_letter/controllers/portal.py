# -*- coding: utf-8 -*-

from odoo import http, fields, _
from odoo.http import request


class OfferLetterPortal(http.Controller):

    @http.route('/offer/respond/<string:token>', type='http', auth='public', website=True, csrf=False)
    def offer_respond(self, token, action=None, **kw):
        """Candidate response route from email buttons (Accept / Reject)."""
        offer = request.env['hr.offer.letter'].sudo().search([('access_token', '=', token)], limit=1)
        if not offer:
            return request.render('aesl_hr_offer_letter.portal_offer_not_found', {})

        # 1. ACTION: ACCEPT
        if action == 'accept':
            if offer.state == 'sent':
                offer.sudo().write({
                    'state': 'accepted',
                    'response_date': fields.Datetime.now(),
                })
                offer.sudo().message_post(
                    body=_(
                        "<p style='color: green;'><strong>🎉 Offer Accepted by Candidate</strong></p>"
                        "<p>The candidate <strong>%s</strong> has accepted the employment offer via email link on %s.</p>"
                        "<p>HR may now review and proceed with <strong>Create Employee</strong>.</p>"
                    ) % (offer.candidate_name, fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                )
            values = {
                'offer': offer,
                'already_processed': offer.state in ['accepted', 'done'] and action != 'accept',
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
                        body=_(
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

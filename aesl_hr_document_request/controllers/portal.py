# -*- coding: utf-8 -*-

import base64
import io
from PIL import Image

from odoo import http, fields, _
from odoo.addons.portal.controllers.portal import CustomerPortal, pager
from odoo.http import request

class HrDocumentRequestPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id

        if 'doc_request_count' in counters:
            values['doc_request_count'] = request.env['hr.document.request'].sudo().search_count([
                ('partner_id', '=', partner.id)
            ])

        if partner:
            pending_requests = request.env['hr.document.request'].sudo().search([
                ('partner_id', '=', partner.id),
                ('state', '=', 'pending')
            ])
            values['pending_doc_requests'] = pending_requests
            values['pending_doc_request_count'] = len(pending_requests)

        return values

    @http.route(['/my/document_requests', '/my/document_requests/page/<int:page>'], type='http', auth='user', website=True)
    def portal_my_doc_requests(self, page=1, **kw):
        partner = request.env.user.partner_id
        DocRequest = request.env['hr.document.request']
        domain = [('partner_id', '=', partner.id)]

        total = DocRequest.sudo().search_count(domain)
        pager_data = pager(
            url="/my/document_requests",
            total=total,
            page=page,
            step=10
        )
        doc_requests = DocRequest.sudo().search(
            domain,
            order="create_date desc",
            limit=10,
            offset=pager_data['offset']
        )
        values = self._prepare_portal_layout_values()
        values.update({
            'doc_requests': doc_requests,
            'page_name': 'doc_request',
            'pager': pager_data,
            'default_url': '/my/document_requests',
        })
        return request.render("aesl_hr_document_request.portal_my_doc_requests_list", values)

    @http.route('/my/document_request/<int:req_id>', type='http', auth='user', website=True)
    def portal_my_doc_request_detail(self, req_id, **kw):
        partner = request.env.user.partner_id
        doc_req = request.env['hr.document.request'].sudo().browse(req_id)

        if not doc_req.exists() or doc_req.partner_id != partner:
            return request.redirect('/my/document_requests')

        values = self._prepare_portal_layout_values()
        values.update({
            'doc_req': doc_req,
            'page_name': 'doc_request',
        })
        return request.render("aesl_hr_document_request.portal_doc_request_form", values)

    @http.route('/my/document_request/submit', type='http', auth='user', methods=['POST'], website=True, csrf=True)
    def portal_doc_request_submit(self, req_id, **post):
        partner = request.env.user.partner_id
        doc_req = request.env['hr.document.request'].sudo().browse(int(req_id))

        if not doc_req.exists() or doc_req.partner_id != partner:
            return request.redirect('/my/document_requests')

        file_upload = post.get('attachment_file')
        signature_data = post.get('signature_data')
        signed_name = post.get('signed_by') or partner.name

        # Process uploaded file attachment
        attachment = False
        if file_upload and hasattr(file_upload, 'filename') and file_upload.filename:
            file_content = file_upload.read()
            attachment = request.env['ir.attachment'].sudo().create({
                'name': file_upload.filename,
                'datas': base64.b64encode(file_content),
                'res_model': 'hr.document.request',
                'res_id': doc_req.id,
            })
            doc_req.attachment_id = attachment.id

        # Process digital signature with solid white background conversion
        if signature_data and signature_data.startswith('data:image'):
            img_parts = signature_data.split(';base64,')
            base64_str = img_parts[1] if len(img_parts) > 1 else img_parts[0]

            try:
                img_bytes = base64.b64decode(base64_str)
                img = Image.open(io.BytesIO(img_bytes)).convert('RGBA')
                white_bg = Image.new('RGBA', img.size, (255, 255, 255, 255))
                composite = Image.alpha_composite(white_bg, img).convert('RGB')
                buf = io.BytesIO()
                composite.save(buf, format='PNG')
                base64_str = base64.b64encode(buf.getvalue()).decode('utf-8')
            except Exception:
                pass

            doc_req.write({
                'signature': base64_str,
                'signed_by': signed_name,
                'signed_on': fields.Datetime.now(),
            })

        # Update status to submitted and auto-create document in Documents App
        doc_req.write({'state': 'submitted'})
        doc_req.action_approve()

        return request.redirect(f'/my/document_request/{doc_req.id}?submitted=1')

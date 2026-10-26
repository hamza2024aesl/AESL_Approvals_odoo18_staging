import base64
import io
import logging
from markupsafe import Markup
from PIL import Image, ImageDraw
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from odoo.tools.pdf import PdfFileReader, PdfFileWriter
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class HrDocumentRequest(models.Model):
    _name = 'hr.document.request'
    _description = 'HR Employee Document Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Document Title', required=True, tracking=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Partner', compute='_compute_partner_id', store=True)
    user_id = fields.Many2one('res.users', string='Related User', compute='_compute_partner_id', store=True)
    
    instructions = fields.Text(string='Instructions / Description')
    deadline = fields.Date(string='Deadline')
    
    folder_id = fields.Many2one(
        'documents.document',
        string='Workspace / Folder',
        domain="[('type', '=', 'folder'), ('shortcut_document_id', '=', False)]",
        tracking=True
    )
    tag_ids = fields.Many2many('documents.tag', string='Tags')
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending Upload'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], string='Status', default='draft', tracking=True, required=True)
    
    attachment_id = fields.Many2one('ir.attachment', string='Uploaded Attachment', tracking=True)
    attachment_file = fields.Binary(related='attachment_id.datas', string='Attachment Data', readonly=False)
    attachment_name = fields.Char(related='attachment_id.name', string='Attachment Name', readonly=False)
    attachment_mimetype = fields.Char(related='attachment_id.mimetype', string='MIME Type')
    is_pdf = fields.Boolean(compute='_compute_file_type', string='Is PDF')
    is_image = fields.Boolean(compute='_compute_file_type', string='Is Image')
    
    signature = fields.Binary(string='Digital Signature', attachment=True)
    signed_by = fields.Char(string='Signed By')
    signed_on = fields.Datetime(string='Signed On')
    is_stamped = fields.Boolean(string='Signature Stamped on File', default=False)
    
    document_id = fields.Many2one('documents.document', string='Created Document', readonly=True)

    @api.depends('attachment_id', 'attachment_id.mimetype', 'attachment_name')
    def _compute_file_type(self):
        for rec in self:
            mimetype = (rec.attachment_id.mimetype or '').lower()
            name = (rec.attachment_name or '').lower()
            rec.is_pdf = 'pdf' in mimetype or name.endswith('.pdf')
            rec.is_image = any(img_ext in mimetype or name.endswith(img_ext) for img_ext in ['image', '.png', '.jpg', '.jpeg', '.webp'])

    @api.depends('employee_id', 'employee_id.user_id', 'employee_id.work_contact_id')
    def _compute_partner_id(self):
        for rec in self:
            if rec.employee_id:
                rec.user_id = rec.employee_id.user_id
                rec.partner_id = rec.employee_id.user_id.partner_id or rec.employee_id.work_contact_id
            else:
                rec.user_id = False
                rec.partner_id = False

    def action_download_attachment(self):
        self.ensure_one()
        if not self.attachment_id:
            raise UserError(_("No uploaded attachment found to download."))
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self.attachment_id.id}?download=true',
            'target': 'self',
        }

    def action_view_document(self):
        self.ensure_one()
        if not self.document_id:
            return
        return {
            'name': _('Document in Documents App'),
            'type': 'ir.actions.act_window',
            'res_model': 'documents.document',
            'view_mode': 'form',
            'res_id': self.document_id.id,
            'target': 'current',
        }

    def action_stamp_signature(self):
        """
        Physically merges/stamps the digital signature onto the uploaded file (PDF or Image).
        This guarantees that when viewed in Documents App previewer, PDF viewer, or downloaded,
        the signature is permanently visible at the bottom of the document.
        """
        for rec in self:
            if not rec.attachment_id or not rec.signature:
                continue

            try:
                file_bytes = rec.attachment_id.raw or base64.b64decode(rec.attachment_id.datas or b'')
                if not file_bytes:
                    continue

                sig_bytes = base64.b64decode(rec.signature)
                signer_name = rec.signed_by or (rec.employee_id.name if rec.employee_id else 'Employee')
                date_str = fields.Datetime.to_string(rec.signed_on or fields.Datetime.now())

                is_pdf = (rec.attachment_name or '').lower().endswith('.pdf') or 'pdf' in (rec.attachment_id.mimetype or '').lower()

                signed_bytes = False
                if is_pdf:
                    signed_bytes = self._stamp_pdf(file_bytes, sig_bytes, signer_name, date_str)
                    if signed_bytes:
                        rec.attachment_id.sudo().write({
                            'datas': base64.b64encode(signed_bytes),
                            'mimetype': 'application/pdf',
                        })
                else:
                    signed_bytes = self._stamp_image(file_bytes, sig_bytes, signer_name, date_str)
                    if signed_bytes:
                        rec.attachment_id.sudo().write({
                            'datas': base64.b64encode(signed_bytes),
                        })

                if signed_bytes:
                    rec.is_stamped = True
                    # Sync to Documents App if already created
                    if rec.document_id:
                        rec.document_id.sudo().write({
                            'attachment_id': rec.attachment_id.id,
                            'name': rec.name or rec.attachment_id.name,
                        })

            except Exception as e:
                _logger.error("Failed to stamp digital signature on document #%s: %s", rec.id, str(e), exc_info=True)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Signature Stamped"),
                'message': _("The digital signature has been successfully stamped onto the document!"),
                'type': 'success',
                'sticky': False,
            }
        }

    @api.model
    def _stamp_pdf(self, pdf_bytes, sig_bytes, signer_name, date_str):
        try:
            reader = PdfFileReader(io.BytesIO(pdf_bytes), strict=False)
            pages = list(reader.pages) if hasattr(reader, 'pages') else [reader.getPage(i) for i in range(reader.getNumPages())]
            if not pages:
                return False

            last_page = pages[-1]
            mediabox = getattr(last_page, 'mediabox', getattr(last_page, 'mediaBox', None))
            try:
                if hasattr(mediabox, 'width'):
                    page_w = float(abs(mediabox.width))
                    page_h = float(abs(mediabox.height))
                else:
                    page_w = float(abs(mediabox.getWidth()))
                    page_h = float(abs(mediabox.getHeight()))
            except Exception:
                page_w, page_h = 595.27, 841.89  # Standard A4

            # Prepare signature image
            sig_img = Image.open(io.BytesIO(sig_bytes))
            if sig_img.mode in ('RGBA', 'LA') or (sig_img.mode == 'P' and 'transparency' in sig_img.info):
                alpha = sig_img.convert('RGBA')
                bg = Image.new('RGBA', alpha.size, (255, 255, 255, 255))
                bg.paste(alpha, mask=alpha)
                sig_img = bg.convert('RGB')

            sig_buf = io.BytesIO()
            sig_img.save(sig_buf, format='PNG')
            sig_buf.seek(0)
            img_reader = ImageReader(sig_buf)

            # Create overlay canvas
            packet = io.BytesIO()
            can = canvas.Canvas(packet, pagesize=(page_w, page_h))

            box_w = 210.0
            box_h = 70.0
            margin = 25.0
            box_x = max(15.0, page_w - box_w - margin)
            box_y = margin

            # Draw white background box with clean border
            can.setFillColorRGB(1.0, 1.0, 1.0)
            can.setStrokeColorRGB(0.7, 0.7, 0.7)
            can.setLineWidth(1)
            can.roundRect(box_x, box_y, box_w, box_h, 4, fill=1, stroke=1)

            # Draw digital signature image
            can.drawImage(img_reader, box_x + 6, box_y + 10, width=85, height=50, preserveAspectRatio=True, mask='auto')

            # Draw textual verification details
            can.setFillColorRGB(0.1, 0.5, 0.2)
            can.setFont('Helvetica-Bold', 7.5)
            can.drawString(box_x + 96, box_y + 54, "DIGITALLY SIGNED")

            can.setFillColorRGB(0.2, 0.2, 0.2)
            can.setFont('Helvetica-Bold', 7)
            can.drawString(box_x + 96, box_y + 40, "Signer:")
            can.setFont('Helvetica', 6.5)
            can.drawString(box_x + 96, box_y + 30, signer_name[:24])

            can.setFont('Helvetica-Bold', 7)
            can.drawString(box_x + 96, box_y + 19, "Date:")
            can.setFont('Helvetica', 6.5)
            can.drawString(box_x + 96, box_y + 10, date_str)

            can.save()
            packet.seek(0)

            # Merge overlay onto the last page
            overlay_reader = PdfFileReader(packet, strict=False)
            overlay_page = overlay_reader.pages[0] if hasattr(overlay_reader, 'pages') else overlay_reader.getPage(0)

            writer = PdfFileWriter()
            for i, p in enumerate(pages):
                if i == len(pages) - 1:
                    if hasattr(p, 'merge_page'):
                        p.merge_page(overlay_page)
                    elif hasattr(p, 'mergePage'):
                        p.mergePage(overlay_page)
                if hasattr(writer, 'add_page'):
                    writer.add_page(p)
                elif hasattr(writer, 'addPage'):
                    writer.addPage(p)

            out_stream = io.BytesIO()
            if hasattr(writer, 'write_stream'):
                writer.write_stream(out_stream)
            elif hasattr(writer, 'write'):
                writer.write(out_stream)

            val = out_stream.getvalue()
            out_stream.close()
            packet.close()
            sig_buf.close()
            return val
        except Exception as e:
            _logger.error("Error in _stamp_pdf: %s", str(e), exc_info=True)
            return False

    @api.model
    def _stamp_image(self, img_bytes, sig_bytes, signer_name, date_str):
        try:
            base_img = Image.open(io.BytesIO(img_bytes)).convert('RGBA')
            sig_img = Image.open(io.BytesIO(sig_bytes)).convert('RGBA')

            target_sig_w = min(220, int(base_img.width * 0.3))
            aspect = sig_img.height / max(1, sig_img.width)
            target_sig_h = max(30, int(target_sig_w * aspect))
            resample_filter = getattr(Image, 'Resampling', Image).LANCZOS if hasattr(Image, 'Resampling') else getattr(Image, 'ANTIALIAS', 1)
            sig_img = sig_img.resize((target_sig_w, target_sig_h), resample_filter)

            box_pad = 10
            box_w = target_sig_w + 175 + box_pad * 2
            box_h = max(target_sig_h, 65) + box_pad * 2
            badge = Image.new('RGBA', (box_w, box_h), (255, 255, 255, 245))
            draw = ImageDraw.Draw(badge)
            draw.rectangle([(0, 0), (box_w - 1, box_h - 1)], outline=(180, 180, 180, 255), width=2)

            sig_y = box_pad + (box_h - box_pad * 2 - target_sig_h) // 2
            badge.paste(sig_img, (box_pad, sig_y), mask=sig_img)

            text_x = box_pad + target_sig_w + 12
            draw.text((text_x, box_pad + 6), "DIGITALLY SIGNED", fill=(25, 135, 84))
            draw.text((text_x, box_pad + 26), f"Signer: {signer_name[:22]}", fill=(33, 37, 41))
            draw.text((text_x, box_pad + 44), f"Date: {date_str}", fill=(108, 117, 125))

            pos_x = max(10, base_img.width - box_w - 20)
            pos_y = max(10, base_img.height - box_h - 20)
            base_img.paste(badge, (pos_x, pos_y), mask=badge)

            out_buf = io.BytesIO()
            base_img.convert('RGB').save(out_buf, format='JPEG', quality=95)
            val = out_buf.getvalue()
            out_buf.close()
            return val
        except Exception as e:
            _logger.error("Error in _stamp_image: %s", str(e), exc_info=True)
            return False

    def action_send_request(self):
        for rec in self:
            if rec.state == 'draft':
                rec.state = 'pending'
                if rec.partner_id:
                    rec.message_post(
                        body=_("Document request '%s' has been sent to employee %s.", rec.name, rec.employee_id.name),
                        partner_ids=[rec.partner_id.id]
                    )

    def action_approve(self):
        for rec in self:
            if rec.state in ['submitted', 'pending']:
                rec.state = 'approved'

                # Stamp digital signature directly onto the uploaded document file
                if rec.attachment_id and rec.signature:
                    rec.action_stamp_signature()

                # Update or create document in Odoo Documents app
                if rec.attachment_id:
                    if rec.document_id:
                        rec.document_id.sudo().write({
                            'attachment_id': rec.attachment_id.id,
                            'name': rec.name or rec.attachment_id.name,
                        })
                    else:
                        doc = self.env['documents.document'].sudo().create({
                            'name': rec.name or rec.attachment_id.name,
                            'attachment_id': rec.attachment_id.id,
                            'folder_id': rec.folder_id.id if rec.folder_id else False,
                            'tag_ids': [(6, 0, rec.tag_ids.ids)] if rec.tag_ids else False,
                            'owner_id': rec.user_id.id if rec.user_id else self.env.user.id,
                            'partner_id': rec.partner_id.id if rec.partner_id else False,
                            'res_model': rec._name,
                            'res_id': rec.id,
                        })
                        rec.document_id = doc.id

                    # Attach Digital Signature to Documents App Chatter/Attachments
                    if rec.signature and rec.document_id:
                        existing_sig = self.env['ir.attachment'].sudo().search([
                            ('res_model', '=', 'documents.document'),
                            ('res_id', '=', rec.document_id.id),
                            ('name', 'like', 'Digital_Signature_%')
                        ], limit=1)
                        if not existing_sig:
                            sig_attachment = self.env['ir.attachment'].sudo().create({
                                'name': f"Digital_Signature_{rec.signed_by or 'Employee'}.png",
                                'datas': rec.signature,
                                'mimetype': 'image/png',
                                'res_model': 'documents.document',
                                'res_id': rec.document_id.id,
                            })
                            signed_by_name = rec.signed_by or (rec.employee_id.name if rec.employee_id else 'Employee')
                            signed_time = fields.Datetime.to_string(rec.signed_on or fields.Datetime.now())
                            rec.document_id.sudo().message_post(
                                body=Markup(f"""
                                    <div style="border: 1px solid #ced4da; border-radius: 8px; padding: 12px; background-color: #f8f9fa; max-width: 480px; font-family: sans-serif;">
                                        <div style="font-weight: bold; font-size: 14px; margin-bottom: 4px; color: #198754;">
                                            &#9997;&#65039; Digitally Signed Document
                                        </div>
                                        <div style="font-size: 12px; color: #495057; margin-bottom: 8px;">
                                            Signed by: <b>{signed_by_name}</b> on {signed_time}
                                        </div>
                                        <div style="background-color: #ffffff; border: 1px solid #dee2e6; border-radius: 6px; padding: 8px; text-align: center;">
                                            <img src="/web/image/{sig_attachment.id}" style="max-height: 90px; max-width: 100%;" alt="Signature"/>
                                        </div>
                                    </div>
                                """),
                                attachment_ids=[sig_attachment.id]
                            )

    def action_reject(self):
        for rec in self:
            rec.state = 'rejected'

    def action_reset_draft(self):
        for rec in self:
            rec.state = 'draft'

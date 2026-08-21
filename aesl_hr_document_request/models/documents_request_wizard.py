# -*- coding: utf-8 -*-

from dateutil.relativedelta import relativedelta
from odoo import models, fields, api

class RequestWizardInherit(models.TransientModel):
    _inherit = "documents.request_wizard"

    def request_document(self):
        """
        Override Documents App 'Request a file' wizard to auto-create
        hr.document.request records. This ensures requests initiated from
        Documents App instantly appear on Employee Portal for Upload & Digital Signature.
        """
        document = super(RequestWizardInherit, self).request_document()
        partner = self.requestee_id or self.partner_id

        if partner:
            employee = self.env['hr.employee'].sudo().search([
                '|', ('user_id.partner_id', '=', partner.id),
                     ('work_contact_id', '=', partner.id)
            ], limit=1)

            deadline_date = False
            if self.activity_date_deadline_range > 0:
                deadline_date = fields.Date.context_today(self) + relativedelta(
                    **{self.activity_date_deadline_range_type: self.activity_date_deadline_range}
                )

            self.env['hr.document.request'].sudo().create({
                'name': self.name,
                'employee_id': employee.id if employee else False,
                'partner_id': partner.id,
                'user_id': partner.user_ids[0].id if partner.user_ids else False,
                'instructions': self.activity_note,
                'deadline': deadline_date,
                'folder_id': self.folder_id.id if self.folder_id else False,
                'tag_ids': [(6, 0, self.tag_ids.ids if self.tag_ids else [])],
                'state': 'pending',
                'document_id': document.id,
            })
        return document

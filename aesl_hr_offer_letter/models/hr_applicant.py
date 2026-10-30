# -*- coding: utf-8 -*-

from odoo import api, fields, models


class HrApplicant(models.Model):
    _inherit = 'hr.applicant'

    offer_letter_ids = fields.One2many(
        'hr.offer.letter',
        'applicant_id',
        string='Offer Letters'
    )
    offer_letter_count = fields.Integer(
        string='Offer Letter Count',
        compute='_compute_offer_letter_count'
    )

    @api.depends('offer_letter_ids')
    def _compute_offer_letter_count(self):
        for rec in self:
            rec.offer_letter_count = len(rec.offer_letter_ids)

    def action_view_offer_letters(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('aesl_hr_offer_letter.action_hr_offer_letter')
        action['domain'] = [('applicant_id', '=', self.id)]
        action['context'] = {
            'default_applicant_id': self.id,
            'default_candidate_name': self.partner_name,
            'default_email': self.email_from,
            'default_phone': self.partner_phone,
            'default_job_id': self.job_id.id,
            'default_department_id': self.department_id.id,
            'default_gross_salary': self.salary_proposed or self.salary_expected or 0.0,
            'default_joining_date': self.availability,
        }
        return action

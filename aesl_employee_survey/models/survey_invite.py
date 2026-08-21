# -*- coding: utf-8 -*-

from odoo import models, api

class SurveyInvite(models.TransientModel):
    _inherit = 'survey.invite'

    def _prepare_answers(self, partners, emails):
        """
        Ensure answers created via wizard auto-link matching partner_id by email if partner_ids was empty.
        This prevents 'answer_wrong_user' survey access errors when employees open their survey email link.
        """
        answers = super(SurveyInvite, self)._prepare_answers(partners, emails)
        for answer in answers:
            if not answer.partner_id and answer.email:
                partner = self.env['res.partner'].search([('email', '=ilike', answer.email.strip())], limit=1)
                if partner:
                    answer.sudo().write({'partner_id': partner.id})
        return answers

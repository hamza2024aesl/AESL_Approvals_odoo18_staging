# -*- coding: utf-8 -*-

from odoo import models, fields, api

class SurveyInvite(models.TransientModel):
    _inherit = 'survey.invite'

    employee_ids = fields.Many2many(
        'hr.employee',
        'survey_invite_employee_rel',
        'invite_id',
        'employee_id',
        string='Recipients'
    )

    def _get_employee_user_partner(self, emp):
        if emp.user_id and emp.user_id.partner_id:
            return emp.user_id.partner_id
        if emp.work_contact_id:
            return emp.work_contact_id
        return False

    @api.onchange('employee_ids')
    def _onchange_employee_ids(self):
        if self.employee_ids:
            partners = self.env['res.partner']
            for emp in self.employee_ids:
                partner = self._get_employee_user_partner(emp)
                if partner:
                    partners |= partner
            self.partner_ids = [(6, 0, partners.ids)]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('employee_ids') and not vals.get('partner_ids'):
                emp_ids = vals['employee_ids'][0][2] if isinstance(vals['employee_ids'][0], (list, tuple)) else vals['employee_ids']
                employees = self.env['hr.employee'].browse(emp_ids)
                partners = self.env['res.partner']
                for emp in employees:
                    p = self._get_employee_user_partner(emp)
                    if p:
                        partners |= p
                if partners:
                    vals['partner_ids'] = [(6, 0, partners.ids)]
        return super(SurveyInvite, self).create(vals_list)

# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError,AccessError

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    travel_department_id = fields.Many2one('hr.department', string='Travel Department', store=True)
    is_manager_assistant = fields.Boolean('Managers Assistant')


class AssistantEmployeeMixin(models.AbstractModel):
    _name = 'assistant.employee.mixin'
    _description = 'Managers Assistant Employee Mixin'

    is_manager_assistant = fields.Boolean(compute='_compute_is_managers_assistant')

    @api.depends_context('uid')
    def _compute_is_managers_assistant(self):
        is_assistant = bool(self.env.user.employee_id.is_manager_assistant)
        for rec in self:
            rec.is_manager_assistant = is_assistant

    def _check_employee_change_allowed(self, vals):
        """Assistant (ya HR manager) ke ilawa koi dusre employee ke naam pe create nahi kar sakta."""
        if 'employee_id' not in vals or self.env.su:
            return
        user = self.env.user
        if user.employee_id.is_manager_assistant or user.has_group('hr.group_hr_manager'):
            return
        if vals['employee_id'] != user.employee_id.id:
            raise AccessError("You can create own request.")

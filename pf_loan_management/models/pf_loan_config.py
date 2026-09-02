# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class PFLoanConfig(models.Model):
    _name = 'pf.loan.config'
    _description = 'PF Loan Approvers Configuration'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Configuration Name", default="PF Loan Approvers Config", required=True)
    hr_id = fields.Many2one('hr.employee', string="1st Approver (HR)", required=True, tracking=True)
    hod_id = fields.Many2one('hr.employee', string="2nd Approver (Head of Department)", required=True, tracking=True)
    finance_id = fields.Many2one('hr.employee', string="3rd Approver (Finance Officer)", required=True, tracking=True)
    trustee_id = fields.Many2one('hr.employee', string="4th Approver (Trustee Main)", tracking=True)
    trustee_ids = fields.Many2many('hr.employee', 'pf_loan_config_trustee_rel', 'config_id', 'employee_id', string="4th Approver (Trustees)", tracking=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    @api.model
    def get_config(self):
        return self.sudo().search([], limit=1)

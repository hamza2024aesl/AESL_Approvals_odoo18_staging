# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ApprovalConfig(models.Model):
    _name = 'approval.config'
    _description = 'Approval Configuration'

    name = fields.Char(string='Name', required=True)
    config_type = fields.Selection([
        ('domestic', 'Domestic'),
        ('international', 'International')
    ], string='Configuration Type', required=True, default='domestic')
    
    first_approver_line_ids = fields.One2many('approval.config.line', 'config_id', string='1st Approver', domain=[('line_type', '=', 'first_approver')])
    second_approver_line_ids = fields.One2many('approval.config.line', 'config_id', string='2nd Approver', domain=[('line_type', '=', 'second_approver')])
    finance_line_ids = fields.One2many('approval.config.line', 'config_id', string='Finance & Admin', domain=[('line_type', '=', 'finance')])
    hr_line_ids = fields.One2many('approval.config.line', 'config_id', string='HR', domain=[('line_type', '=', 'hr')])

class ApprovalConfigLine(models.Model):
    _name = 'approval.config.line'
    _description = 'Approval Configuration Line'

    config_id = fields.Many2one('approval.config', string='Configuration Reference', ondelete='cascade')
    line_type = fields.Selection([
        ('first_approver', '1st Approver'),
        ('second_approver', '2nd Approver'),
        ('finance', 'Finance & Admin'),
        ('hr', 'HR')
    ], string='Line Type', required=True)
    
    work_location_ids = fields.Many2many('hr.work.location', string='Regions')
    department_id = fields.Many2one('hr.department', string='Department')
    employee_id = fields.Many2one('hr.employee', string='Approver Employee')

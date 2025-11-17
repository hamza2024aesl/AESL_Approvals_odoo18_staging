from odoo import fields, models


class InputCode(models.Model):
    _name = 'input.code'
    _description = 'Input Code'

    line = fields.Many2one('hr.salary.rule')
    description = fields.Char(string='Description')
    code = fields.Char(string='Code')

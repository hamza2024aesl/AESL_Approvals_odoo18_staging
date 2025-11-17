# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class IncrementRaiseLines(models.Model):
    _name = 'increment.raise.lines'

    increment_raise_id = fields.Many2one('appraisal.system', string='Increment Raise Lines',required=True, index=True,
                                         ondelete='cascade')
    increment_raise_amount = fields.Float(string="Increment Raise Amount")
    increment_raise_by = fields.Many2one('res.users', string="Increment Raised By")

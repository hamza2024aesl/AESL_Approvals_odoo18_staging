# -*- coding: utf-8 -*-

from odoo import fields, models


class HrAssetItemTemplate(models.Model):
    _name = 'hr.asset.item.template'
    _description = 'Asset Checklist Template Item'
    _order = 'department_type, sequence, id'

    name = fields.Char(string='Asset / Item Description', required=True)
    department_type = fields.Selection([
        ('admin', 'Admin Department'),
        ('it', 'IT Department'),
        ('hse', 'HSE Department'),
    ], string='Responsible Department', required=True, index=True)
    sequence = fields.Integer(string='Sequence', default=10)
    placeholder_hint = fields.Char(string='Details Placeholder / Hint', help="Example: Serial number, vehicle registration, or card ID")
    active = fields.Boolean(string='Active', default=True)

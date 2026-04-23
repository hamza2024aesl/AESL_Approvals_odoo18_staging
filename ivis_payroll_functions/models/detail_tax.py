from odoo import models, fields


class DetailTax(models.Model):
    _name = 'detail.tax'
    _description = 'Detailed Tax'

    name = fields.Char()
    code = fields.Char()
    recurring = fields.Boolean(string="Recurring")

from odoo import models, fields


class InstituteInstitute(models.Model):
    _name = 'institute.institute'
    _description = "Institute"

    name = fields.Char(string="Institute")

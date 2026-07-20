from odoo import models, fields


class OtherDocument(models.Model):
    _name = 'other.document'
    _description = "Other Documents"

    document_id = fields.Many2one('hr.employee', string='Other documents')
    name = fields.Char(string="Document name", required=True)
    attach_file = fields.Binary(string='Attach document')

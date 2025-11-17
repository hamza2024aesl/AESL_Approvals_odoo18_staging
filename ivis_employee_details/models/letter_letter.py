from odoo import models, fields


class LetterLetter(models.Model):
    _name = 'letter.letter'
    _description = "Letters"

    letter_no = fields.Char(required=True)
    letter_id = fields.Many2one('hr.employee', string="Letters")
    name = fields.Char(required=True)
    issue_date = fields.Date()
    documents = fields.Binary()

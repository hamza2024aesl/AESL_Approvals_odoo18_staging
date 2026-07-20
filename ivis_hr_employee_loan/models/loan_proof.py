from odoo import models, fields


class LoanProof(models.Model):
    _name = 'loan.proof'
    _description = "Loan Proof"

    name = fields.Char(
        string='Name',
        required=True,
    )
    mandatory = fields.Boolean(
        string='Mandatory'
    )

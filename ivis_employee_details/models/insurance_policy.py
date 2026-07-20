from odoo import models, fields


class InsurancePolicy(models.Model):
    _name = 'insurance.policy'
    _description = "Insurance Policy"

    name = fields.Char('Policy Name', required=True)
    description = fields.Char('Description', required=True)

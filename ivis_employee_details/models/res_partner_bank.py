from odoo import models, fields


class ResPartnerBankInherit(models.Model):
    _inherit = 'res.partner.bank'

    x_studio_branch_name = fields.Char(string="Branch Name")
    x_studio_branch_code = fields.Char(string="Branch Code")

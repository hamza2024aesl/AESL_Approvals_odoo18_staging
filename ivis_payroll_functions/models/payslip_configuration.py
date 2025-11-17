from odoo import fields, models


class payslip_configuration(models.Model):
    _name = 'payslip.configuration'

    name = fields.Selection([(0, 'Disable Tax Summary'), (1, 'Enable Tax Summary')], string='Tax Summary')

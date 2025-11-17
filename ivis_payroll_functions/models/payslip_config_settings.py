from odoo import api, fields, models
from odoo.exceptions import AccessError


class payslip_config_transient(models.TransientModel):
    _name = 'payslip.config.settings'

    name = fields.Selection([(0, 'Disable Tax Summary'), (1, 'Enable Tax Summary')], string='Tax Summary')

    @api.model
    def default_get(self, fields):
        res = super(payslip_config_transient, self).default_get(fields)
        obj = self.env['payslip.configuration'].search([])
        if obj:
            res['name'] = obj[0].name
        return res

    def execute(self):
        # self.ensure_one()
        if not self.env.user._is_superuser() and not self.env.user.has_group('hr_payroll.group_hr_payroll_manager'):
            raise AccessError("Only administrators can change the settings")
        self.env['payslip.configuration'].search([]).unlink()
        # self.env['payslip.configuration'].create({'name': 'self.name'})
        return {
            'url': '/web',
            'type': 'ir.actions.act.url',
            'target': 'self'
        }

    def cancel(self):
        return {
            'url': '/web',
            'type': 'ir.actions.act.url',
            'target': 'self'
        }

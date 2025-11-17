from odoo import api, models


class Machinedata(models.Model):
    _inherit = 'zk.machine.attendance'
    _description = 'Machine Data'

    @api.model
    def _CRON_fetch_attendance(self):
        machines = self.env['zk.machine'].search([])
        for machine in machines:
            machine.download_attendance()
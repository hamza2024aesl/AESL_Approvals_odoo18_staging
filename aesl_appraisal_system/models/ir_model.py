from odoo import models, _
from odoo.exceptions import UserError


class IrModel(models.Model):
    _inherit = 'ir.model'

    def export_data(self, fields_to_export, raw_data=False):
        if not self.env.user.has_group('aesl_appraisal_system.group_hr_manager_appraisal_3'):
            raise UserError(_("You do not have permission to export data."))
        return super(IrModel, self).export_data(fields_to_export, raw_data)

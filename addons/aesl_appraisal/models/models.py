from odoo import models, fields


class ContractInherit(models.Model):
    _inherit = 'hr.contract'

    # Note: All these fields already exist in hr.contract
    # We're just inheriting them to customize views if needed

    # Add any custom fields if needed
    appraisal_note = fields.Text(string='Appraisal Note',
                                 help='Additional notes for appraisal')

    def _get_report_base_filename(self):
        return self.name
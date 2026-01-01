from odoo import models, fields, api, _


class HrAppraisalRemarks(models.Model):
    _name = 'appraisal.future.prospect'
    _description = 'Appraisal Future Prospect'

    appraisal_id = fields.Many2one('hr.appraisal', string="Appraisal")
    future_prospect_text = fields.Text(string="Future Prospect Text")
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date, datetime, time

class HrAppraisalRemarks(models.Model):
    _name = 'hr.appraisal.remarks'
    _description = 'Appraisal Remarks'

    appraisal_id = fields.Many2one('hr.appraisal', string="Appraisal")
    remark_text = fields.Text(string="Remark Text")

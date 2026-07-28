# ---------------------------------------------------------
# DYNAMIC APPRAISAL WORKFLOW – FINAL VERSION
# ---------------------------------------------------------

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError,UserError
from datetime import date, datetime, time


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    x_studio_grade = fields.Char(string="Grade")

from odoo import models, fields


class HrSalaryRuleInherit(models.Model):
    _inherit = 'hr.salary.rule'

    appears_on_report = fields.Boolean(string='Appears on Report')
    report_sequence = fields.Integer(string='Sequence on Report')

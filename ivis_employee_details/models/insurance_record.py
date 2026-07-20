from odoo import models, fields


class InsuranceRecord(models.Model):
    _name = 'insurance.record'
    _description = "Employee's Insurance"

    insurance_id = fields.Many2one('hr.employee', string="Insurance")
    name = fields.Char(default='Insurance')
    policy_num = fields.Char(string="Policy No", required=True)
    policy_coverage = fields.Selection(
        [('three_months', ' 3 months'), ('half_yearly', 'Half Yearly'), ('yearly', 'Yearly')], string="Policy Duration")
    policy_type = fields.Many2one('insurance.policy', string="Policy type", required=True)
    policy_amount = fields.Float(string='Policy amount', required=True)
    issue_date = fields.Date(string="Issue Date", required=True)
    expiry_date = fields.Date(string="Expiry Date", required=True)
    reminder_period = fields.Integer(string="Reminder", default='7',
                                     help='Sends Reminder Notification for Expiration of Insurance before specified days')
    description = fields.Text(string="Description")

from odoo import fields, models


class CustomTreeReport(models.TransientModel):
    _name = 'custom.tree.report'
    _description = 'Custom Tree Report'

    department_id = fields.Many2one('hr.department', 'Department')
    employee_id = fields.Many2one('hr.employee', 'Employee')
    gross_pay = fields.Float('Gross Pay')
    employee_code = fields.Char(related='employee_id.registration_number')
    opening_pfund = fields.Float('Opening PFund')
    current_pfund = fields.Float('Current Month PFund')
    interest = fields.Float("Total Interest")
    pfund_till_date = fields.Float('PFund Till Date')
    emplr_pfund = fields.Float('Emplr Cotr Till Date')
    total_pfund = fields.Float('Total PFund')

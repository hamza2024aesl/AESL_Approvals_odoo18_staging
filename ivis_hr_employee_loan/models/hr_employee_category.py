from odoo import models, fields


class HrEmployeeCategory(models.Model):
    _inherit = "hr.employee.category"
    _description = "Employee Category"

    loan_policy = fields.Many2many(
        'loan.policy',
        'employee_category_policy_rel_loan',
        'category_id',
        'policy_id',
        string='Loan Policies'
    )
    allow_multiple_loan = fields.Boolean(
        string='Allow Multiple Loans'
    )

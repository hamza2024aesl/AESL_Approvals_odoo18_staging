from odoo import models, fields


class LoanPloicy(models.Model):
    _name = "loan.policy"
    _description = "Loan Policy Details"

    name = fields.Char(
        'Name',
        required=True
    )
    code = fields.Char(
        'Code'
    )
    employee_categ_ids = fields.Many2many(
        'hr.employee.category',
        'employee_category_policy_rel_loan',
        'policy_id',
        'category_id',
        'Employee Categories'
    )
    employee_ids = fields.Many2many(
        'hr.employee',
        'policy_employee_rel',
        'policy_id',
        'employee_id',
        "Employee's"
    )
    company_id = fields.Many2one(
        'res.company',
        'Company',
        required=True,
        default=lambda self: self.env.user.company_id
    )
    policy_type = fields.Selection(
        selection=[
            ('maxamt', 'Max Loan Amount'),
            ('loan_gap', 'Gap between two loans'),
            ('eligible_duration', 'Qualifying Period'),
            ('', '')],
        string='Policy Type',
        required=True,
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('done', 'Done')],
        string='State',
        readonly=True
    )
    max_loan_type = fields.Selection(
        selection=[
            # ('basic', 'Basic Salary'),
            # ('gross', 'Gross Salary'),
            ('fixed', 'Fix Amount'),
            ('multiple_of_salary', 'Multiple of Salary'),
            ('', '')],
        string='Basis',
        help='As a percentage of Basic/Gross Salary or as a fixed amount',
    )
    policy_value = fields.Float(
        string='Value',
        help='If policy type is Max Loan Amount and Basis is Fixed Amount, then set value as a fixed amount, ie maximum loan that can be taken. \n If policy type is Gap between two loans or Qualifying Period, then set value as a number of months.'
    )

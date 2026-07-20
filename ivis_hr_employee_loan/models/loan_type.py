from odoo import models, fields, api, _
from odoo.exceptions import UserError


class LoanType(models.Model):
    _name = 'loan.type'
    _description = 'Loan Type'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def onchange_interest_payable(self, int_payble):
        if not int_payble:
            return {'value': {'interest_mode': '', 'int_rate': 0.0}}
        return {}

    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('done', 'Done')],
        string='State',
        readonly=True
    )
    name = fields.Char(
        string='Name',
        required=True
    )

    @api.constrains('name')
    def _check_name(self):
        record_exist = self.env['loan.type'].search([('name', '=', self.name)])
        if len(record_exist) > 1:
            raise UserError(_('Loan Type Already Exist'))

    code = fields.Char(
        string='Code'
    )
    int_payable = fields.Boolean(
        string='Is Interest Payable',
        default=True
    )
    interest_mode = fields.Selection(
        selection=[
            ('flat', 'Flat'),
            ('reducing', 'Reducing')],
        string='Interest Mode',
    )
    int_rate = fields.Float(
        string='Rate',
        help='Put interest between 0-100 in range',
        digits=(16, 2),
        required=True
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=False,
        readonly=True,
        default=lambda self: self.env.user.company_id
    )
    loan_interest_account = fields.Many2one(
        'account.account',
        string="Interest Account"
    )
    employee_categ_ids = fields.Many2many(
        'hr.employee.category',
        'employee_category_loan_type_rel',
        'loan_type_id',
        'category_id',
        'Employee Categories'
    )
    employee_ids = fields.Many2many(
        'hr.employee',
        'loan_type_employee_rel',
        'loan_type_id',
        'employee_id',
        "Employee's"
    )
    payment_method = fields.Selection(
        selection=[
            ('salary', 'Deduction From Payroll'),
            ('cash', 'Direct Cash/Cheque')],
        string='Repayment Method',
        default='salary'
    )
    disburse_method = fields.Selection(
        selection=[
            ('payroll', 'Through Payroll'),
            ('loan', 'Direct Cash/Cheque')],
        string='Disburse Method',
        default='loan'
    )
    noOfSalary = fields.Integer()
    servicePeriod = fields.Integer()
    loan_proof_ids = fields.Many2many(
        'loan.proof',
        string='Loan Proofs',
    )

    # @api.model
    # def create(self, vals):
    #     created_id = super(LoanType, self).create(vals)
    #     category = self.env['hr.salary.rule.category'].search([('name', '=', 'Deduction')])
    #     self.env['hr.salary.rule'].create(
    #         {'name': vals['name'], 'code': str(vals['name']), 'category_id': category.id, 'amount_select': 'code',
    #          'amount_python_compute': "result = -employee.get_installment_loan(employee.id, payslip.date_from, payslip.date_to,'" +
    #                                   vals['name'] + "')", 'is_loan_payment': 'True'})
    #     return created_id

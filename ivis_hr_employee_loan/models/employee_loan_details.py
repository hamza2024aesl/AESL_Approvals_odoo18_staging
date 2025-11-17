import math
import time
from datetime import datetime, date
from dateutil import relativedelta as rdelta
from dateutil.relativedelta import relativedelta
from lxml import etree
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT


class EmployeeLoanDetails(models.Model):
    _name = "employee.loan.details"
    _description = "Employee Loan"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "name desc"

    dont_disburse_loan = fields.Boolean('Do Not Disburse Loan')
    cheque_no = fields.Char('Cheque No')
    ref = fields.Char('Ref')

    def unlink(self):
        if any(self.installment_lines.filtered(lambda x: x.state in ['paid'])):
            raise ValidationError("Some Installments have been paid, now you cannot delete Loan")
        return super(EmployeeLoanDetails, self).unlink()

    # def write(self, vals):
    #     res = super(EmployeeLoanDetails, self).write(vals)
    #     if self.installment_lines:
    #         Sum = sum(i.total for i in self.installment_lines)
    #         SUM = str("{:.2f}".format(Sum))
    #         TOTAL = str("{:.2f}".format(self.final_total))
    #         if SUM != TOTAL:
    #             raise ValidationError(_("Total Loan and EMI Total is not same!"))
    #     return res

    def apply(self):
        self.action_applied()

    def cancel(self):
        self.write({'state': 'cancel'})

    def reject(self):
        self.write({'state': 'rejected'})

    def get_lines(self):
        self.env.cr.execute(
            """select install_no,principal_amt,interest_amt,date_from,date_to,total,state from loan_installment_details where loan_id = {0} order by date_from""".format(
                self.id))
        rs = self.env.cr.dictfetchall()
        return rs

    def get_default_date_format(self, loan_date):
        lang_id = self.env['res.lang'].search([('code', '=', self.env.context.get('lang', 'en_US'))])
        return datetime.strptime(str(loan_date), '%Y-%m-%d').strftime(lang_id.date_format)

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(EmployeeLoanDetails, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                               submenu=submenu)
        doc = etree.XML(res['arch'])
        nodes = doc.xpath("//field[@name='employee_id']")
        for node in nodes:
            if self.env.user.has_group('ivis_hr_employee_loan.hr_loan_approval_group') == True:
                node.set('domain', "[('id','>',0)]")
            else:
                node.set('domain', "['|',('parent_id.user_id','=',uid),('user_id','=',uid)]")
        res['arch'] = etree.tostring(doc)
        return res

    def final_approved(self):
        self.write({'state': 'final_approved'})

    def hr_approved(self):
        self.write({'state': 'hr_approved'})

    def manager_approval(self):

        if self.employee_id.parent_id.user_id.id == self.env.uid or \
                self.env.user.has_group('ivis_hr_employee_loan.top_management_loan_approval_group') == True:
            self.write({'state': 'manager_approved'})
        else:
            raise UserError(_('Only Your Boss can approve your request'))

    def disburse_loan(self):
        if self.dont_disburse_loan:
            self.write({'state': 'disburse'})
        else:
            if not self.cheque_no:
                raise ValidationError("Kindly Enter Cheque No.")

            if not self.ref:
                self.ref = 'Loan of ' + self.employee_id.name,

            payement_method_id = \
                self.env['account.payment.method'].search(
                    [('code', '=', 'manual'), (('payment_type', '=', 'outbound'))])[
                    0].id
            payment = self.env['account.payment'].create({
                'partner_type': 'supplier',
                'payment_type': 'outbound',
                'partner_id': self.employee_id.address_home_id.id,
                'journal_id': self.journal_id.id,
                'company_id': self.employee_id.address_home_id.company_id.id,
                'payment_method_id': payement_method_id,
                'amount': self.total_amount_due,
                'currency_id': self.currency_id.id,
                'payment_date': self.date_disb,
                'ref': self.cheque_no,
                'pay_ref': self.ref,
                'loan_id': self.id,
            })
            payment.tick_loan_assign(self.employee_loan_account)
            payment.post()
            self.write({'state': 'disburse', 'voucher_ref': payment.id})

    # @api.constrains('installment_lines')
    # def check_total_principal_interest_amount(self):
    #     if not self.int_payable and sum(self.installment_lines.mapped('principal_amt')) != sum(self.installment_lines.mapped('interest_amt')):
    #         raise UserError('Total principal amount and total interest amount should be exactly same for non interest based loans.')

    def check_total_amount(self):
        if self.interest_mode == 'flat':
            Sum = sum(line.principal_amt for line in self.installment_lines[:-1])
            if self.final_total != Sum:
                if Sum < self.actual_principal_amount:
                    difference = self.actual_principal_amount - Sum
                    val = self.flat_rate_method(self.int_rate, difference)
                    for rec in self.installment_lines[-1]:
                        rec.write({'principal_amt': difference,
                                   'interest_amt': val,
                                   'interest_rate': self.int_rate,
                                   'total': val + difference})
        elif self.interest_mode == False:
            Sum = sum(line.principal_amt for line in self.installment_lines[:-1])
            if self.final_total != Sum:
                if Sum < self.actual_principal_amount:
                    difference = self.actual_principal_amount - Sum
                    for rec in self.installment_lines[-1]:
                        rec.write({'principal_amt': difference,
                                   'interest_amt': 0.0,
                                   'interest_rate': 0.0,
                                   'total': difference})

    @api.onchange('employee_id')
    def get_details(self):
        for user in self:
            if self.employee_id:
                self.department_id = self.employee_id.department_id
                self.company_id = self.employee_id.company_id

    @api.depends('installment_lines', 'actual_principal_amount', 'int_rate', 'duration', 'installment_lines.state',
                 'no_of_months')
    def _cal_amount_all(self):
        for rec in self:
            total_interest_amount = 0
            if rec.int_payable:
                if rec.interest_mode == 'flat':
                    per_month = self.flat_rate_method(rec.int_rate, rec.duration)
                    p_amount = 0
                    duration = 0
                    if rec.actual_principal_amount:
                        p_amount = rec.actual_principal_amount
                    else:
                        p_amount = 0
                    if rec.duration:
                        duration = rec.duration
                    else:
                        duration = 0
                    installement_per_month = p_amount / duration if p_amount and duration else 0
                    rec.total_interest_amount = per_month * installement_per_month
                elif rec.interest_mode == 'reducing':
                    values = self.reducing_balance_method(rec.actual_principal_amount, rec.int_rate, rec.no_of_months)
                    for key, value in values.items():
                        total_interest_amount += value['interest_comp']
            paid_total = 0
            principal_total_paid = 0
            for payment in rec.installment_lines:
                if payment.state == 'paid':
                    paid_total += payment.total
                    if payment.balloon_amount >= 1:
                        paid_total += payment.balloon_amount
                else:
                    principal_total_paid += payment.principal_amt
            rec.total_interest_amount = (total_interest_amount if not rec.installment_lines else sum(
                i.interest_amt for i in rec.installment_lines))
            rec.total_amount_paid = paid_total
            rec.final_total = rec.actual_principal_amount + (
                rec.total_interest_amount if not rec.installment_lines else sum(
                    i.interest_amt for i in rec.installment_lines))
            rec.total_amount_due = rec.final_total - rec.total_amount_paid
            rec.total_amount_due_principal = principal_total_paid

    @api.depends('loan_policy_ids')
    def _calc_max_loan_amt(self):
        for rec in self:
            for policy in rec.loan_policy_ids:
                if policy.policy_type == 'maxamt':
                    if policy.max_loan_type == 'basic':
                        if rec.employee_id.contract_id.wage:
                            rec.max_loan_amt = rec.employee_id.contract_id.wage * policy.policy_value / 100
                    elif policy.max_loan_type == 'gross':
                        rec.max_loan_amt = rec.employee_gross * policy.policy_value / 100
                    else:
                        rec.max_loan_amt = policy.policy_value

    def _check_multi_loan(self, employee):
        allow_multiple_loans = employee.allow_multiple_loan
        for categ in employee.category_ids:
            if categ.allow_multiple_loan:
                allow_multiple_loans = categ.allow_multiple_loan
                break
        return allow_multiple_loans

    @api.depends('loan_type')
    def _get_loan_values(self):
        for rec in self:
            rec.int_payable = rec.loan_type.int_payable
            allowed_employees = []
            for categ in rec.loan_type.employee_categ_ids:
                allowed_employees += map(lambda x: x.id, categ.employee_ids)
            allowed_employees += map(lambda x: x.id, rec.loan_type.employee_ids)
            if rec.employee_id.id in allowed_employees:
                # rec.int_rate = rec.loan_type.int_rate
                rec.interest_mode = rec.loan_type.interest_mode
                rec.int_payable = rec.loan_type.int_payable

    installment_type = fields.Selection([('amount_wise', 'Amount Per Month'), ('month_wise', 'Month')])

    @api.depends('installment_type')
    def _change_field_status(self):
        for rec in self:
            rec.no_of_months = 0
            rec.duration = 0

    @api.model
    def flat_rate_method(self, rate, duration):
        per_month_without_interest = (duration * rate) / 100
        months = (rate / 12)
        return per_month_without_interest * months

    @api.depends('loan_type')
    def _compute_proof_loan(self):
        for rec in self:
            rec.loan_proof_ids = rec.loan_type.loan_proof_ids

    @api.model
    def reducing_balance_method(self, p, r, n):
        # Determine the interest rate on the loan, the length of the loan and the amount of the loan
        res = {}
        for i in range(0, n):
            step_1_p = p  # principal amount at the beginning of each period
            rate = (r / 100)
            step_2_r_m = rate / 12  # interest rate per month
            step_3_r_m = 1 + step_2_r_m  # add 1 to interest rate per month
            step_4 = step_3_r_m ** (
                    n - i)  # Raise the step_2_r_m to the power of the number of payments required on the loan
            step_5 = step_4 - 1  # minus 1 from step_4
            step_6 = step_2_r_m / step_5  # Divide the interest rate per month(step_2_r_m) by the step_5
            step_7 = step_6 + step_2_r_m  # Add the interest rate per month to the step_6
            step_8_EMI = round(step_7 * step_1_p, 2)  # Total EMI to pay month
            step_9_int_comp = round(step_1_p * step_2_r_m, 2)  # Total Interest component in EMI
            step_10_p_comp = round(step_8_EMI - step_9_int_comp, 2)  # Total principal component in EMI
            p -= step_10_p_comp  # new principal amount
            res[i] = {'emi': step_8_EMI,
                      'principal_comp': step_10_p_comp,
                      'interest_comp': step_9_int_comp
                      }
        return res

    #    @api.multi
    #    def _check_status(self):
    #        payslip_obj = self.env['hr.payslip']
    #        for loan in self:
    #            if loan.loan_type.disburse_method == 'payroll' and loan.state == 'approved':
    #                payslips = payslip_obj.search([('contract_id', '=', loan.employee_id.contract_id.id),
    #                                             ('date_to', '>=', loan.date_approved),
    #                                             ('date_from', '<=', loan.date_approved)])
    #                for slip in payslips:
    #                    if slip.state == 'done':
    #                        for line in slip.line_ids:
    #                            if line.salary_rule_id.loan_allowance:
    #                                loan.check_status = True
    #                                break
    #                        if loan.check_status:
    #                            self._cr.execute("update employee_loan_details set state='disburse' where id = %s" % (loan.id))
    #                            break
    @api.model
    def _employee_get(self):
        ids = self.env['hr.employee'].search([('user_id', '=', self._uid)], limit=1)
        if ids:
            return ids

    name = fields.Char(
        string='Number',
        readonly=True,
        copy=False
    )
    # default = _employee_get
    # readonly = True,
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
    )

    department_id = fields.Many2one(
        'hr.department',
        string="Department",
    )
    date_applied = fields.Date(
        string='Applied Date',
        required=True,
        readonly=False,
        default=fields.Date.context_today
    )
    date_approved = fields.Date(
        string='Approved Date',
        readonly=True,
        copy=False
    )
    date_repayment = fields.Date(
        string='Repayment Date',
        copy=False
    )
    date_disb = fields.Date(
        string='Disbursement Date',
        required=True,
    )
    loan_type = fields.Many2one(
        'loan.type',
        string='Loan Type',
        required=True,
    )
    duration = fields.Integer(
        string='Installment Amount(per month)'
    )
    no_of_months = fields.Integer(
        string='Installment Month',
    )
    loan_policy_ids = fields.Many2many(
        'loan.policy',
        'loan_policy_rel',
        'policy_id',
        'loan_id',
        string="Active Policies",
    )
    int_payable = fields.Boolean(
        compute='_get_loan_values',
        string='Is Interest Payable',
        store=True,
    )
    interest_mode = fields.Selection(
        compute='_get_loan_values',
        selection=[('flat', 'Flat'), ('reducing', 'Reducing'), ('', '')],
        string='Interest Mode',
        store=True,
        default=''
    )
    int_rate = fields.Float(
        related='loan_type.int_rate',
        string='Rate',
        help='Interest rate between 0-100 in range',
        digits=(16, 2),
        # store=True
    )
    principal_amount = fields.Float(
        string='Requested Amount',
        required=True,
    )
    actual_principal_amount = fields.Float(
        string='Approved Amount',
    )
    employee_gross = fields.Float(
        string='Gross Salary',
        help='Employee Gross Salary from Payslip if payslip is not available please enter value manually.',
        required=False,
    )
    final_total = fields.Float(
        compute='_cal_amount_all',
        string='Total Loan',
        store=True
    )
    total_amount_paid = fields.Float(
        compute='_cal_amount_all',
        #         multi="calc",
        string='Received From Employee',
        store=True
    )
    total_amount_due_principal = fields.Float(
        compute='_cal_amount_all',
        #         multi="calc",
        help='Remaining Principal Amount due.',
        string='Principal Balance on Loan',
        store=True
    )
    total_amount_due = fields.Float(
        compute='_cal_amount_all',
        #         multi="calc",
        help='Remaining Amount due.',
        string='Balance on Loan',
        store=True
    )
    total_interest_amount = fields.Float(
        compute='_cal_amount_all',
        string='Total Interest on Loan',
        store=True
    )
    max_loan_amt = fields.Float(
        compute='_calc_max_loan_amt',
        store=True,
        string='Max Loan Amount'
    )
    installment_lines = fields.One2many(
        'loan.installment.details',
        'loan_id',
        'Installments',
        copy=False
    )
    company_id = fields.Many2one(
        'res.company',
        'Company',
        required=True,
        default=lambda self: self.env.user.company_id
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        readonly=True,
        default=lambda self: self.env.user.company_id.currency_id
    )
    user_id = fields.Many2one(
        'res.users',
        default=lambda self: self.env.user,
        string='User',
        required=True,
    )
    employee_loan_account = fields.Many2one(
        'account.account',
        string="Employee Account",
        readonly=False,
    )
    journal_id = fields.Many2one(
        'account.journal',
        string='Disburse Journal',
        help='Journal related to loan for Accounting Entries',
        required=False,
        readonly=False,
    )
    journal_id1 = fields.Many2one(
        'account.journal',
        string='Repayment Board Journal',
        required=False,
        readonly=False,
    )
    journal_id2 = fields.Many2one(
        'account.journal',
        string='Interest Journal',
        required=False,
        readonly=False,
    )
    move_id = fields.Many2one(
        'account.move',
        string='Accounting Entry',
        readonly=True,
        help='Accounting Entry once loan has been given to employee',
        copy=False
    )
    voucher_ref = fields.Many2one(
        'account.payment',
        string='Voucher Ref',
        help='Voucher Reference once loan has been given to employee',
        copy=False
    )
    loan_proof_ids = fields.Many2many(
        'loan.proof',
        compute='_compute_proof_loan',
        string='Loan Proofs',
    )
    #    check_status = fields.Boolean(
    #        compute='_check_status',
    #        string='Check Status',
    #        store=True
    #    )
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('applied', 'Applied'),
            ('manager_approved', 'Manager Approved'),
            ('hr_approved', 'HR Approved'),
            ('final_approved', 'Final Approved'),
            ('paid', 'Paid'),
            ('disburse', 'Disbursed'),
            ('rejected', 'Rejected'),
            ('cancel', 'Cancelled')],
        string='State',
        readonly=True,
        copy=False,
        default='draft',
    )
    notes = fields.Text(
        string='Note'
    )

    #     @api.one
    #     def copy(self, default=None):
    #         print "--------copy-------------"
    #         if not default:
    #             default = {}
    #         default.update({
    #             'installment_lines': [],
    #             'date_approved': False,
    #             'date_repayment': False,
    #             'name':False,
    #             'move_id':False,
    #             'state': 'draft'
    #         })
    #         return super(EmployeeLoanDetails, self).copy(default)

    def onchange_loan_type(self, loan_type, employee):
        if loan_type:
            if not employee:
                raise UserError(_('Please specify Employee.'))
            loan_type = self.env['loan.type'].browse(loan_type)
            employee_obj = self.env['hr.employee'].browse(employee)

            allowed_employees = []
            for categ in loan_type.employee_categ_ids:
                allowed_employees += map(lambda x: x.id, categ.employee_ids)
            allowed_employees += map(lambda x: x.id, loan_type.employee_ids)
            if employee not in allowed_employees:
                raise UserError(_('%s  does not Qualify for %s ') % (employee_obj.name, loan_type.name))
        return {}

    def onchange_employee_id(self, employee):
        # TO DO ACCESS RIGHT ISSUE ON PAYSLIP LINE
        self = self.sudo()
        if not employee:
            return {'value': {'loan_policy_ids': []}}
        employee_obj = self.env['hr.employee'].browse(employee)
        policies_on_categ = []
        policies_on_empl = []
        for categ in employee_obj.category_ids:
            if categ.loan_policy:
                policies_on_categ += map(lambda x: x.id, categ.loan_policy)
        if employee_obj.loan_policy:
            policies_on_empl = map(lambda x: x.id, employee_obj.loan_policy)
        domain = [('employee_id', '=', employee), ('contract_id', '=', employee_obj.contract_id.id),
                  ('code', '=', 'GROSS')]
        line_ids = self.env['hr.payslip.line'].search(domain)
        department_id = employee_obj.department_id.id or False
        #         print 'department_id==========',department_id
        address_id = employee_obj.address_home_id or False
        if not address_id:
            raise UserError(_('There is no home/work address defined for employee : %s ') % (_(employee_obj.name)))
        partner_id = address_id and address_id.id or False
        if not partner_id:
            raise UserError(_('There is no partner defined for employee : %s ') % (_(employee_obj.name)))
        gross_amount = 0.0
        if line_ids:
            #             line = self.env['hr.payslip.line'].browse(line_ids)[0]
            line = line_ids[0]
            gross_amount = line.amount

        return {'value': {'department_id': department_id,
                          'loan_policy_ids': list(set(policies_on_categ + policies_on_empl)),
                          'employee_gross': gross_amount,
                          'employee_loan_account': address_id.property_account_receivable_id.id or False}}

    # probuse override to fix issue of  when we apply for a loan first loan policy is selected and when we save loan request the loan policy get removed/disappeared and we have to select loan policy again
    def create(self, vals):
        if type(vals) == list and vals[0].get('employee_id', False):
            employee_id = vals[0]['employee_id']
            employee = self.env['hr.employee'].sudo().browse(employee_id)

            policies_on_categ = []
            policies_on_empl = []
            for categ in employee.category_ids:
                if categ.loan_policy:
                    policies_on_categ += map(lambda x: x.id, categ.loan_policy)
            if employee.loan_policy:
                policies_on_empl += map(lambda x: x.id, employee.loan_policy)

            loan_policy_ids = list(set(policies_on_categ + policies_on_empl))
            vals[0].update({'loan_policy_ids': [(6, 0, loan_policy_ids)]})
        return super(EmployeeLoanDetails, self).create(vals)

    def action_applied(self):
        for user in self:
            if user.actual_principal_amount > user.principal_amount:
                raise UserError(_('The Actual Principal amount cannot be greater than the Principal amount'))
        loans = self.env['employee.loan.details'].search([('employee_id', '=', self.employee_id.id)])
        if loans:
            for loan in loans:
                if self.employee_id.allow_multiple_loan == False:
                    if loan.state != "draft":
                        if loan.total_amount_due != 0:
                            raise ValidationError(
                                "You are not eligible to apply for a loan. Please clear your unhandled balances first")

        for loan in self:
            if not loan.interest_mode:
                if loan.installment_type == 'amount_wise':
                    loan.no_of_months = 0
                elif loan.installment_type == 'month_wise':
                    loan.duration = 0
            contract_obj = self.env['hr.contract'].search(
                [('employee_id', '=', loan.employee_id.id), ('state', '=', 'open')])
            difference = rdelta.relativedelta(datetime.now().date(), contract_obj.date_start)
            if (difference.years >= self.loan_type.servicePeriod):
                self.onchange_loan_type(loan.loan_type.id, loan.employee_id.id)
                msg = ''
                if loan.actual_principal_amount <= 0.0:
                    msg += 'Principal Amount\n '
                if loan.int_payable and loan.int_rate <= 0.0:
                    msg += 'Interest Rate\n '
                if loan.duration:
                    if loan.duration <= 0.0:
                        msg += 'Duration of Loan'
                if msg:
                    raise UserError(_('Please Enter values greater then zero:\n %s ') % (msg))
                status = self.check_employee_loan_qualification(loan)
                if not isinstance(status, bool):
                    raise UserError(_('Loan Policies not satisfied :\n %s ') % (_(status)))
                seq_no = self.env['ir.sequence'].get('employee.loan.details')
                #             self.write({'state':'applied', 'name':seq_no})
                loan.state = 'applied'
                loan.name = seq_no
                loan.date_approved = date.today()
                return True
            else:
                raise ValidationError("You are not eligible to apply for a loan")

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancel'

    #         return self.write({'state':'cancel'})

    @api.model
    def check_employee_loan_qualification(self, loan_obj):
        loan_date_today = loan_obj.date_applied
        loan_date_today_obj = datetime.strptime(str(loan_date_today), DEFAULT_SERVER_DATE_FORMAT)
        msg = 'Mr./Mrs. %s does not meet following Loan policies:' % (loan_obj.employee_id.name)
        qualified = True
        allow_multiple_loan = self._check_multi_loan(loan_obj.employee_id)
        # allow_multiple_loan = filter(None, allow_multiple_loan)  # probuse
        if loan_obj.employee_id.loan_defaulter:
            msg += '\n Blacklisted: You are Blacklisted as loan defaulter and hence you cannot apply for a new loan !'
            qualified = False
        if not allow_multiple_loan:
            loans_list = self.search([('state', '=', 'disburse'), ('employee_id', '=', loan_obj.employee_id.id)],
                                     order='date_applied asc')
            if len(loans_list):
                msg += '\n Multiple loan: Multiple loan is not allowed !'
                qualified = False
        for policy in loan_obj.loan_policy_ids:
            if policy.policy_type == 'maxamt' and policy.max_loan_type == 'fixed':
                if loan_obj.max_loan_amt > 0.0 and loan_obj.actual_principal_amount > loan_obj.max_loan_amt:
                    qualified = False
                    msg += '\n %s :Loan amount is > %s ' % (policy.name, loan_obj.max_loan_amt)

            if policy.policy_type == 'maxamt' and policy.max_loan_type == 'multiple_of_salary':
                latestContract = self.env['hr.contract'].search([('employee_id', '=', loan_obj.employee_id.id)],
                                                                order="create_date desc", limit=1)
                if loan_obj.max_loan_amt > 0.0 and loan_obj.actual_principal_amount > loan_obj.max_loan_amt * latestContract.wage:
                    qualified = False
                    msg += '\n %s :Loan amount is against Loan Policy' % (policy.name)

            #             if policy.policy_type == 'loan_gap' and not allow_multiple_loan: #probuse
            if policy.policy_type == 'loan_gap' and allow_multiple_loan:  # probuse
                loans_list = self.search([('state', '=', 'disburse'), ('employee_id', '=', loan_obj.employee_id.id)],
                                         order='date_applied asc')
                if loans_list:
                    #                     last_loan = self.browse(loans_list[0]) #probuse
                    last_loan = loans_list[0]  # probuse
                    last_loan_date = last_loan.date_applied
                    last_loan_date_obj = datetime.strptime(str(last_loan_date), DEFAULT_SERVER_DATE_FORMAT)
                    diff = last_loan_date_obj + relativedelta(months=int(policy.policy_value))
                    if diff > loan_date_today_obj:
                        qualified = False
                        msg += '\n %s :\n\t\t Last loan date: %s \n\t\tGap required(months) : %s \n\t\tcan apply on/after: %s' \
                               % (policy.name, last_loan_date, policy.policy_value, diff.strftime('%Y-%m-%d'))
            if policy.policy_type == 'eligible_duration':
                contract_date = loan_obj.employee_id.contract_id.date_start
                if contract_date:
                    contract_date_obj = datetime.strptime(str(contract_date), DEFAULT_SERVER_DATE_FORMAT)
                    actual_date = contract_date_obj + relativedelta(months=int(policy.policy_value))
                    if actual_date > loan_date_today_obj:
                        qualified = False
                        msg += '\n %s :\n\t\tContract date: %s  \n\t\tGap required(months):%s \n\t\tcan apply on/after: %s' \
                               % (policy.name, contract_date, policy.policy_value, actual_date.strftime('%Y-%m-%d'))
                else:
                    raise UserError(_('Please Define Contract Date'))
        if not qualified:
            return msg
        return qualified

    def compute_installments(self):
        for loan in self:
            if not len(loan.installment_lines):
                self.create_installments(loan)
            elif loan.int_payable:  # self._context.get('recompute') and
                access_payment = 0.0
                duration_left = 0
                prin_amt_received = 0.0
                total_acc_pay = 0.0
                for install in loan.installment_lines:
                    if install.state in ('paid', 'approve'):
                        prin_amt_received += install.principal_amt
                        if install.balloon_amount >= 1:
                            prin_amt_received += install.balloon_amount
                        continue
                    duration_left += 1
                total_acc_pay = loan.duration - duration_left
                new_p = loan.actual_principal_amount - prin_amt_received
                interest_amt = 0.0
                principal_amt = 0.0
                total = 0.0
                if loan.interest_mode == 'flat':
                    principal_amt = new_p / duration_left
                    if loan.int_payable:
                        # TQ
                        interest_amt = self.flat_rate_method(loan.int_rate, loan.duration)
                    total = principal_amt + interest_amt
                cnt = -1
                if loan.interest_mode == 'reducing':
                    reducing_val = self.reducing_balance_method(new_p, loan.int_rate, duration_left)
                    total_acc_pay = loan.no_of_months - duration_left
                for install in loan.installment_lines:
                    cnt += 1
                    if install.state in ('paid', 'approve'): continue
                    if loan.interest_mode == 'reducing':
                        reducing_val = self.reducing_balance_method(new_p, loan.int_rate, duration_left)
                        principal_amt = reducing_val[cnt - total_acc_pay]['principal_comp']
                        if loan.int_payable:
                            interest_amt = reducing_val[cnt - total_acc_pay]['interest_comp']
                        total = principal_amt + interest_amt
                    install.write({'principal_amt': principal_amt if principal_amt > 0 else 0,
                                   'interest_amt': interest_amt if interest_amt > 0 else 0,
                                   'interest_rate': loan.int_rate,
                                   'total': total})
            else:
                # this is to reload the values
                # loan.write({})
                # for install in loan.installment_lines:
                #     install.write({})

                prin_amt_received = 0.0
                last_installment_date = date.today()
                for install in loan.installment_lines.filtered(lambda x: x.state in ('paid', 'approve')):
                    prin_amt_received += install.principal_amt
                    if install.balloon_amount >= 1:
                        prin_amt_received += install.balloon_amount
                    last_installment_date = install.date_to
                    continue

                loan.installment_lines.filtered(lambda x: x.state not in ['paid', 'approve']).unlink()

                no_of_installment = 0
                after_paid_loan_amount = self.actual_principal_amount - prin_amt_received
                if self.duration:
                    no_of_installment = ((after_paid_loan_amount) / (self.duration))
                    if after_paid_loan_amount < self.duration:
                        raise UserError(_('Amount of installment should be less than Principal amount.'))
                if self.no_of_months and self.interest_mode == False:
                    no_of_installment = self.no_of_months
                no_of_install = math.ceil(no_of_installment)
                installment = int(no_of_install)
                day = last_installment_date.day
                month = last_installment_date.month
                year = last_installment_date.year
                installment_obj = self.env['loan.installment.details']
                total = self.duration if self.duration else (
                        after_paid_loan_amount / self.no_of_months)
                for install_no in range(0, installment):
                    date_from = datetime(year, month, day)
                    date_to = date_from + relativedelta(months=1)
                    day, month, year = date_to.day, date_to.month, date_to.year
                    state = 'unpaid'
                    installment_line = {'install_no': (install_no + len(
                        loan.installment_lines.filtered(lambda x: x.state in ('paid', 'approve')))) + 1,
                                        'date_from': date_from.strftime('%Y-%m-%d'),
                                        'date_to': date_to.strftime('%Y-%m-%d'),
                                        'principal_amt': self.duration if self.duration else (
                                                after_paid_loan_amount / self.no_of_months),
                                        'interest_amt': 0.0,
                                        'total': total,
                                        'loan_id': loan.id,
                                        'interest_rate': loan.int_rate,
                                        'state': state
                                        }
                    installment_obj.create(installment_line)

        self.check_total_amount()
        self._cal_amount_all()
        return True

    @api.model
    def create_installments(self, loan):
        date_approved = time.strftime(DEFAULT_SERVER_DATE_FORMAT)
        if not loan.date_disb:
            raise UserError(_('Please give disbursement date.'))
        else:
            date_disb = loan.date_disb
        date_approved_obj = datetime.strptime(str(date_disb), DEFAULT_SERVER_DATE_FORMAT)
        installment_obj = self.env['loan.installment.details']
        day = date_approved_obj.day
        month = date_approved_obj.month
        year = date_approved_obj.year
        interest_amt = 0.0
        principal_amt = self.actual_principal_amount
        no_of_installment = 0
        if self.duration:
            no_of_installment = ((self.actual_principal_amount) / (self.duration))
            if self.actual_principal_amount < self.duration:
                raise UserError(_('Amount of installment should be less than Principal amount.'))
        if self.no_of_months and self.interest_mode == False:
            no_of_installment = self.no_of_months
        no_of_install = math.ceil(no_of_installment)
        installment = int(no_of_install)
        if not self.interest_mode:
            if self.installment_type == 'amount_wise':
                self.no_of_months = 0
            elif self.installment_type == 'month_wise':
                self.duration = 0
        if loan.int_payable:
            interest_amt = self.flat_rate_method(loan.int_rate, loan.duration)
        total = self.duration if self.duration else (self.actual_principal_amount / self.no_of_months) + interest_amt
        if loan.interest_mode == 'reducing':
            reducing_val = self.reducing_balance_method(loan.actual_principal_amount, loan.int_rate, loan.no_of_months)
            for install_no in range(0, loan.no_of_months):
                date_from = datetime(year, month, day)
                date_to = date_from + relativedelta(months=1)
                if loan.interest_mode == 'reducing':
                    reducing_val = self.reducing_balance_method(loan.actual_principal_amount, loan.int_rate,
                                                                loan.no_of_months)
                    principal_amt = reducing_val[install_no]['principal_comp']
                    if loan.int_payable:
                        interest_amt = reducing_val[install_no]['interest_comp']
                    total = principal_amt + interest_amt
                day, month, year = date_to.day, date_to.month, date_to.year
                state = 'unpaid'
                # if date_from.date() < date.today():
                #     if date_from.date().year < date.today().year:
                #         state = 'paid'
                #     elif date_from.date().month != date.today().month:
                #         state = 'paid'
                # else:
                #     state = 'unpaid'
                installment_line = {'install_no': install_no + 1,
                                    'date_from': date_from.strftime('%Y-%m-%d'),
                                    'date_to': date_to.strftime('%Y-%m-%d'),
                                    'principal_amt': self.duration if self.duration else principal_amt,
                                    'interest_amt': interest_amt,
                                    'total': total,
                                    'loan_id': loan.id,
                                    'interest_rate': loan.int_rate,
                                    'state': state
                                    }
                installment_obj.create(installment_line)
        else:
            for install_no in range(0, installment):
                date_from = datetime(year, month, day)
                date_to = date_from + relativedelta(months=1)
                day, month, year = date_to.day, date_to.month, date_to.year
                state = 'unpaid'
                # if date_from.date() < date.today():
                #     if date_from.date().year < date.today().year:
                #         state = 'paid'
                #     elif date_from.date().month != date.today().month:
                #         state = 'paid'
                # else:
                #     state = 'unpaid'
                installment_line = {'install_no': install_no + 1,
                                    'date_from': date_from.strftime('%Y-%m-%d'),
                                    'date_to': date_to.strftime('%Y-%m-%d'),
                                    'principal_amt': self.duration if self.duration else (
                                            self.actual_principal_amount / self.no_of_months),
                                    'interest_amt': interest_amt,
                                    'total': total,
                                    'loan_id': loan.id,
                                    'interest_rate': loan.int_rate,
                                    'state': state
                                    }
                installment_obj.create(installment_line)
        return True

    def action_disburse(self):
        move_pool = self.env['account.move']
        #         period_pool = self.env['account.period']
        for loan in self:
            if loan.loan_type.disburse_method == 'payroll':
                loan.write({'state': 'disburse'})
                return True
            vals = {}
            #             period_id = period_pool.find(loan.date_applied)[0]
            timenow = time.strftime('%Y-%m-%d')
            address_id = loan.employee_id.address_home_id or False
            partner_id = address_id and address_id and address_id.id or False
            if not partner_id:
                raise UserError(_('Please configure Home Address On Employee.'))
            move = {
                'narration': loan.name,
                'date': loan.date_disb,
                'ref': loan.name,
                'journal_id': loan.journal_id.id,
                #                 'period_id': period_id.id,
            }

            credit_account_id = loan.journal_id.default_account_id
            if not loan.journal_id:
                raise UserError(_('Please configure Disburse Journal.'))
            if not credit_account_id:
                raise UserError(_('Please configure Debit/Credit accounts on the Journal %s ') % (loan.journal_id.name))
            credit_account_id = credit_account_id.id
            debit_account_id = loan.employee_loan_account.id or False
            if not debit_account_id:
                raise UserError(_('Please configure debit account of employee'))

            debit_line = (0, 0, {
                'name': _('Loan of %s') % (loan.employee_id.name),
                'date': loan.date_disb,
                'partner_id': partner_id,
                'account_id': debit_account_id,
                'journal_id': loan.journal_id.id,
                #                     'period_id': period_id.id,
                'debit': loan.actual_principal_amount,
                'credit': 0.0,
            })
            credit_line = (0, 0, {
                'name': _('Loan of %s') % (loan.employee_id.name),
                'date': loan.date_disb,
                'partner_id': partner_id,
                'account_id': credit_account_id,
                'journal_id': loan.journal_id.id,
                #                     'period_id': period_id.id,
                'debit': 0.0,
                'credit': loan.actual_principal_amount,
            })
            move.update({'line_ids': [debit_line, credit_line]})
            move_id = move_pool.create(move)
            date_disb = time.strftime(DEFAULT_SERVER_DATE_FORMAT)
            if not loan.date_disb:
                vals.update(state='disburse', move_id=move_id.id, date_disb=date_disb)
            else:
                vals.update(state='disburse', move_id=move_id.id)
            loan.write(vals)
        #             if loan.journal_id.entry_posted:#todoprobuse
        #             move_id.post()
        return True

    def action_approved(self):
        date_approved = time.strftime(DEFAULT_SERVER_DATE_FORMAT)
        date_approved_obj = datetime.strptime(str(date_approved), DEFAULT_SERVER_DATE_FORMAT)
        for loan in self:
            vals = {}
            if not loan.date_approved:
                vals.update(
                    date_approved=date_approved,
                    state='approved')
            else:
                vals.update(state='approved')

            self.write(vals)
        return True

    def action_rejected(self):
        #         print "---------------action_rejected------"
        for rec in self:
            rec.state = 'rejected'

    #         return self.write({'state':'rejected'})

    def action_paid(self):
        for rec in self:
            rec.state = 'paid'

    def action_reset(self):
        #         print "-----------action_reset----------"
        #         self.write({'state':'draft'})
        for rec in self:
            rec.state = 'draft'
        # from openerp import workflow
        # workflow.trg_delete(self._uid, self._name, self.id, self._cr)
        # workflow.trg_create(self._uid, self._name, self.id, self._cr)
        #        self.workflow_delete()
        #        self.workflow_create()
        return True

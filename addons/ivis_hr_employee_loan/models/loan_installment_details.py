import time
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class LoanInstallmentDetail(models.Model):
    _name = 'loan.installment.details'
    _description = 'Loan Installment'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.onchange('principal_amt')
    @api.depends('principal_amt', 'interest_amt')
    def update_interest_amount(self):
        if self.principal_amt:
            self.total = self.principal_amt + self.interest_amt

    # _order = "loan_id desc"

    #    @api.multi
    #    @api.depends('loan_id', 'loan_id.loan_type')
    #    def _check_status(self):
    #        payslip_obj = self.env['hr.payslip']
    #        for install in self:
    #            if install.loan_id:
    #                if install.loan_id.loan_type.payment_method == 'salary' and install.loan_id.state == 'disburse':
    #                    payslips = payslip_obj.search([('contract_id', '=', install.loan_id.employee_id.contract_id.id),
    #                                                 ('date_to', '>=', install.date_from),
    #                                                 ('date_to', '<=', install.date_to)])
    #                    for slip in payslips:
    #                        if slip.state == 'done':
    #                            for line in slip.line_ids:
    #                                if line.salary_rule_id.loan_deduction:
    #                                    install.check_status = True
    #                                    break
    #                            if install.check_status:
    #                                self._cr.execute("update loan_installment_details set state='paid' where id = %s" % (install.id))
    #                                break

    @api.depends('loan_id', 'install_no')
    def _get_name(self):
        for install in self:
            install.name = install.loan_id and install.loan_id.name or '' + '/Install/' + str(install.install_no)

    #    test_prepayment_id = fields.Many2one(
    #        'loan.prepayment',
    #        string='Prepayment',
    #        required=False
    #    )
    name = fields.Char(
        compute='_get_name',
        string='Name',
        store=True
    )
    install_no = fields.Integer(
        string='Number',
        required=True,
        readonly=False,
        help='Installment number.'
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        readonly=True,
        default=lambda self: self.env.user.company_id.currency_id
    )
    loan_id = fields.Many2one(
        'employee.loan.details',
        string='Loan',
        readonly=True,
        required=False
    )
    date_from = fields.Date(
        string='Date From',
        readonly=False,
    )
    date_to = fields.Date(
        string='Date To',
        readonly=False,
    )
    principal_amt = fields.Float(
        string='Principal Amount',
        digits=(16, 2),
        readonly=False,
    )
    amount_already_paid = fields.Float(
        string='Amount Already Paid',
        digits=(16, 2),
        readonly=True,
    )
    interest_amt = fields.Float(
        string='Interest Amount',
        digits=(16, 2),
        readonly=False,
    )
    interest_rate = fields.Float(
        string="Rate",
        readonly=True,
    )
    int_payable = fields.Boolean(
        related='loan_id.int_payable',
        string='Interest Payable',
    )
    loan_type = fields.Many2one(
        related='loan_id.loan_type',
        string='Loan Type',
        store=True
    )
    loan_repayment_method = fields.Selection(
        related='loan_type.payment_method',
        string='Loan Repayment Method',
        store=True,
    )  # probuse
    loan_state = fields.Selection(
        related='loan_id.state',
        string='Loan State',
        store=True
    )
    balloon_amount = fields.Float(string='Balloon Amount')

    total = fields.Float(
        string='EMI (Installment)',
        digits=(16, 2),
        readonly=False,
        help='Equated monthly installments.'
    )
    employee_id = fields.Many2one(
        related='loan_id.employee_id',
        store=True,
        string='Employee',
        readonly=True
    )
    move_id = fields.Many2one(
        'account.move',
        string='Accounting Entry',
        readonly=True
    )
    int_move_id = fields.Many2one(
        'account.move',
        string='Interest Accounting Entry',
        readonly=False
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        readonly=True,
        default=lambda self: self.env.user.company_id
    )
    #    check_status = fields.Boolean(
    #        compute='_check_status',
    #        string='Check Status',
    #        store=True
    #    )
    state = fields.Selection(
        selection=[
            ('unpaid', 'Unpaid'),
            ('approve', 'Approved'),
            ('paid', 'Paid')],
        string='State',
        readonly=False,
        default='unpaid',
    )

    def action_reset(self):
        #         print "==============action_reset============="
        for rec in self:
            rec.state = 'unpaid'

    #         return self.write({'state':'unpaid'})

    def action_approve(self):
        for rec in self:
            rec.state = 'approve'

    #         print "========'=action_approve========="
    #         return self.write({'state':'approve'})

    def book_interest(self):  # todoprobuse
        move_pool = self.env['account.move']
        #         period_pool = self.env['account.period']
        for installment in self:
            if installment.loan_id.loan_type.payment_method == 'cash':
                if installment.loan_id:
                    if installment.loan_id.state != 'disburse':
                        raise UserError(_('Loan is not Disbursed yet !'))
                    if installment.int_move_id:
                        raise UserError(_('Book interest entry is already generated !'))
                #             period_id = period_pool.find(installment.date_from)[0]
                timenow = time.strftime('%Y-%m-%d')
                address_id = installment.loan_id.employee_id.address_home_id or False
                partner_id = address_id and address_id.id or False

                if not partner_id:
                    raise UserError(_('Please configure Home Address for Employee !'))

                move = {
                    'narration': installment.loan_id.name,
                    'date': installment.date_from,
                    'ref': installment.install_no,
                    'journal_id': installment.loan_id.journal_id2.id,
                    #                 'period_id': period_id,
                }
                #                 debit_account_id = installment.loan_id.journal_id2.default_account_id
                #                 if not debit_account_id:
                #                     raise UserError( _('Please configure Debit/Credit accounts on the Journal %s ') % (installment.journal_id.name))
                #                 debit_account_id = debit_account_id.id
                deb_interest_line = (0, 0, {
                    'name': _('Interest of loan %s') % (installment.loan_id.name),
                    'date': installment.date_from,
                    'partner_id': partner_id,
                    'account_id': installment.loan_id.employee_loan_account.id,
                    'journal_id': installment.loan_id.journal_id2.id,
                    #                     'period_id': period_id,
                    'debit': installment.interest_amt,
                    'credit': 0.0
                })

                cred_interest_line = (0, 0, {
                    'name': _('Interest of loan %s') % (installment.loan_id.name),
                    'date': installment.date_from,
                    'partner_id': partner_id,
                    'account_id': installment.loan_id.loan_type.loan_interest_account.id,
                    'journal_id': installment.loan_id.journal_id2.id,
                    #                     'period_id': period_id,
                    'credit': installment.interest_amt,
                    'debit': 0.0
                })
                move.update({'line_ids': [deb_interest_line, cred_interest_line]})
                inst_move_id = move_pool.create(move)
                installment.write({'int_move_id': inst_move_id.id})
        #             if installment.loan_id.journal_id2.entry_posted:
        #                 inst_move_id.post()
        return True

    def book_interest1(self):  # ok
        move_pool = self.env['account.move']
        #         period_pool = self.env['account.period']
        for installment in self:
            #            if installment.loan_id:
            #                if installment.loan_id.state == 'draft':
            #                    raise UserError(_('Loan is not confirm/Approved yet !'))
            #                if installment.int_move_id:
            #                    raise UserError(_('Book interest entry is already generated !'))
            #             period_id = period_pool.find(installment.date_from)[0]
            timenow = time.strftime('%Y-%m-%d')
            address_id = installment.loan_id.emp_id.address_home_id or False
            partner_id = address_id and address_id.id or False

            if not partner_id:
                raise UserError(_('Please configure Home Address for Employee !'))

            move = {
                'narration': installment.loan_id.name,
                'date': installment.date_from,
                'ref': installment.install_no,
                'journal_id': installment.loan_id.journal_id2.id,
                #                 'period_id': period_id,
            }
            #             debit_account_id = installment.loan_id.journal_id2.default_account_id
            #             if not debit_account_id:
            #                 raise UserError( _('Please configure Debit/Credit accounts on the Journal %s ') % (installment.loan_id.journal_id2.name))
            #             debit_account_id = debit_account_id.id
            if not installment.loan_id.employee_loan_account:
                raise UserError(_('Please configure Employee account.'))
            deb_interest_line = (0, 0, {
                'name': _('Interest of loan %s') % (installment.loan_id.name),
                'date': installment.date_from,
                'partner_id': partner_id,
                'account_id': installment.loan_id.employee_loan_account.id,
                'analytic_account_id': installment.loan_id.account_analytic_id.id or False,
                'journal_id': installment.loan_id.journal_id2.id,
                #                     'period_id': period_id,
                'debit': installment.interest_amt,
                'credit': 0.0
            })
            cred_interest_line = (0, 0, {
                'name': _('Interest of loan %s') % (installment.loan_id.name),
                'date': installment.date_from,
                'partner_id': partner_id,
                'account_id': installment.loan_id.loan_type.loan_interest_account.id,
                'journal_id': installment.loan_id.journal_id2.id,
                #                     'period_id': period_id,
                'credit': installment.interest_amt,
                'debit': 0.0
            })
            move.update({'line_ids': [deb_interest_line, cred_interest_line]})
            inst_move_id = move_pool.create(move)
            installment.write({'int_move_id': inst_move_id.id})
        #             if installment.loan_id.journal_id2.entry_posted:#todoprobuse
        #                 inst_move_id.post()
        #             inst_move_id.post()
        return True

    def pay_installment1(self):  # ok
        ctx = dict(self._context or {})
        ctx.update(recompute=True)
        move_pool = self.env['account.move']
        #         period_pool = self.env['account.period']
        for installment in self:
            if installment.loan_id.loan_type.payment_method == 'cash':
                #                 period_id = period_pool.find(installment.date_from)[0]
                timenow = time.strftime('%Y-%m-%d')
                address_id = installment.loan_id.emp_id.address_home_id or False
                partner_id = address_id and address_id.id or False

                if not partner_id:
                    raise UserError(_('Please configure Home Address for Employee !'))

                move = {
                    'narration': installment.loan_id.name,
                    'date': installment.date_from,
                    'ref': installment.install_no,
                    'journal_id': installment.loan_id.journal_id1.id,
                    #                     'period_id': period_id,
                }
                if not installment.loan_id.journal_id1.default_account_id:
                    raise UserError(_('Please configure Debit/Credit accounts on the Journal %s ') % (
                        installment.loan_id.journal_id1.name))
                if not installment.loan_id.employee_loan_account:
                    raise UserError(_('Please give employee account.'))
                debit_line = (0, 0, {
                    'name': _('EMI of loan %s') % (installment.loan_id.name),
                    'date': installment.date_from,
                    'partner_id': partner_id,
                    'account_id': installment.loan_id.journal_id1.default_account_id.id,
                    'journal_id': installment.loan_id.journal_id1.id,
                    #                         'period_id': period_id,
                    'debit': installment.total,
                    'credit': 0.0,
                })
                credit_line = (0, 0, {
                    'name': _('EMI of loan %s') % (installment.loan_id.name),
                    'date': installment.date_from,
                    'partner_id': partner_id,
                    'account_id': installment.loan_id.employee_loan_account.id,
                    'journal_id': installment.loan_id.journal_id1.id,
                    #                         'period_id': period_id,
                    'debit': 0.0,
                    'analytic_account_id': installment.loan_id.account_analytic_id.id or False,
                    'credit': installment.total,
                })
                move.update({'line_ids': [debit_line, credit_line]})
                move_id = move_pool.create(move)
                installment.write({'state': 'paid', 'move_id': move_id.id})
                #                 if installment.loan_id.journal_id1.entry_posted:
                #                     move_id.post()#todoprobuse
                #                 move_id.post()
                #                self.pool.get('employee.loan.details').compute_installments(cr, uid, [installment.loan_id.id], context=context)
                ctx.pop('recompute')
        return True

    def pay_installment(self):  # ok #probusetodo when call from form view of opening balance
        ctx = dict(self._context or {})
        move_pool = self.env['account.move']
        #         period_pool = self.env['account.period']
        for installment in self:
            # if installment.loan_id.state != 'disburse':
            #     raise UserError(_('Loan is not Disbursed yet !'))
            if installment.loan_id.loan_type.payment_method == 'cash':
                #                 period_id = period_pool.find(installment.date_from)[0]
                timenow = time.strftime('%Y-%m-%d')
                address_id = installment.loan_id.employee_id.address_home_id or False
                partner_id = address_id and address_id.id or False

                if not partner_id:
                    raise UserError(_('Please configure Home Address for Employee !'))

                move = {
                    'narration': installment.loan_id.name,
                    'date': installment.date_from,
                    'ref': installment.install_no,
                    'journal_id': installment.loan_id.journal_id1.id,
                    #                     'period_id': period_id,
                }
                if not installment.loan_id.journal_id1.default_account_id:
                    raise UserError(
                        _('Please configure Debit/Credit accounts on the Journal %s ') % (self.journal_id1.name))
                debit_line = (0, 0, {
                    'name': _('EMI of loan %s') % (installment.loan_id.name),
                    'date': installment.date_from,
                    'partner_id': partner_id,
                    'account_id': installment.loan_id.journal_id1.default_account_id.id,
                    'journal_id': installment.loan_id.journal_id1.id,
                    #                         'period_id': period_id,
                    'debit': installment.total,
                    'credit': 0.0,
                })
                credit_line = (0, 0, {
                    'name': _('EMI of loan %s') % (installment.loan_id.name),
                    'date': installment.date_from,
                    'partner_id': partner_id,
                    'account_id': installment.loan_id.employee_loan_account.id,
                    'journal_id': installment.loan_id.journal_id1.id,
                    #                         'period_id': period_id,
                    'debit': 0.0,
                    'credit': installment.total,
                })
                move.update({'line_ids': [debit_line, credit_line]})
                move_id = move_pool.create(move)
                installment.write({'state': 'paid', 'move_id': move_id.id})
                #                 if installment.loan_id.journal_id.entry_posted:#todoprobuse
                #                     move_id.post()
                #                 move_id.post()
                installment.loan_id.compute_installments()
                if ctx.get('recompute'):
                    ctx.pop('recompute')
            else:
                installment.write({'state': 'paid'})
        return True

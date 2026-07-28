from odoo import models, fields
from odoo.exceptions import ValidationError, UserError
from odoo.tools import float_is_zero, float_compare
from odoo.tools.translate import _


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def action_payslip_done(self):
        res = super(HrPayslip, self).action_payslip_done()
        precision = self.env['decimal.precision'].precision_get('Payroll')

        payslips_to_post = self.filtered(lambda slip: not slip.payslip_run_id)
        payslip_runs = (self - payslips_to_post).mapped('payslip_run_id')
        for run in payslip_runs:
            if run._are_payslips_ready():
                payslips_to_post |= run.slip_ids

        payslips_to_post = payslips_to_post.filtered(lambda slip: slip.state == 'done' and not slip.move_id)

        if any(not payslip.struct_id for payslip in payslips_to_post):
            raise ValidationError(_('One of the contract for these payslips has no structure type.'))
        if any(not structure.journal_id for structure in payslips_to_post.mapped('struct_id')):
            raise ValidationError(_('One of the payroll structures has no account journal defined on it.'))

        for slip in payslips_to_post:
            slip_mapped_data = {
                slip.struct_id.journal_id.id: {fields.Date().end_of(slip.date_to, 'month'): self.env['hr.payslip']} for
                slip
                in payslips_to_post}
            slip_mapped_data[slip.struct_id.journal_id.id][fields.Date().end_of(slip.date_to, 'month')] |= slip

            for journal_id in slip_mapped_data:
                for slip_date in slip_mapped_data[journal_id]:
                    line_ids = []
                    debit_sum = 0.0
                    credit_sum = 0.0
                    date = slip_date
                    move_dict = {
                        'narration': '',
                        'ref': date.strftime('%B %Y'),
                        'journal_id': journal_id,
                        'date': date,
                    }

                    for slip in slip_mapped_data[journal_id][slip_date]:
                        move_dict['narration'] += slip.number or '' + ' - ' + slip.employee_id.name or ''
                        move_dict['narration'] += '\n'
                        move_dict['partner_id'] = slip.employee_id.address_home_id.id
                        line_ids = []

                        for line in slip.line_ids.filtered(lambda line: line.category_id):
                            amount = -line.total if slip.credit_note else line.total
                            if line.code == 'NETYB':
                                for tmp_line in slip.line_ids.filtered(lambda line: line.category_id):
                                    if tmp_line.salary_rule_id.not_computed_in_net:
                                        if amount > 0:
                                            amount -= abs(tmp_line.total)
                                        elif amount < 0:
                                            amount += abs(tmp_line.total)
                            if float_is_zero(amount, precision_digits=precision):
                                continue
                            debit_account_id = line.salary_rule_id.account_debit.id
                            credit_account_id = line.salary_rule_id.account_credit.id

                            if debit_account_id:
                                debit = amount if amount > 0.0 else 0.0
                                credit = -amount if amount < 0.0 else 0.0

                                line_vals = {
                                    'name': line.name,
                                    'partner_id': slip.employee_id.address_home_id.id,
                                    'account_id': debit_account_id,
                                    'journal_id': slip.struct_id.journal_id.id,
                                    'date': date,
                                    'debit': debit,
                                    'credit': credit,
                                    'analytic_account_id': line.salary_rule_id.analytic_account_id.id or slip.contract_id.analytic_account_id.id,
                                }
                                line_ids.append(line_vals)

                            if credit_account_id:
                                debit = -amount if amount < 0.0 else 0.0
                                credit = amount if amount > 0.0 else 0.0

                                line_vals = {
                                    'name': line.name,
                                    'partner_id': slip.employee_id.address_home_id.id,
                                    'account_id': credit_account_id,
                                    'journal_id': slip.struct_id.journal_id.id,
                                    'date': date,
                                    'debit': debit,
                                    'credit': credit,
                                    'analytic_account_id': line.salary_rule_id.analytic_account_id.id or slip.contract_id.analytic_account_id.id,
                                }
                                line_ids.append(line_vals)

                        for line_id in line_ids:
                            debit_sum += line_id['debit']
                            credit_sum += line_id['credit']

                        if float_compare(credit_sum, debit_sum, precision_digits=precision) == -1:
                            acc_id = slip.journal_id.default_account_id.id
                            if not acc_id:
                                raise UserError(
                                    _('The Expense Journal "%s" has not properly configured the Credit Account!') % (
                                        slip.journal_id.name))
                            existing_adjustment_line = (
                                line_id for line_id in line_ids if line_id['name'] == _('Adjustment Entry')
                            )
                            adjust_credit = next(existing_adjustment_line, False)

                            if not adjust_credit:
                                adjust_credit = {
                                    'name': _('Adjustment Entry'),
                                    'partner_id': False,
                                    'account_id': acc_id,
                                    'journal_id': slip.journal_id.id,
                                    'date': date,
                                    'debit': 0.0,
                                    'credit': debit_sum - credit_sum,
                                }
                                line_ids.append(adjust_credit)
                            else:
                                adjust_credit['credit'] = debit_sum - credit_sum

                        elif float_compare(debit_sum, credit_sum, precision_digits=precision) == -1:
                            acc_id = slip.journal_id.default_account_id.id
                            if not acc_id:
                                raise UserError(
                                    _('The Expense Journal "%s" has not properly configured the Debit Account!') % (
                                        slip.journal_id.name))
                            existing_adjustment_line = (
                                line_id for line_id in line_ids if line_id['name'] == _('Adjustment Entry')
                            )
                            adjust_debit = next(existing_adjustment_line, False)

                            if not adjust_debit:
                                adjust_debit = {
                                    'name': _('Adjustment Entry'),
                                    'partner_id': False,
                                    'account_id': acc_id,
                                    'journal_id': slip.journal_id.id,
                                    'date': date,
                                    'debit': credit_sum - debit_sum,
                                    'credit': 0.0,
                                }
                                line_ids.append(adjust_debit)
                            else:
                                adjust_debit['debit'] = credit_sum - debit_sum

                        move_dict['line_ids'] = [(0, 0, line_vals) for line_vals in line_ids]
                        move = self.env['account.move'].create(move_dict)
                        slip.write({'move_id': move.id, 'date': date})
        return res

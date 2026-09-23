# -*- coding: utf-8 -*-
from collections import defaultdict

from odoo import models, fields, api,_

from server.odoo.exceptions import UserError


class HrPayslipInherit(models.Model):
    _inherit = 'hr.payslip'

    i_tax_wage = fields.Monetary(compute='_compute_i_tax_net', store=True) #Monthly Income tax
    car_loan_wage = fields.Monetary(compute='_compute_i_tax_net', store=True) #Car Loan
    pf_loan_wi_wage = fields.Monetary(compute='_compute_i_tax_net', store=True) #PF Loan With INterest
    pf_interest_wage = fields.Monetary(compute='_compute_i_tax_net', store=True) #PF Interst Amount
    pf_emp_cont_wage = fields.Monetary(compute='_compute_i_tax_net', store=True) #PF Employee Contribuution
    bonus_wage = fields.Monetary(compute='_compute_i_tax_net', store=True) #Employee Annual Bonus

    @api.depends('line_ids.total')
    def _compute_i_tax_net(self):
        line_values = (self._origin)._get_line_values(['CURRENT_INCOME_TAX','CLOAN','PFLWI','PFLIA','PF_EMPLOYEE','BONUS'])
        for payslip in self:
            payslip.i_tax_wage = line_values['CURRENT_INCOME_TAX'][payslip._origin.id]['total']
            payslip.car_loan_wage = line_values['CLOAN'][payslip._origin.id]['total']
            payslip.pf_loan_wi_wage = line_values['PFLWI'][payslip._origin.id]['total']
            payslip.pf_interest_wage = line_values['PFLIA'][payslip._origin.id]['total']
            payslip.pf_emp_cont_wage = line_values['PF_EMPLOYEE'][payslip._origin.id]['total']
            payslip.bonus_wage = line_values['BONUS'][payslip._origin.id]['total']

    def _get_line_values(self, code_list, vals_list=None, compute_sum=False):
        if vals_list is None:
            vals_list = ['total']
        valid_values = {'quantity', 'amount', 'total', 'ytd'}
        if set(vals_list) - valid_values:
            raise UserError(
                _('The following values are not valid:\n%s', '\n'.join(list(set(vals_list) - valid_values))))
        result = defaultdict(lambda: defaultdict(lambda: dict.fromkeys(vals_list, 0.0)))
        if not self or not code_list:
            return result
        self.env.flush_all()
        selected_fields = ','.join('SUM(%s) AS %s' % (vals, vals) for vals in vals_list)
        self.env.cr.execute("""
               SELECT
                   p.id,
                   pl.code,
                   %s
               FROM hr_payslip_line pl
               JOIN hr_payslip p
               ON p.id IN %s
               AND pl.slip_id = p.id
               AND pl.code IN %s
               GROUP BY p.id, pl.code
           """ % (selected_fields, '%s', '%s'), (tuple(self.ids), tuple(code_list)))
        # self = hr.payslip(1, 2)
        # request_rows = [
        #     {'id': 1, 'code': 'IP', 'total': 100, 'quantity': 1},
        #     {'id': 1, 'code': 'IP.DED', 'total': 200, 'quantity': 1},
        #     {'id': 2, 'code': 'IP', 'total': -2, 'quantity': 1},
        #     {'id': 2, 'code': 'IP.DED', 'total': -3, 'quantity': 1}
        # ]
        request_rows = self.env.cr.dictfetchall()
        # result = {
        #     'IP': {
        #         'sum': {'quantity': 2, 'total': 300},
        #         1: {'quantity': 1, 'total': 100},
        #         2: {'quantity': 1, 'total': 200},
        #     },
        #     'IP.DED': {
        #         'sum': {'quantity': 2, 'total': -5},
        #         1: {'quantity': 1, 'total': -2},
        #         2: {'quantity': 1, 'total': -3},
        #     },
        # }
        for row in request_rows:
            code = row['code']
            payslip_id = row['id']
            for vals in vals_list:
                if compute_sum:
                    result[code]['sum'][vals] += row[vals] or 0.0
                result[code][payslip_id][vals] += row[vals] or 0.0
        return result


class HrEmployeeInherit(models.Model):
    _inherit = 'hr.employee'

    travel_department_id = fields.Many2one('hr.department', string='Travel Department', store=True)
    mobile_allowance = fields.Float(string='Mobile Allowance')
    is_pec_certified = fields.Boolean(string='PEC?')
    pec_certificate_expiry = fields.Date(string="PEC Exp. Date")
from odoo import models, api

class LoanReport(models.AbstractModel):
    _name = 'report.ivis_hr_employee_loan.loan_report_template'
    _description = 'Loan Report'

    def _get_loan_data(self, data):
        field_mapping = {
            'principal': 'principal_amount',
            'state': 'state',
            'applied': 'date_applied',
            'approved': 'date_approved',
            'rejected': 'date_repayment',
            'loan_type': 'loan_type'
        }

        domain = []
        filter_type = data.get('filter')
        condition = data.get('condition')

        if filter_type in ('applied', 'approved', 'rejected'):
            field = field_mapping[filter_type]
            if condition == 'range':
                domain.extend([
                    (field, '>=', data.get('date1')),
                    (field, '<=', data.get('date2'))
                ])
            else:
                domain.append((field, condition, data.get('date1')))

        elif filter_type == 'principal':
            field = field_mapping['principal']
            if condition == 'range':
                domain.extend([
                    (field, '>=', data.get('amount1')),
                    (field, '<=', data.get('amount2'))
                ])
            else:
                domain.append((field, condition, data.get('amount1')))

        elif filter_type == 'loan_type':
            domain.append((field_mapping['loan_type'], '=', data.get('loan_type')[0]))

        else:
            domain.append((field_mapping['state'], '=', data.get('state')))

        if data.get('employee_ids'):
            domain.append(('employee_id', 'in', data.get('employee_ids')))

        return self.env['employee.loan.details'].search(domain)

    @api.model
    def _get_report_values(self, docids, data=None):
        loan_records = self._get_loan_data(data)
        return {
            'doc_ids': loan_records.ids,
            'doc_model': 'employee.loan.details',
            'docs': loan_records,
            'get_lines': self._get_lines,
        }

    def _get_lines(self, lines):
        res = []
        open_amt = 0.0
        for count, line in enumerate(lines, 1):
            if count == 1 or line.install_no == 1:
                open_amt = line.loan_id.principal_amount

            access = round(line.total - (line.principal_amt + line.interest_amt), 2)
            closing_bal = round(open_amt - line.principal_amt - access, 2)

            res.append({
                'no': line.install_no,
                'emi': line.total,
                'principal': line.principal_amt,
                'opening_bal': open_amt,
                'interest': line.interest_amt,
                'closing_bal': closing_bal if closing_bal >= 0 else 0.0,
                'state': line.state,
                'date_from': line.date_from,
                'date_to': line.date_to
            })

            open_amt = closing_bal if closing_bal >= 0 else 0.0

        return res

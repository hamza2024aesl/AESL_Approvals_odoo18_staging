import calendar
import datetime
from odoo import models


class ProvidentFundsReport(models.AbstractModel):
    _name = 'provident.funds.report'
    _description = 'Provident Fund Report'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, obj):

        if obj.employee_ids:
            all_employees = obj.employee_ids
        else:
            all_employees = self.env['hr.employee'].search([])

        format1 = workbook.add_format({'font_size': 18, 'align': 'center', 'bold': True})
        format2 = workbook.add_format({'font_size': 11, 'align': 'center', 'bold': True})
        num_fmt = workbook.add_format({'num_format': '#,##0.00'})

        sheet = workbook.add_worksheet("Report")
        sheet.write(1, 4, obj.current_company.name, format1)
        # sheet.write(3, 3, 'Current Date: ', format2)
        sheet.write(3, 3, '', format2)

        bold = workbook.add_format({"bold": True, 'align': 'center'})
        date_format = workbook.add_format({'num_format': 'd mmm yyyy', 'align': 'left'})

        # sheet.write(3, 4, obj.current_month, date_format)
        sheet.write(3, 4, f'01-Jan-{obj.current_month.year} to 31-Dec-{obj.current_month.year}',
                    workbook.add_format({'align': 'center', 'bold': True}))

        col = 3
        row = 5

        for employee in all_employees:
            current_year = obj.current_month.year
            # current_date = datetime.date.today()
            # current_year = current_date.year
            first_day_of_current_year = datetime.datetime(current_year, 1, 1)

            payslips_of_current_year = self.env['hr.payslip'].search(
                [('employee_id', '=', employee.id), ('date_from', '>=', first_day_of_current_year)], order='date_from')

            current_year_employee_contributions = 0
            current_year_employer_contributions = 0

            for payslip in payslips_of_current_year:
                current_year_employee_contributions += payslip.line_ids.filtered(lambda x: x.code == 'PF').total
                current_year_employer_contributions += payslip.line_ids.filtered(lambda x: x.code == 'PFEC').total

            opening_basic = 0
            opening_employee_contributions = employee.pf_employee + employee.employee_contribution - abs(
                current_year_employee_contributions)
            opening_employer_contributions = employee.pf_employer + employee.employer_contribution - abs(
                current_year_employer_contributions)

            total_opening_contribution = opening_employer_contributions + opening_employee_contributions
            opening_dividend_accumu = employee.pf_interest
            grand_total = total_opening_contribution + opening_dividend_accumu

            sheet.write(row, col, 'Name', bold)
            sheet.write(row, col + 1, employee.name)
            row += 1
            contract = self.env['hr.contract'].search([('state', '=', 'open'), ('employee_id', '=', employee.id)],
                                                      limit=1)
            sheet.write(row, col, 'Confirmation Date', bold)
            sheet.write(row, col + 1, contract.date_start, date_format)
            row += 2
            sheet.write(row, col, '')
            sheet.write(row, col + 1, 'BASIC SALARY', bold)
            sheet.write(row, col + 2, 'CONTRIBUTION BY EMPLOYEE', bold)
            sheet.write(row, col + 3, 'TOTAL CONTRIBUTION BY EMPLOYEE', bold)
            sheet.write(row, col + 4, 'CONTRIBUTION BY EMPLOYER', bold)
            sheet.write(row, col + 5, 'TOTAL CONTRIBUTION BY EMPLOYER', bold)
            sheet.write(row, col + 6, 'TOTAL CONTRIBUTION', bold)
            sheet.write(row, col + 7, 'DIVIDEND ALLUMU', bold)
            sheet.write(row, col + 8, 'GRAND TOTAL', bold)
            row += 1

            sheet.write(row, col, 'BAL B/F', bold)
            sheet.write(row, col + 1, opening_basic, num_fmt)
            sheet.write(row, col + 2, opening_employee_contributions, num_fmt)
            sheet.write(row, col + 3, opening_employee_contributions, num_fmt)
            sheet.write(row, col + 4, opening_employer_contributions, num_fmt)
            sheet.write(row, col + 5, opening_employer_contributions, num_fmt)
            sheet.write(row, col + 6, total_opening_contribution, num_fmt)
            sheet.write(row, col + 7, opening_dividend_accumu, num_fmt)
            sheet.write(row, col + 8, grand_total, num_fmt)
            row += 1
            total_employee_contribution = opening_employee_contributions
            total_employer_contribution = opening_employer_contributions

            for payslip in payslips_of_current_year:
                month = calendar.month_name[payslip.date_from.month]
                basic = payslip.line_ids.filtered(lambda x: x.code == 'BASIC').total
                employee_contribution = abs(payslip.line_ids.filtered(lambda x: x.code == 'PF').total)
                total_employee_contribution += employee_contribution
                employer_contribution = abs(payslip.line_ids.filtered(lambda x: x.code == 'PFEC').total)
                total_employer_contribution += employer_contribution
                total_contribution = total_employee_contribution + total_employer_contribution

                if month == "January":
                    dividend_accumu = employee.interest
                else:
                    dividend_accumu = 0
                grand_total = total_contribution + dividend_accumu

                sheet.write(row, col, month, bold)
                sheet.write(row, col + 1, basic, num_fmt)
                sheet.write(row, col + 2, employee_contribution, num_fmt)
                sheet.write(row, col + 3, total_employee_contribution, num_fmt)
                sheet.write(row, col + 4, employer_contribution, num_fmt)
                sheet.write(row, col + 5, total_employer_contribution, num_fmt)
                sheet.write(row, col + 6, total_contribution, num_fmt)
                sheet.write(row, col + 7, dividend_accumu, num_fmt)
                sheet.write(row, col + 8, grand_total, num_fmt)
                row += 1

            row += 3
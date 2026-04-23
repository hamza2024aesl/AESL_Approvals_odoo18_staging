import string
from odoo import models, fields


class PayrollReportOne(models.AbstractModel):
    _name = 'report.xlsx_payroll_report.xlsx_payroll_report_one'
    _inherit = 'report.report_xlsx.abstract'
    _description = "Payroll Report One"

    def generate_xlsx_report(self, workbook, data, lines):
        format1 = workbook.add_format({
            'font_size': 12,
            'align': 'vcenter',
            'bold': True,
            'bg_color': '#d3dde3',
            'color': 'black',
             'bottom': True,
        })
        format2 = workbook.add_format({
            'font_size': 12,
            'align': 'vcenter',
            'bold': True,
            'bg_color': '#edf4f7',
            'color': 'black',
            'num_format': '#,##0.00'
        })
        format3 = workbook.add_format({
            'font_size': 11,
            'align': 'vcenter',
            'bold': False,
            'num_format': '#,##0.00'
        })
        format3_colored = workbook.add_format({
            'font_size': 11,
            'align': 'vcenter',
            'bg_color': '#f7fcff',
            'bold': False,
            'num_format': '#,##0.00'
        })
        format4 = workbook.add_format({
            'font_size': 12,
            'align': 'vcenter',
            'bold': True
        })
        format5 = workbook.add_format({
            'font_size': 12,
            'align': 'vcenter',
            'bold': False
        })
        # sheet = workbook.add_worksheet('Payslip Report')

        # Fetch available salary rules:
        used_structures = []
        for sal_structure in lines.slip_ids.struct_id:
            if sal_structure.id not in used_structures:
                used_structures.append([sal_structure.id, sal_structure.name])

        # Logic for each workbook, i.e. group payslips of each salary structure into a separate sheet:
        struct_count = 1
        for used_struct in used_structures:
            # Generate Workbook
            sheet = workbook.add_worksheet(str(struct_count) + ' - ' + str(used_struct[1]))
            cols = list(string.ascii_uppercase)
            cols += [a + b for a in string.ascii_uppercase for b in string.ascii_uppercase]

            rules = []
            col_no = 2
            # Fetch available salary rules:
            for item in lines.slip_ids.struct_id.rule_ids:
                if item.struct_id.id == used_struct[0]:
                    col_title = ''
                    row = [None, None, None, None, None]
                    row[0] = col_no
                    row[1] = item.code
                    row[2] = item.name
                    col_title = str(cols[col_no]) + ':' + str(cols[col_no])
                    row[3] = col_title
                    if len(item.name) < 8:
                        row[4] = 12
                    else:
                        row[4] = len(item.name) + 2
                    rules.append(row)
                    col_no += 1

            # Report Details:
            for item in lines.slip_ids:
                if item.struct_id.id == used_struct[0]:
                    batch_period = str(item.date_from.strftime('%B %d, %Y')) + '  To  ' + str(
                        item.date_to.strftime('%B %d, %Y'))
                    company_name = item.company_id.name
                    break

            # Company Name
            sheet.write(0, 0, company_name, format4)

            # sheet.write(0, 2, 'Payslip Period:', format4)
            # sheet.write(0, 3, batch_period, format5)
            #
            # sheet.write(1, 2, 'Payslip Structure:', format4)
            # sheet.write(1, 3, used_struct[1], format5)

            # List report column headers:
            sheet.write(2, 0, 'Registration Number', format1)
            sheet.write(2, 1, 'Employee Name', format1)
            sheet.write(2, 2, 'Mobile Phone', format1)
            sheet.write(2, 3, 'Customer reference number', format1)
            sheet.write(2, 4, 'Purpose of payment', format1)
            sheet.write(2, 5, 'Department', format1)
            sheet.write(2, 6, 'Designation', format1)
            sheet.write(2, 7, 'CNIC No', format1)
            sheet.write(2, 8, 'Grade', format1)
            sheet.write(2, 9, 'Bank Account Number', format1)
            sheet.write(2, 10, 'Bank Account Title Name', format1)
            sheet.write(2, 11, 'Work Location', format1)
            sheet.write(2, 12, 'Activity', format1)
            for rule in rules:
                if rule[1] == 'GROSS':
                    sheet.write(2, 13, rule[2], format1)
                elif rule[1] == 'NET':
                    sheet.write(2, 14, rule[2], format1)

            # Generate names, dept, and salary items:
            x = 4
            e_name = 4
            has_payslips = False
            for slip in lines.slip_ids:
                if lines.slip_ids:
                    if slip.struct_id.id == used_struct[0] and slip.employee_id.bank_account_id.acc_number:
                        has_payslips = True
                        today = fields.Date.context_today(self)
                        dd = f"{today.day:02d}"
                        mm = f"{today.month:02d}"
                        yyyy = f"{today.year:04d}"
                        emp_code = slip.employee_id.identification_id or ""
                        customer_ref = f"{emp_code}{dd}{mm}{yyyy}"  # e.g. 41715012026

                        sheet.write(e_name, 0, emp_code, format3)
                        sheet.write(e_name, 1, slip.employee_id.name, format3)
                        sheet.write(e_name, 2, slip.employee_id.mobile_phone, format3)
                        sheet.write(e_name, 3, customer_ref, format3)
                        sheet.write(e_name, 4, '012', format3)
                        sheet.write(e_name, 5, slip.employee_id.department_id.name, format3)
                        sheet.write(e_name, 6, slip.employee_id.job_id.name, format3)
                        sheet.write(e_name, 7, slip.employee_id.ssnid, format3)
                        sheet.write(e_name, 8, slip.employee_id.contract_id.x_studio_grade, format3)
                        sheet.write(e_name, 9, slip.employee_id.bank_account_id.acc_number, format3)
                        sheet.write(e_name, 10, slip.employee_id.bank_account_id.acc_holder_name, format3)
                        sheet.write(e_name, 11, slip.employee_id.work_location_id.name, format3)
                        department = slip.employee_id.department_id.name or ""
                        work_location = slip.employee_id.work_location_id.name or ""

                        activity = department + (work_location[0] if work_location else "")

                        sheet.write(e_name, 12, activity, format3)

                        for line in slip.line_ids:
                            for rule in rules:
                                if line.code == rule[1] and (line.code == 'GROSS'):
                                    if line.amount > 0:
                                        sheet.write(x, 13, line.amount, format3_colored)
                                    else:
                                        sheet.write(x, 13, line.amount, format3)

                                elif line.code == rule[1] and (line.code == 'NET'):
                                    if line.amount > 0:
                                        sheet.write(x, 14, line.amount, format3_colored)
                                    else:
                                        sheet.write(x, 14, line.amount, format3)

                        x += 1
                        e_name += 1

            # Generate summission row at report end:
            sum_x = e_name
            if has_payslips == True:
                sheet.write(sum_x, 0, 'Total', format2)
                sheet.write(sum_x, 1, '', format2)
                for i in range(13, 15):
                    sum_start = cols[i] + '5'
                    sum_end = cols[i] + str(sum_x)
                    sum_range = '{=SUM(' + str(sum_start) + ':' + sum_end + ')}'
                    sheet.write_formula(sum_x, i, sum_range, format2)
                    i += 1

            # set width and height of colmns & rows:
            sheet.set_column('A:A', 10)  # Registration
            sheet.set_column('B:B', 32)  # Name
            for rule in rules:
                sheet.set_column(rule[3], rule[4])
            sheet.set_column('C:C', 13)   # Mobile
            sheet.set_column('D:D', 22)  # Customer reference number
            sheet.set_column('E:E', 16)  # Purpose of payment
            sheet.set_column('I:I', 7)  # Grade
            sheet.set_column('M:M', 12)  # Activity column

            struct_count += 1

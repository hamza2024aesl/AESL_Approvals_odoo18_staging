import string
from odoo import models


class PayrollReport(models.AbstractModel):
    _name = 'report.xlsx_payroll_report.xlsx_payroll_report'
    _inherit = 'report.report_xlsx.abstract'
    _description = "Payroll Report"

    def generate_xlsx_report(self, workbook, data, lines):
        # print("lines", lines.name)
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
            'bold': True,
        })
        format5 = workbook.add_format({
            'font_size': 12,
            'align': 'vcenter',
            'bold': False,
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
            col_no = 3
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

            sheet.write(0, 2, 'Payslip Period:', format4)
            sheet.write(0, 3, batch_period, format5)

            sheet.write(1, 2, 'Payslip Structure:', format4)
            sheet.write(1, 3, used_struct[1], format5)

            # List report column headers:
            sheet.write(2, 0, 'Registration Number', format1)
            sheet.write(2, 1, 'Employee Name', format1)
            sheet.write(2, 2, 'Department', format1)
            sheet.write(2, 3, 'Grade', format1)
            sheet.write(2, 4, 'Designation', format1)
            sheet.write(2, 5, 'Work Location', format1)
            for rule in rules:
                sheet.write(2, rule[0], rule[2], format1)

            # Generate names, dept, and salary items:
            # col = 0
            x = 4
            e_name = 4
            has_payslips = False
            for slip in lines.slip_ids:
                if lines.slip_ids:
                    if slip.struct_id.id == used_struct[0]:
                        has_payslips = True
                        sheet.write(e_name, 0, slip.employee_id.identification_id, format3)
                        sheet.write(e_name, 1, slip.employee_id.name, format3)
                        sheet.write(e_name, 2, slip.employee_id.department_id.name, format3)
                        # grades column added (08/03/2022)
                        sheet.write(e_name, 3, slip.employee_id.contract_id.x_studio_grade, format3)
                        sheet.write(e_name, 4, slip.employee_id.job_id.name, format3)
                        sheet.write(e_name, 5, slip.employee_id.work_location_id.name, format3)
                        for line in slip.line_ids:
                            for rule in rules:
                                if line.code == rule[1]:
                                    if line.amount > 0:
                                        sheet.write(x, rule[0], line.amount, format3_colored)
                                    else:
                                        sheet.write(x, rule[0], line.amount, format3)
                        x += 1
                        e_name += 1

            # Generate summission row at report end:
            sum_x = e_name
            if has_payslips == True:
                sheet.write(sum_x, 0, 'Total', format2)
                sheet.write(sum_x, 1, '', format2)
                for i in range(5, col_no):
                    sum_start = cols[i] + '3'
                    sum_end = cols[i] + str(sum_x)
                    sum_range = '{=SUM(' + str(sum_start) + ':' + sum_end + ')}'
                    # print(sum_range)
                    sheet.write_formula(sum_x, i, sum_range, format2)
                    i += 1

            # set width and height of colmns & rows:
            sheet.set_column('A:A', 10)
            sheet.set_column('B:B', 35)
            for rule in rules:
                sheet.set_column(rule[3], rule[4])
            sheet.set_column('C:C', 20)
            sheet.set_column('D:D', 30)
            sheet.set_column('E:E', 15)
            sheet.set_column('F:F', 15)

            struct_count += 1

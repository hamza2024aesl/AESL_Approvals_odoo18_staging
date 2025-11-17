import string
from odoo import models


class PayrollReportTwo(models.AbstractModel):
    _name = 'report.xlsx_payroll_report.xlsx_payroll_report_two'
    _inherit = 'report.report_xlsx.abstract'
    _description = "Payroll Report Two"

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
            'num_format': '#,##0.00',
        })
        format3 = workbook.add_format({
            'font_size': 11,
            'align': 'vcenter',
            'bold': False,
            'num_format': '#,##0.00',
        })
        format3_colored = workbook.add_format({
            'font_size': 11,
            'align': 'vcenter',
            'bg_color': '#f7fcff',
            'bold': False,
            'num_format': '#,##0.00',
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
                    address_id = item.company_id.street
                    address_id2 = item.company_id.street2
                    city_id = item.company_id.city
                    state_id = item.company_id.state_id
                    zip_id = item.company_id.zip
                    ntn_id = item.company_id.vat
                    country_name = item.company_id.country_id
                    break

            # Company Name
            # sheet.write(0, 0, company_name, format4)
            sheet.write(0, 0,
                        'STATEMENT OF DEDUCTION OF TAX ON INCOME CHARGABLE UNDER HEAD "SALARY" FOR THE MONTH ' + lines.name + ' NAME AND ADDRESS OF EMPLOYER: '
                        + company_name + '', format4)
            sheet.write(1, 0, ' ' + str(address_id) + ' ' + str(address_id2) + ' ' + str(city_id) + ' ' + str(
                state_id.name) + ' ' + str(zip_id) + ' ' + str(country_name.name) + ' NATIONAL TAX NUMBER: ' + str(
                ntn_id) + ' ', format4)

            # sheet.write(1, 2, 'Payslip Structure:', format4)
            # sheet.write(1, 3, used_struct[1], format5)

            # List report column headers:
            sheet.write(3, 0, 'S.No', format1)
            sheet.write(3, 1, 'Payment Section', format1)
            sheet.write(3, 2, 'Tax Payer Name', format1)
            sheet.write(3, 3, 'Department', format1)
            sheet.write(3, 4, 'Designation', format1)
            sheet.write(3, 5, 'CNIC No.', format1)
            sheet.write(3, 6, 'Employee Location', format1)
            sheet.write(3, 7, 'Tax Payer City', format1)
            sheet.write(3, 8, 'Employee Address', format1)
            sheet.write(3, 9, 'Tax Payer Status', format1)
            sheet.write(3, 10, 'Tax Payer Business Name', format1)
            for rule in rules:
                if rule[1] == 'GROSS':
                    sheet.write(3, 11, rule[2], format1)
                elif rule[1] == 'BONUS':
                    sheet.write(3, 12, 'Bonus', format1)
                elif rule[1] == 'ITAXYB':
                    sheet.write(3, 13, 'Taxable Amount', format1)
                elif rule[1] == 'SRITAXYB':
                    sheet.write(3, 14, 'Surcharge Amount', format1)
                    # sheet.write(3, 12, rule[2], format1)
                # elif rule[1] == 'BASIC':
                #     sheet.write(3, 13, rule[2], format1)
                # elif rule[1] == 'TIYB':
                #     sheet.write(3, 14, rule[2], format1)
                # sheet.write(3, rule[0], rule[2], format1)

            # Generate names, dept, and salary items:
            x = 4
            sno = 1
            p_section = 0
            ind = 0
            e_name = 4
            has_payslips = False
            for slip in lines.slip_ids:
                if lines.slip_ids:
                    if slip.struct_id.id == used_struct[0]:  # and slip.line.code == 'ITAXYB':
                        has_payslips = True

                        val = {
                            'gross': 0,
                            'itaxyb': 0,
                            'sritaxyb': 0,
                            'basicyb': 0,
                            'tiyb': 0,
                            'bonus': 0
                        }
                        for line in slip.line_ids.filtered(
                                lambda x: x.code in ['GROSS', 'ITAXYB', 'SRITAXYB', 'BASIC', 'TIYB', 'BONUS']):
                            if line.code == 'GROSS':
                                val['gross'] = line.amount
                            elif line.code == 'ITAXYB':
                                val['itaxyb'] = line.amount
                            elif line.code == 'SRITAXYB':
                                val['sritaxyb'] = line.amount
                            elif line.code == 'BASIC':
                                val['basicyb'] = line.amount
                            elif line.code == 'TIYB':
                                val['tiyb'] = line.amount
                            elif line.code == 'BONUS':
                                val['bonus'] = line.amount
                        if val['itaxyb'] != 0:
                            sheet.write(e_name, 0, sno)
                            sheet.write(e_name, 1, '149/3')
                            address_id = slip.employee_id.address_home_id.street
                            address_id2 = slip.employee_id.address_home_id.street2
                            city_id = slip.employee_id.address_home_id.city
                            state_id = slip.employee_id.address_home_id.state_id
                            zip_id = slip.employee_id.address_home_id.zip
                            country_name = slip.employee_id.address_home_id.country_id

                            # state_id1 = slip.employee_id.address_id.state_id

                            sheet.write(e_name, 2, slip.employee_id.name, format3)
                            sheet.write(e_name, 3, slip.employee_id.department_id.name, format3)
                            sheet.write(e_name, 4, slip.employee_id.job_id.name, format3)
                            sheet.write(e_name, 5, slip.employee_id.identification_id, format3)
                            sheet.write(e_name, 6, slip.employee_id.location_id.emp_location, format3)
                            sheet.write(e_name, 7, slip.employee_id.location_id.emp_location, format3)
                            # sheet.write(e_name, 7, ' ' + str(state_id.name) + ' ', format3)
                            sheet.write(e_name, 8,
                                        ' ' + str(address_id) + ' ' + str(address_id2) + ' ' + str(city_id) + ' ' + str(
                                            state_id.name) + ' ' + str(zip_id) + ' ' + str(country_name.name) + ' ',
                                        format3)
                            sheet.write(e_name, 9, 'INDIVIDUAL', format3)
                            sheet.write(e_name, 10, '', format3)
                            sheet.write(x, 11, val['gross'], format3)
                            sheet.write(x, 12, round(val['bonus']), format3)
                            sheet.write(x, 13, round(val['itaxyb']), format3)
                            sheet.write(x, 14, round(val['sritaxyb']), format3)

                            # sheet.write(x, 13, val['basicyb'], format3)
                            # sheet.write(x, 14, val['tiyb'], format3)
                            p_section += 1
                            ind += 1
                            sno += 1
                            x += 1
                            e_name += 1
            # Generate summission row at report end:
            sum_x = e_name
            if has_payslips == True:
                sheet.write(sum_x, 0, 'Total', format2)
                sheet.write(sum_x, 6, '', format2)
                for i in range(11, 16):
                    sum_start = cols[i] + '5'
                    sum_end = cols[i] + str(sum_x)
                    sum_range = '{=SUM(' + str(sum_start) + ':' + sum_end + ')}'
                    sheet.write_formula(sum_x, i, sum_range, format2)
                    i += 1

            # set width and height of colmns & rows:
            sheet.set_column('A:A', 7)
            sheet.set_column('B:B', 10)
            for rule in rules:
                sheet.set_column(rule[3], rule[4])
            sheet.set_column('C:C', 35)
            sheet.set_column('G:G', 15)
            sheet.set_column('I:I', 10)
            sheet.set_column('J:J', 15)
            # sheet.set_column('K:K', 15)
            sheet.set_column('L:L', 15)

            struct_count += 1

            sheet.write(sum_x + 2, 0, 'I, ' + self.env['hr.employee'].search([('job_id.name', '=', 'FINANCE MANAGER')],
                                                                             limit=1).name + '(Finance Manager) being the person responsible for paying the above salary , etc.Do hereby declare that the above list is complete and that particulars given above correct.',
                        format4)

            sheet.write(sum_x + 5, 0, 'Date: ', format4)
            sheet.write(sum_x + 5, 1, '', format5)

            sheet.write(sum_x + 5, 8, 'Signature: ', format4)
            sheet.write(sum_x + 5, 9, '', format5)

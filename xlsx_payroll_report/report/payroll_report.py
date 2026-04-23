import string
from odoo import models


class PayrollReport(models.AbstractModel):
    _name = 'report.xlsx_payroll_report.xlsx_payroll_report'
    _inherit = 'report.report_xlsx.abstract'
    _description = "Payroll Report"

    def generate_xlsx_report(self, workbook, data, lines):

        # ================= FORMATS =================
        format1 = workbook.add_format({
            'font_size': 12, 'align': 'vcenter', 'bold': True,
            'bg_color': '#d3dde3', 'color': 'black', 'bottom': True,
        })
        format2 = workbook.add_format({
            'font_size': 12, 'align': 'vcenter', 'bold': True,
            'bg_color': '#edf4f7', 'color': 'black',
            'num_format': '#,##0.00'
        })
        format3 = workbook.add_format({
            'font_size': 11, 'align': 'vcenter',
            'num_format': '#,##0.00'
        })
        format3_colored = workbook.add_format({
            'font_size': 11, 'align': 'vcenter',
            'bg_color': '#f7fcff',
            'num_format': '#,##0.00'
        })
        format4 = workbook.add_format({'font_size': 12, 'bold': True})
        format5 = workbook.add_format({'font_size': 12})

        # ================= STRUCTURES =================
        used_structures = []
        for struct in lines.slip_ids.struct_id:
            if struct.id not in [x[0] for x in used_structures]:
                used_structures.append([struct.id, struct.name])

        struct_count = 1

        for used_struct in used_structures:

            sheet = workbook.add_worksheet(f"{struct_count} - {used_struct[1]}")

            cols = list(string.ascii_uppercase)
            cols += [a + b for a in string.ascii_uppercase for b in string.ascii_uppercase]

            # ================= FIXED HEADERS =================
            fixed_headers = [
                ('Registration Number', 10),
                ('GP No.', 12),
                ('Employee Name', 35),
                ('Department', 20),
                ('Grade', 15),
                ('CNIC', 18),
                ('Designation', 30),
                ('Work Location', 15),
            ]

            start_rule_col = len(fixed_headers)
            col_no = start_rule_col
            rules = []

            # insert_after_name = "PF Loan - Total"
            # pf_inserted = False

            # ================= SALARY RULES =================
            for rule in lines.slip_ids.struct_id.rule_ids:
                if rule.struct_id.id != used_struct[0]:
                    continue

                rules.append([
                    col_no,
                    rule.code,
                    rule.name,
                    f"{cols[col_no]}:{cols[col_no]}",
                    max(len(rule.name) + 2, 12),
                ])
                col_no += 1

                # Insert PF Balance column
                # if not pf_inserted and rule.name == insert_after_name:
                #     pf_balance_col = col_no
                #     rules.append([
                #         pf_balance_col,
                #         "PF_BAL",
                #         "PF Balance",
                #         f"{cols[pf_balance_col]}:{cols[pf_balance_col]}",
                #         14,
                #     ])
                #     col_no += 1
                #     pf_inserted = True

            # if not pf_inserted:
            #     pf_balance_col = col_no
            #     rules.append([
            #         pf_balance_col,
            #         "PF_BAL",
            #         "PF Balance",
            #         f"{cols[pf_balance_col]}:{cols[pf_balance_col]}",
            #         14,
            #     ])
            #     col_no += 1

            # ================= TAIL HEADERS =================
            tail_headers = [
                ('Beneficiary Name', 25),
                ('Beneficiary Account Number', 24),
                ('Contact Number / Mobile', 22),
                ('Beneficiary Email Address', 28),
                ('Bank Account Title', 22),
            ]

            tail_cols = []
            for title, width in tail_headers:
                tail_cols.append((col_no, title, width))
                col_no += 1

            # ================= REPORT HEADER =================
            slip = lines.slip_ids.filtered(lambda s: s.struct_id.id == used_struct[0])[:1]
            if slip:
                sheet.write(0, 0, slip.company_id.name, format4)
                sheet.write(0, 2, 'Payslip Period:', format4)
                sheet.write(0, 3, f"{slip.date_from:%B %d, %Y} To {slip.date_to:%B %d, %Y}", format5)
                sheet.write(1, 2, 'Payslip Structure:', format4)
                sheet.write(1, 3, used_struct[1], format5)

            # ================= COLUMN HEADERS =================
            for idx, (title, _) in enumerate(fixed_headers):
                sheet.write(2, idx, title, format1)

            for rule in rules:
                sheet.write(2, rule[0], rule[2], format1)

            for col, title, _ in tail_cols:
                sheet.write(2, col, title, format1)

            # ================= DATA ROWS =================
            row = 3
            sorted_slips = lines.slip_ids.sorted(lambda s: s.employee_id.identification_id.lower())

            for slip in sorted_slips:
                if slip.struct_id.id != used_struct[0]:
                    continue

                emp = slip.employee_id
                bank = emp.bank_account_id

                # Fixed columns
                sheet.write(row, 0, emp.identification_id or '', format3)
                sheet.write(row, 1, emp.x_studio_field_uRb4K or '', format3)
                sheet.write(row, 2, emp.name or '', format3)
                sheet.write(row, 3, emp.department_id.name or '', format3)
                sheet.write(row, 4, emp.contract_id.x_studio_grade or '', format3)
                sheet.write(row, 5, emp.ssnid or '', format3)
                sheet.write(row, 6, emp.job_id.name or '', format3)
                sheet.write(row, 7, emp.work_location_id.name or '', format3)

                # Salary rules
                for line in slip.line_ids:
                    for rule in rules:
                        if line.code == rule[1]:
                            sheet.write(
                                row, rule[0], line.amount,
                                format3_colored if line.amount > 0 else format3
                            )

                # PF Balance from MODEL METHOD
                pf_balance = slip.get_pf_balance_as_of()
                # sheet.write(row, pf_balance_col, pf_balance, format3_colored)

                # Tail columns
                sheet.write(row, tail_cols[0][0], bank.partner_id.name if bank else '', format3)
                sheet.write(row, tail_cols[1][0], bank.acc_number if bank else '', format3)
                sheet.write(row, tail_cols[2][0], emp.private_phone or '', format3)
                sheet.write(row, tail_cols[3][0], emp.private_email or '', format3)
                sheet.write(row, tail_cols[4][0], bank.acc_holder_name if bank else '', format3)

                row += 1

            # ================= TOTAL ROW =================
            sheet.write(row, 0, 'Total', format2)

            first_tail_col = tail_cols[0][0]
            for col in range(start_rule_col, first_tail_col):
                sheet.write_formula(
                    row, col,
                    f"=SUM({cols[col]}3:{cols[col]}{row})",
                    format2
                )

            # ================= COLUMN WIDTHS =================
            for idx, (_, width) in enumerate(fixed_headers):
                sheet.set_column(idx, idx, width)

            for rule in rules:
                sheet.set_column(rule[3], rule[4])

            for col, _, width in tail_cols:
                sheet.set_column(col, col, width)

            struct_count += 1

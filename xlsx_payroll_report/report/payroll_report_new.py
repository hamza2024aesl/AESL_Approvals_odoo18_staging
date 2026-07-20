from odoo import models

header_total = {}


class HrPayslipInherit(models.Model):
    _inherit = 'hr.payslip.run'

    def get_rules_header(self):
        global header_total
        header_total = {}
        rules = []
        used_structures = []
        for sal_structure in self.slip_ids.struct_id:
            if sal_structure.id not in used_structures:
                used_structures.append([sal_structure.id, sal_structure.name])

        for used_struct in used_structures:
            for item in self.slip_ids.struct_id.rule_ids:
                if item.struct_id.id == used_struct[0]:
                    row = [None, None, None, None, None]
                    row[1] = item.code
                    row[2] = item.name
                    if len(item.name) < 8:
                        row[4] = 12
                    else:
                        row[4] = len(item.name) + 2
                    rules.append(row)
        val = []
        for rule in rules:
            if rule[2]:
                val.append(rule[2])
                header_total.update({str(rule[1]): 0})
        return val

    def get_report_data(self):
        global header_total
        keylist = list(header_total)
        values = []
        rules = []
        used_structures = []
        for sal_structure in self.slip_ids.struct_id:
            if sal_structure.id not in used_structures:
                used_structures.append([sal_structure.id, sal_structure.name])
        for used_struct in used_structures:
            for item in self.slip_ids.struct_id.rule_ids:
                if item.struct_id.id == used_struct[0]:
                    row = [None, None, None, None, None]
                    row[1] = item.code
                    row[2] = item.name
                    if len(item.name) < 8:
                        row[4] = 12
                    else:
                        row[4] = len(item.name) + 2
                    rules.append(row)
            for slip in self.slip_ids:

                x = {
                    'reg_no': slip.employee_id.identification_id,
                    'name': slip.employee_id.name,
                    'dept': slip.employee_id.department_id.name,
                    'job': slip.employee_id.job_id.name,
                    'loc': slip.employee_id.work_location_id.name[:1] if slip.employee_id.work_location_id.name else False,
                }
                vals = [0.0 for _ in range(len(keylist))]
                for line in slip.line_ids:
                    for rule in rules:
                        if line.code == rule[1]:
                            # if line.total > 0:
                            #     # vals.append(line.total)
                            #     vals[keylist.index(line.code)] = line.total
                            #     header_total[str(line.code)] += line.total
                            #
                            # else:

                            vals[keylist.index(line.code)] = line.total
                            # vals.append(line.total)
                            header_total[str(line.code)] += line.total

                    x.update({'values': vals})
                values.append(x)
        return values

    def get_total(self):
        global header_total
        return [v for k, v in header_total.items()]

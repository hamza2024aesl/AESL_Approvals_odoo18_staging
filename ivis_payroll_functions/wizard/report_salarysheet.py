import copy
from odoo import models, api


class ReportSalarysheet(models.AbstractModel):
    _name = 'report.salarysheet'
    _description = 'Report Salarysheet'

    def get_all_rules(self, company_id):
        self.env.cr.execute(
            """select hsr.name,hsrc.code from hr_salary_rule as hsr join hr_salary_rule_category as hsrc on hsr.category_id = hsrc.id where active = True and appears_on_report = True order by report_sequence""")
        return self.env.cr.dictfetchall()

    @api.model
    def _get_report_values(self, docids, data=None):
        self.model = self.env.context.get('active_model')
        docs = self.env[self.model].browse(self.env.context.get('active_id'))
        result = []

        salary_rules = self.get_all_rules(docs.salary_rule_id.company_id.id)

        pre_rules = copy.deepcopy(salary_rules)

        for item in pre_rules:
            del item['code']

        i = 0

        for rule in data['form']['rules']:
            x = []
            for payslip_id in rule:
                result.append({payslip_id: copy.deepcopy(pre_rules)})
                for payslip in rule[payslip_id]:
                    for rule_dict in result[i][payslip_id]:
                        if rule_dict['name'] not in x:
                            if rule_dict['name'] == payslip['name']:
                                loc = result[i][payslip_id].index(rule_dict)
                                result[i][payslip_id][loc]['amount'] = payslip['amount']
                                x.append(payslip['name'])
                            else:
                                loc = result[i][payslip_id].index(rule_dict)
                                result[i][payslip_id][loc]['amount'] = 0.0
                        else:
                            continue
                i += 1

        salary_rules = self.get_all_rules(docs.salary_rule_id.company_id.id)

        return {
            'doc_model': self.model,
            'docs': docs,
            'rules': salary_rules,
            'result': result,
        }

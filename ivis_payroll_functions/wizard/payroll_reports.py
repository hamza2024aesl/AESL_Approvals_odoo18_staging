from datetime import datetime
from odoo import api, fields, models, _


class PayrollReports(models.TransientModel):
    _name = 'payroll.reports'
    _description = 'Payroll Reports'

    type = fields.Selection([('Provident Fund', 'Provident Fund')], string='Type', default='Provident Fund')
    date_from = fields.Date('Date From', default='lambda *a: datetime.now().strftime("%Y-%m-%d")')
    date_to = fields.Date('Date To', default='lambda *a: datetime.now().strftime("%Y-%m-%d")')

    @api.constrains('date_from', 'date_to')
    def check_dates(self):
        if self.date_from:
            if self.date_from > self.date_to:
                return False
            # if self.date_to > fields.date.today():
            #     return False
        return True

    def fetch_service_period(self, emp_id):
        rec = self.env['hr.contract'].search([('employee_id', '=', emp_id)])
        if rec:
            start_date = rec[0].date_start
            fmt = '%Y-%m-%d'

            d1 = datetime.strptime(str(start_date), fmt)
            d2 = datetime.strptime(str(self.date_to), fmt)

            diff = d2 - d1

            if (diff.days > 365):
                return True
            else:
                return False
        else:
            return False

    def current_pf(self, emp_id):
        self.env.cr.execute("""
                            select sum(hpsl.amount) as curr_pf,hps.employee_id from hr_payslip as hps
                            inner join hr_payslip_line as hpsl on hps.id = hpsl.slip_id
                            where hpsl.code = 'PF' and hps.date_from between '%s' and '%s'
                            and hps.employee_id =%s group by hps.employee_id
                            order by hps.employee_id asc 
                            """ % (self.date_from, self.date_to, emp_id))
        records = self.env.cr.dictfetchall()
        if len(records) > 0:
            return records[0]['curr_pf']
        else:
            return 0

    def opening_pf(self, emp_id):
        # self.env.cr.execute("""
        #         select sum(hpsl.amount) as pf ,hps.employee_id from hr_payslip as hps
        #         inner join hr_payslip_line as hpsl on hps.id = hpsl.slip_id
        #         where hpsl.code = 'PF' and hps.date_from < '%s' and hps.employee_id = %s
        #         group by hps.employee_id order by hps.employee_id asc
        #         """ % (self.date_from, emp_id))
        # records = self.env.cr.dictfetchall()
        emp = self.env['hr.employee'].search([('id', '=', emp_id)])
        records = emp.pf_employee + emp.pf_employer + emp.pf_interest
        if records > 0:
            return records
        else:
            return 0

    def pf_till_date_employee(self, emp_id):
        # self.env.cr.execute("""
        #         select sum(hpsl.amount) as pf ,hps.employee_id from hr_payslip as hps
        #         inner join hr_payslip_line as hpsl on hps.id = hpsl.slip_id
        #         where hpsl.code = 'PF' and hps.date_from < '%s' and hps.employee_id = %s
        #         group by hps.employee_id order by hps.employee_id asc
        #         """ % (self.date_from, emp_id))
        # records = self.env.cr.dictfetchall()
        emp = self.env['hr.employee'].search([('id', '=', emp_id)])
        records = emp.pf_employee + emp.employee_contribution
        if records > 0:
            return records
        else:
            return 0

    def pf_till_date_employer(self, emp_id):
        # self.env.cr.execute("""
        #         select sum(hpsl.amount) as pf ,hps.employee_id from hr_payslip as hps
        #         inner join hr_payslip_line as hpsl on hps.id = hpsl.slip_id
        #         where hpsl.code = 'PF' and hps.date_from < '%s' and hps.employee_id = %s
        #         group by hps.employee_id order by hps.employee_id asc
        #         """ % (self.date_from, emp_id))
        # records = self.env.cr.dictfetchall()
        emp = self.env['hr.employee'].search([('id', '=', emp_id)])
        records = emp.pf_employer + emp.employer_contribution
        if records > 0:
            return records
        else:
            return 0

    def generate_report(self):
        report_ = self.env['custom.tree.report']
        report_.search([]).unlink()
        self.env.cr.execute("""
        select sum(hpsl.amount) as gross,hps.employee_id as emp_id, he.department_id as dpt_id,he.name as emp
        from hr_employee as he 
        inner join hr_payslip as hps on he.id=hps.employee_id
        inner join hr_payslip_line as hpsl on hps.id = hpsl.slip_id
        where hpsl.code = 'GROSS' and hps.date_from between '%s' and '%s' and he.company_id = '%s' group by hps.employee_id,he.department_id,he.name
        order by hps.employee_id asc
        """ % (self.date_from, self.date_to, self.env.company.id))
        records = self.env.cr.dictfetchall()
        for rec in records:
            emp = self.env['hr.employee'].search([('id', '=', rec['emp_id'])])
            emp.compute_funds_pf()
            rec['opening_pf'] = self.opening_pf(rec['emp_id'])
            rec['curr_pf'] = self.current_pf(rec['emp_id'])
            pfund_till_date = abs(self.pf_till_date_employee(rec['emp_id']))
            emplr_pfund = abs(self.pf_till_date_employer(rec['emp_id'])) if self.fetch_service_period(
                rec['emp_id']) else 0
            report_.create({
                'department_id': rec['dpt_id'],
                'employee_id': rec['emp_id'],
                'gross_pay': rec['gross'],
                'opening_pfund': abs(rec['opening_pf']),
                'current_pfund': abs(rec['curr_pf']),
                'interest': emp.interest + emp.pf_interest,
                'pfund_till_date': pfund_till_date,
                'emplr_pfund': emplr_pfund,
                'total_pfund': pfund_till_date + emplr_pfund + abs(emp.pf_interest) + + abs(
                    emp.interest) if self.fetch_service_period(
                    rec['emp_id']) else 0
            })

        ir_model_data = self.env['ir.model.data']
        tree_res = ir_model_data.get_object_reference('ivis_payroll_functions', 'custom_report_tree_view')
        tree_id = tree_res and tree_res[1] or False
        return {
            'name': _('Report Tree'),
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'custom.tree.report',
            'views': [(tree_id, 'tree')],
            'type': 'ir.actions.act_window',
        }

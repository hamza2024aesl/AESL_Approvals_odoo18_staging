from odoo import models, fields,api,_
from collections import defaultdict
from odoo.exceptions import UserError

class HrSummaryReportWizard(models.TransientModel):
    _name = 'higher.management.wizard'
    _description = 'Higher Management Report Wizard'

    location_id = fields.Many2one('hr.work.location', "Region")
    department_ids = fields.Many2many('hr.department', string='Department')
    all_dept = fields.Boolean('All Region', default=False)

    def print_higher_management(self):
        data = {
            'ids': self.ids,
            'model': 'higher.management.wizard',
            'form': self.read()[0],
        }
        if not (self.department_ids or self.location_id):
            raise UserError(_("Please select valid fields"))

        grouped_departments = defaultdict(lambda: defaultdict(list))
        grouped_departments_region = defaultdict(lambda: defaultdict(list))
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        grade = ''
        for dept in self.department_ids:
            if not self.all_dept:
                appraisals = self.sudo().env['appraisal.system'].sudo().search([
                    ('location', '=', self.location_id.emp_location),
                    ('department_id', '=', dept.id),
                    ('appraisal_approver_id', '=', self.env.user.id)
                ])
            else:
                if self.location_id:
                    raise UserError(_("Please remove the selected regions"))
                appraisals = self.sudo().env['appraisal.system'].sudo().search([
                    ('department_id', '=', dept.id),
                    ('appraisal_approver_id', '=', self.env.user.id)
                ])
            for emp in appraisals:
                if emp.appraisal_approver_id:
                    # region = emp.location
                    manager_name = emp.appraisal_approver_id.name
                    last_manager_name = emp.write_uid.name
                    filter_line = emp.recomm_increment_lines_id.filtered(lambda line: line.increment_raise_by.id == emp.appraisal_approver_id.id)
                    last_line = emp.recomm_increment_lines_id[-1] if emp.recomm_increment_lines_id else None
                    if last_line:
                        if last_line.recomm_grades == 0:
                            grade = ''
                        else:
                            grade = last_line.recomm_grades
                    record = {
                        'emp_name': emp.employee_id.name,
                        'emp_no': emp.registration_number,
                        'curr_grade': emp.grade,
                        'curr_salary': emp.gross_salary,
                        'curr_designation': emp.job_id.name,
                        'recomm_salary': (last_line.increment_raise_amount + emp.gross_salary) if last_line else 0,
                        'recomm_raise_amount': last_line.increment_raise_amount if last_line else 0,
                        'recomm_grade': grade if last_line else '',
                        'recomm_designation': last_line.recomm_desigantion_id.name if last_line else False,
                        'percentage': ((last_line.increment_raise_amount/ emp.gross_salary) * 100) if last_line else 0,
                        'doc_state': emp.doc_state,
                        'state': emp.state,
                        'url': ("%s/web#id=%s&action=839&model=appraisal.system&view_type=form&cids=&menu_id=" % (
                            base_url, emp.id)),
                    }
                    grouped_departments[manager_name][last_manager_name].append(record)
        data['records'] = {managers: dict(last_managers) for managers, last_managers in grouped_departments.items()}

        return self.env.ref('aesl_appraisal_system.appraisal_system_higher_management_report_pdf').report_action(self, data=data)
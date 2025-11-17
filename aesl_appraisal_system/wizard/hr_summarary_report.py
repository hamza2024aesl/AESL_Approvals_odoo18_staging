from odoo import models, fields,api,_
from collections import defaultdict
from odoo.exceptions import UserError

class HrSummaryReportWizard(models.TransientModel):
    _name = 'hr.summary.wizard'
    _description = 'HR Summary Report Wizard'

    location_id = fields.Many2one('hr.work.location', "Region")
    department_id = fields.Many2one('hr.department', string='Department')
    department_ids = fields.Many2many('hr.department', string='Department')
    all_dept = fields.Boolean('All Region', default=False)



    def print_hr_report_1(self):
        data = {
            'ids': self.ids,
            'model': 'manager.summary.wizard',
            'form': self.read()[0],
        }
        for dept in self.department_ids:
            appraisals = self.sudo().env['appraisal.system'].sudo().search([('location', '=', self.location_id.emp_location),('department_id','=',dept.id)])
            grouped_records = defaultdict(list)
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            records = []
            mngr_nmae = []
            department = []
            for emp in appraisals:
                for emp_line in emp.sudo().recomm_increment_lines_id:
                    if emp.department_id.name not in department:
                        department.append()
                    if emp_line.increment_raise_by.name not in mngr_nmae:
                        mngr_nmae.append(emp_line.increment_raise_by.name)
                        group_key = emp_line.increment_raise_by.name
                        grouped_records[group_key].append({
                            'emp_name': emp.employee_id.name,
                            'emp_no': emp.registration_number,
                            'curr_grade': emp.grade,
                            'curr_salary': emp.gross_salary,
                            'curr_designation': emp.job_id.name,
                            'recomm_salary': (
                                    emp_line.increment_raise_amount + emp.gross_salary) if emp_line.increment_raise_amount else 0,
                            'recomm_raise_amount': emp_line.increment_raise_amount,
                            'recomm_grade': emp_line.recomm_grades,
                            'recomm_designation': emp_line.recomm_desigantion_id.name,
                            'percentage': ((
                                                       emp_line.increment_raise_amount / emp.gross_salary) * 100) if emp_line.increment_raise_amount and emp.gross_salary else 0,
                            'doc_state': emp.doc_state,
                            # 'url': (("%s/web#id=%s&action=839&model=appraisal.system&view_type=form&cids=&menu_id=466")%base_url, %emp.id),
                            'url': ("%s/web#id=%s&action=839&model=appraisal.system&view_type=form&cids=&menu_id=" % (
                            base_url, emp.id)),
                            'state': emp.state,
                            # 'url': ("'/web#id=' + str(emp.id) + '&model=appraisal.system&view_type=form'")
                        })
                    else:
                        group_key = emp_line.increment_raise_by.name
                        grouped_records[group_key].append({
                            'emp_name': emp.employee_id.name,
                            'emp_no': emp.registration_number,
                            'curr_grade': emp.grade,
                            'curr_salary': emp.gross_salary,
                            'curr_designation': emp.job_id.name,
                            'recomm_salary': (
                                    emp_line.increment_raise_amount + emp.gross_salary) if emp_line.increment_raise_amount else 0,
                            'recomm_raise_amount': emp_line.increment_raise_amount,
                            'recomm_grade': emp_line.recomm_grades,
                            'recomm_designation': emp_line.recomm_desigantion_id.name,
                            'percentage': ((emp_line.increment_raise_amount / emp.gross_salary) * 100) if emp_line.increment_raise_amount and emp.gross_salary else 0,
                            'doc_state': emp.doc_state,
                            'state': emp.state,
                            'url': ("%s/web#id=%s&action=839&model=appraisal.system&view_type=form&cids=&menu_id=" % (
                            base_url, emp.id)),
                        })
                print('name', emp.employee_id.name)
        data['records'] = dict(grouped_records)
        return self.env.ref('aesl_appraisal_system.appraisal_system_hr_summary_report_pdf').report_action(self, data=data)


    def print_hr_report_2(self):
        data = {
            'ids': self.ids,
            'model': 'manager.summary.wizard',
            'form': self.read()[0],
        }
        if not (self.department_ids or self.location_id):
            raise UserError(_("Please select valid fields"))

        grouped_departments = defaultdict(lambda: defaultdict(list))
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')

        for dept in self.department_ids:
            appraisals = self.sudo().env['appraisal.system'].sudo().search([
                ('location', '=', self.location_id.emp_location),
                ('department_id', '=', dept.id)
            ])

            for emp in appraisals:
                if len(emp.sudo().recomm_increment_lines_id) > 1:
                    recommend_lines = emp.sudo().recomm_increment_lines_id[-1]
                else:
                    recommend_lines = emp.sudo().recomm_increment_lines_id
                for emp_line in recommend_lines:
                    if emp_line.increment_raise_by:
                        manager_name = emp_line.increment_raise_by.name
                        record = {
                            'emp_name': emp.employee_id.name,
                            'emp_no': emp.registration_number,
                            'curr_grade': emp.grade,
                            'curr_salary': emp.gross_salary,
                            'curr_designation': emp.job_id.name,
                            'recomm_salary': (
                                        emp_line.increment_raise_amount + emp.gross_salary) if emp_line.increment_raise_amount else 0,
                            'recomm_raise_amount': emp_line.increment_raise_amount,
                            'recomm_grade': emp_line.recomm_grades,
                            'recomm_designation': emp_line.recomm_desigantion_id.name,
                            'percentage': ((
                                                       emp_line.increment_raise_amount / emp.gross_salary) * 100) if emp_line.increment_raise_amount and emp.gross_salary else 0,
                            'doc_state': emp.doc_state,
                            'state': emp.state,
                            'url': ("%s/web#id=%s&action=839&model=appraisal.system&view_type=form&cids=&menu_id=" % (
                            base_url, emp.id)),
                        }
                        grouped_departments[dept.name][manager_name].append(record)

        # Add the grouped data to the report data dictionary
        data['records'] = {dept: dict(managers) for dept, managers in grouped_departments.items()}

        return self.env.ref('aesl_appraisal_system.appraisal_system_hr_summary_report_pdf').report_action(self, data=data)


    def print_hr_report(self):
        data = {
            'ids': self.ids,
            'model': 'manager.summary.wizard',
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
                    ('department_id', '=', dept.id)
                ])
            else:
                if self.location_id:
                    raise UserError(_("Please remove the selected regions"))
                appraisals = self.sudo().env['appraisal.system'].sudo().search([
                    ('department_id', '=', dept.id)
                ])
            for emp in appraisals:
                if emp.appraisal_approver_id:
                    # region = emp.location
                    manager_name = emp.appraisal_approver_id.name
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
                    grouped_departments[dept.name][manager_name].append(record)
                    # grouped_departments_region[region][dept.name][manager_name].append(record)

                    # record = {
                    #     'emp_name': emp.employee_id.name,
                    #     'emp_no': emp.registration_number,
                    #     'curr_grade': emp.grade,
                    #     'curr_salary': emp.gross_salary,
                    #     'curr_designation': emp.job_id.name,
                    #     'recomm_salary': (filter_line.increment_raise_amount + emp.gross_salary) if filter_line.increment_raise_amount else 0,
                    #     'recomm_raise_amount': filter_line.increment_raise_amount if filter_line.increment_raise_amount else 0,
                    #     'recomm_grade': filter_line.recomm_grades if filter_line.recomm_grades else 0,
                    #     'recomm_designation': filter_line.recomm_desigantion_id.name if filter_line.recomm_desigantion_id else False,
                    #     'percentage': ((filter_line.increment_raise_amount/ emp.gross_salary) * 100) if filter_line.increment_raise_amount else 0,
                    #     'doc_state': emp.doc_state,
                    #     'state': emp.state,
                    #     'url': ("%s/web#id=%s&action=839&model=appraisal.system&view_type=form&cids=&menu_id=" % (
                    #         base_url, emp.id)),
                    # }
                    # grouped_departments[dept.name][manager_name].append(record)
                    #
                    #

                # if len(emp.sudo().recomm_increment_lines_id) > 1:
                #     recommend_lines = emp.sudo().recomm_increment_lines_id[-1]
                # else:
                #     recommend_lines = emp.sudo().recomm_increment_lines_id
                # for emp_line in recommend_lines:
                #     if emp_line.increment_raise_by:
                #         manager_name = emp_line.increment_raise_by.name
                #         record = {
                #             'emp_name': emp.employee_id.name,
                #             'emp_no': emp.registration_number,
                #             'curr_grade': emp.grade,
                #             'curr_salary': emp.gross_salary,
                #             'curr_designation': emp.job_id.name,
                #             'recomm_salary': (
                #                         emp_line.increment_raise_amount + emp.gross_salary) if emp_line.increment_raise_amount else 0,
                #             'recomm_raise_amount': emp_line.increment_raise_amount,
                #             'recomm_grade': emp_line.recomm_grades,
                #             'recomm_designation': emp_line.recomm_desigantion_id.name,
                #             'percentage': ((
                #                                        emp_line.increment_raise_amount / emp.gross_salary) * 100) if emp_line.increment_raise_amount and emp.gross_salary else 0,
                #             'doc_state': emp.doc_state,
                #             'state': emp.state,
                #             'url': ("%s/web#id=%s&action=839&model=appraisal.system&view_type=form&cids=&menu_id=" % (
                #             base_url, emp.id)),
                #         }
                #         grouped_departments[dept.name][manager_name].append(record)

        # Add the grouped data to the report data dictionary
        data['records'] = {dept: dict(managers) for dept, managers in grouped_departments.items()}
        # data['records'] = {dept: dict(managers) for region, dept, managers in grouped_departments_region.items()}

        return self.env.ref('aesl_appraisal_system.appraisal_system_hr_summary_report_pdf').report_action(self, data=data)

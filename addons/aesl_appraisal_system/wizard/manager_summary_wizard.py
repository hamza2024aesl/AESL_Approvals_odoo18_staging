from collections import defaultdict
from odoo import models, fields, api


class ManagerSummaryWizard(models.TransientModel):
    _name = 'manager.summary.wizard'
    _description = 'Manager Summary Report Wizard'

    # employee_id = fields.Many2one('hr.employee', string="Employee", default=lambda self: self._default_employee)
    employee_id = fields.Many2one('hr.employee', string="Manager", default=lambda self: self._get_default_employee())

    @api.model
    def _get_default_employee(self):
        # Login user ka employee ID return karein
        return self.env.user.employee_id.id

    def _get_all_parents(self, employee):
        """Recursively fetch all parent managers from bottom to top."""
        managers = []
        current_employee = employee

        # Traverse up the hierarchy until we reach the top-level manager (no parent)
        while current_employee.parent_id:
            managers.append(current_employee.parent_id.id)  # Add the parent's ID to the list
            current_employee = current_employee.parent_id  # Move to the next parent (up the hierarchy)

        return managers

    def finding_managers(self, employee):
        manager = employee.sudo().parent_id
        manager2 = manager.sudo().parent_id if manager else None
        manager3 = manager2.sudo().parent_id if manager2 else None
        manager4 = manager3.sudo().parent_id if manager3 else None
        manager5 = manager4.sudo().parent_id if manager4 else None

        return {
            'manager1': manager,
            'manager2': manager2,
            'manager3': manager3,
            'manager4': manager4,
            'manager5': manager5
        }

    def print_report(self):
        data = {
            'ids': self.ids,
            'model': 'task.timesheet',
            'form': self.read()[0],
        }
        # Redirect to the report action with the record ID
        employees = self.sudo().env['appraisal.system'].search([('manager_ids', 'in', self.sudo().employee_id.id)])
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        records = []
        for emp in employees:
            if emp.employee_id.name not in records:
                filtered_lines = emp.sudo().recomm_increment_lines_id.filtered(
                    lambda line: line.increment_raise_by.id == self.employee_id.user_id.id)
                if filtered_lines:
                    records.append({
                        'emp_name': emp.employee_id.name,
                        'emp_no': emp.registration_number,
                        'curr_grade': emp.grade,
                        'curr_salary': emp.gross_salary,
                        'curr_designation': emp.job_id.name,
                        'recomm_salary': (filtered_lines.increment_raise_amount + emp.gross_salary) if filtered_lines.increment_raise_amount else 0,
                        'recomm_raise_amount': filtered_lines.increment_raise_amount,
                        'recomm_grade': filtered_lines.recomm_grades,
                        'recomm_designation': filtered_lines.recomm_desigantion_id.name,
                        'percentage': ((filtered_lines.increment_raise_amount / emp.gross_salary) * 100) if filtered_lines.increment_raise_amount and emp.gross_salary else 0,
                        'doc_state': emp.doc_state,
                        'state': emp.state,
                        'url': ("%s/web#id=%s&action=839&model=appraisal.system&view_type=form&cids=&menu_id=" % (base_url, emp.id)),
                    })
                else:
                    if emp.appraisal_approver_id.id == self.employee_id.user_id.id:
                        records.append({
                            'emp_name': emp.employee_id.name,
                            'emp_no': emp.registration_number,
                            'curr_grade': emp.grade,
                            'curr_salary': emp.gross_salary,
                            'curr_designation': emp.job_id.name,
                            'recomm_salary': 0,
                            'recomm_raise_amount': 0,
                            'recomm_grade': '',
                            'recomm_designation': False,
                            'percentage': 0,
                            'doc_state': emp.doc_state,
                            'state': emp.state,
                            'url': ("%s/web#id=%s&action=839&model=appraisal.system&view_type=form&cids=&menu_id=" % (
                            base_url, emp.id)),
                        })

        data['records'] = records

        return self.env.ref('aesl_appraisal_system.appraisal_system_manager_summary_report_pdf').report_action(self, data=data)

    def print_report_all(self):
        data = {
            'ids': self.ids,
            'model': 'task.timesheet',
            'form': self.read()[0],
        }
        # Redirect to the report action with the record ID
        employees = self.sudo().env['appraisal.system'].search([('manager_ids', 'in', self.sudo().employee_id.id)])
        grouped_records = defaultdict(list)
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        records = []
        mngr_nmae = []
        for emp in employees:
            for emp_line in emp.sudo().recomm_increment_lines_id:
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
                        'percentage': ((
                                                   emp_line.increment_raise_amount / emp.gross_salary) * 100) if emp_line.increment_raise_amount and emp.gross_salary else 0,
                        'doc_state': emp.doc_state,
                        'state': emp.state,
                        'url': ("%s/web#id=%s&action=839&model=appraisal.system&view_type=form&cids=&menu_id=" % (
                        base_url, emp.id)),
                    })
        data['records'] = dict(grouped_records)

        return self.env.ref('aesl_appraisal_system.appraisal_system_manager_all_summary_report_pdf').report_action(self, data=data)
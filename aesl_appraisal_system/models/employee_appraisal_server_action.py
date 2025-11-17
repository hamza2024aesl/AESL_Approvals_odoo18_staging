# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class InheritApraisalSystems(models.Model):
    _inherit = 'appraisal.system'

    def action_approve_appraisal_to_employee(self):
        for record in self:
            increment_grade = ""
            increment_designation = ""
            if record.employee_id and record.doc_state != 'publish':
                record.doc_state = 'publish'
                if record.recomm_increment_lines_id[-1].recomm_desigantion_id and \
                        record.recomm_increment_lines_id[-1].recomm_desigantion_id != record.sudo().employee_id.job_id:
                    increment_designation = record.recomm_increment_lines_id[-1].recomm_desigantion_id.name

                if record.recomm_increment_lines_id[-1].recomm_grades and \
                        record.recomm_increment_lines_id[-1].recomm_grades != int(record.sudo().employee_id.x_studio_grade):
                    increment_grade = record.recomm_increment_lines_id[-1].recomm_grades

                self.env['employee.appraisal.history'].create({
                    'appraisal_history_id': record.employee_id.id,
                    'employee_id': record.employee_id.id,
                    'increment_amount': record.recomm_increment,
                    'recommended_grade': increment_grade,
                    'recommended_designation': increment_designation,
                    'year': record.write_date.date().year,
                    'appraisal_date': record.write_date.date(),
                    'company_id': record.sudo().employee_id.company_id.id,
                    'personal_file_no': record.sudo().employee_id.x_studio_personal_file_number,
                    'gross_salary': record.sudo().employee_id.contract_id.wage,
                    'department': record.sudo().employee_id.department_id.name,
                    'designation': record.sudo().employee_id.job_id.name,
                    'location': record.sudo().employee_id.location_id.emp_location,
                })
        return {
            'effect': {
                'fadeout': 'slow',
                'message': 'Appraisal has sent to employee',
                'type': 'rainbow_man',
            }
        }

    def action_appraisal_to_employee_contract1(self):
        for record in self:
            if record.employee_id and record.doc_state == 'publish':
                contract = self.env['hr.contract'].search([('employee_id','=',record.employee_id.id),('state','=','open')])
                contract.write({
                    'wage': contract.wage + record.recomm_increment if record.recomm_increment else contract.wage
                })
            else:
                raise ValidationError(_("Contract wage will be updated only for 'Published' records"))

    def action_appraisal_to_employee_contract_backup2(self):
        for record in self:
            if record.employee_id:
                contract = self.env['hr.contract'].search([('employee_id','=',record.employee_id.id),('state','=','open')])
                contract.write({
                    'wage': contract.wage + record.recomm_increment if record.recomm_increment else contract.wage
                })
            return {
                'effect': {
                    'fadeout': 'slow',
                    'message': 'Contract salary has been updated',
                    'type': 'rainbow_man',
                }
            }

    def action_appraisal_to_employee_contract(self):
        for record in self:
            if record.employee_id and record.doc_state == 'publish':
                contract = self.env['hr.contract'].search([('employee_id','=',record.employee_id.id),('state','=','open')])
                employee = self.env['hr.employee'].search([('id','=',record.employee_id.id),('active','=','True')])
                contract.write({
                    # 'wage': contract.wage + record.recomm_increment if record.recomm_increment else contract.wage,
                    'job_id': record.recommend_designation_id.id if record.recommend_designation_id else contract.job_id
                })
                employee.write({
                    'job_id': record.recommend_designation_id.id if record.recommend_designation_id else employee.job_id,
                    'x_studio_grade':record.recommend_grades if record.recommend_grades > int(employee.x_studio_grade) else employee.x_studio_grade
                })
            else:
                pass

class EmployeeAppraisal(models.Model):
    _name = 'employee.appraisal.history'
    _description = "Employee Appraisal History"

    def _get_default_company(self):
        return self.env.user.company_id

    appraisal_history_id = fields.Many2one('hr.employee', string='Employee Appraisal Lines', required=True, index=True,
                                         ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', required=True, string='Name', index=True)
    increment_amount = fields.Float(string="Increment Amount")
    recommended_grade = fields.Char('Recomm. Grade')
    recommended_designation = fields.Char('Recomm. Designation')
    year = fields.Char(string="Year")
    company_id = fields.Many2one('res.company', store=True, default=_get_default_company)
    personal_file_no = fields.Char()
    gross_salary = fields.Char()
    department = fields.Char()
    designation = fields.Char()
    location = fields.Char()
    appraisal_date = fields.Datetime()


    def action_print_report(self):
        data = {
            'ids': self.ids,
            'model': 'employee.appraisal.history',
            'form': self.read()[0],
            'company': self.company_id.name
        }

        # if self.department == 'CE':
        #     dept = 'ENGINE CATERPILLAR'
        # if self.department == 'CM':
        #     dept = 'MACHINE CATERPILLAR'
        # if self.department == 'CO':
        #     dept = 'SERVICES S. O. S. LAB'
        # if self.department == 'CP':
        #     dept = 'PARTS CATERPILLAR'
        # if self.department == 'CS':
        #     dept = 'SERVICE ENGINE CATERPILLAR'
        # if self.department == 'CU':
        #     dept = 'SOLAR DEPARTMENT'
        # if self.department == 'DD':
        #     dept = 'GRUNDFOS PUMP'
        # if self.department == 'GA':
        #     dept = 'GENERAL ADMINISTRATION'
        # if self.department == 'GE':
        #     dept = 'ENGINE G.O.'
        # if self.department == 'GF':
        #     dept = 'GENERAL FINANCE'
        # if self.department == 'GM':
        #     dept = 'GENERAL TECHNICAL CELL'
        # if self.department == 'GI':
        #     dept = 'INFORMATION TECHNOLOGY'
        # if self.department == 'GM':
        #     dept = 'MACHINES G.O.'
        # if self.department == 'GP':
        #     dept = 'GENERAL SALES ADMIN'
        # if self.department == 'GN':
        #     dept = 'PARTS G.O.'
        # if self.department == 'GS':
        #     dept = 'SERVICE G.O.'
        # if self.department == 'GU':
        #     dept = 'GENERAL SOLAR DEPARTMENT'
        # if self.department == 'IS':
        #     dept = 'COMPRESSOR SERVICE'
        # if self.department == 'ID':
        #     dept = 'COMPRESSOR SALES'
        # if self.department == 'NP':
        #     dept = 'COMPRESSOR PARTS'
        # if self.department == 'OE':
        #     dept = 'ENGINE OLYMPIAN'
        dept = ''
        # Using a dictionary to map department abbreviations to their corresponding names
        department_mapping = {
            'CE': 'ENGINE CATERPILLAR',
            'CM': 'MACHINE CATERPILLAR',
            'CO': 'SERVICES S. O. S. LAB',
            'CP': 'PARTS CATERPILLAR',
            'CS': 'SERVICE ENGINE CATERPILLAR',
            'CU': 'SOLAR DEPARTMENT',
            'DD': 'GRUNDFOS PUMP',
            'GA': 'GENERAL ADMINISTRATION',
            'GE': 'ENGINE G.O.',
            'GF': 'GENERAL FINANCE',
            'GM': 'MACHINES G.O.',
            'GI': 'INFORMATION TECHNOLOGY',
            'GN': 'GENERAL SALES ADMIN',
            'GP': 'PARTS G.O.',
            'GS': 'SERVICE G.O.',
            'GU': 'GENERAL SOLAR DEPARTMENT',
            'IS': 'COMPRESSOR SERVICE',
            'ID': 'COMPRESSOR SALES',
            'NP': 'COMPRESSOR PARTS',
            'OE': 'ENGINE OLYMPIAN'
        }

        # Get the department name from the mapping
        dept = department_mapping.get(self.department, '')

        # is_increment_amount = None
        # is_increment_designation = None
        # is_increment_grade = None
        # appraisal_history = self.env['appraisal.system'].search([('employee_id', '=', self.sudo().employee_id.id)])
        # if appraisal_history.recomm_increment_lines_id[-1].increment_raise_amount and appraisal_history.recomm_increment_lines_id[-1].increment_raise_amount > 1:
        #     is_increment_amount = True
        # if appraisal_history.recomm_increment_lines_id[-1].recomm_desigantion_id and appraisal_history.recomm_increment_lines_id[-1].recomm_desigantion_id != appraisal_history.sudo().employee_id.job_id:
        #     is_increment_designation = True
        # if appraisal_history.recomm_increment_lines_id[-1].recomm_grades and appraisal_history.recomm_increment_lines_id[-1].recomm_grades != int(appraisal_history.sudo().employee_id.x_studio_grade):
        #     is_increment_grade = True
        data['appraisal_history'] = [{'emp_name':self.employee_id.name,
                                     'file_no': self.personal_file_no,
                                     # 'emp_no': self.registration_number,
                                     'designation': self.designation,
                                     'location': self.location,
                                     'department': dept,
                                     'new_salary': float(self.gross_salary) + self.increment_amount,
                                     # 'date': self.create_date.strftime('%B %d, %Y'),
                                     'date': self.create_date.strftime('%B %d, %Y'),
                                      'increment_amount': self.increment_amount,
                                      'increment_designation': self.recommended_designation,
                                      'increment_grade': self.recommended_grade,
                                      'company': self.company_id.name,
                                     }]
        return self.env.ref('aesl_appraisal_system.action_report_appraisal_letter_pdf').report_action(self,data=data)


class HrEmployeeInherited(models.Model):
    _inherit = 'hr.employee'

    # increment_history_ids = fields.One2many(
    #     'employee.increment.history', 'employee_id', string="Increment History"
    # )
    appraisal_history_line_ids = fields.One2many('employee.appraisal.history', 'appraisal_history_id',
                                                string='Employee Appraisal Lines',
                                                required=True, index=True)


    def action_view_increment_history(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Last Appraisal',
            'view_mode': 'list',
            'res_model': 'employee.appraisal.history',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }

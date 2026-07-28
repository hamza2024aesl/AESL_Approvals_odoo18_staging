from odoo import models, fields, _
from odoo.exceptions import ValidationError


class EmployeeAppraisalHistory(models.Model):
    _name = 'employee.appraisal.history'

    def _get_default_company(self):
        return self.env.user.company_id

    appraisal_history_id = fields.Many2one('hr.employee', string='Employee Appraisal Lines', required=True, index=True, ondelete='cascade')
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
        data['appraisal_history'] = [{
            'emp_name': self.employee_id.name,
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
        return self.env.ref('aesl_appraisal_system.action_report_appraisal_letter_pdf').report_action(self, data=data)

    def action_appraisal_amount_to_employee_contract(self):
        for record in self:
            if record.employee_id:
                contract = self.env['hr.contract'].search([
                    ('employee_id', '=', record.employee_id.id),
                    ('state', '=', 'open')
                ])
                contract.write({
                    'wage': contract.wage + record.increment_amount if record.increment_amount else contract.wage,
                })
            else:
                raise ValidationError(_("Contract wage will be updated only for 'Published' records"))
            return {
                'effect': {
                    'fadeout': 'slow',
                    'message': 'Contract salary has been updated',
                    'type': 'rainbow_man',
                }
            }

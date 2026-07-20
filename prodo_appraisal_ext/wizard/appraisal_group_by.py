from odoo import models, fields, api, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError
from dateutil import relativedelta

from datetime import date
from datetime import datetime



class HrAppraisalGroupBy(models.Model):
    _name = 'appraisal.group.by'

    mode = fields.Selection([
        ('department', 'Department'),
        ('company', 'Company')
    ], readonly=True)

    department_id = fields.Many2one('hr.department', string="Department")
    company_id = fields.Many2one('res.company', string="Company")
    appraisal_batch_id = fields.Many2one('appraisal.batches', string='Appraisal Batch')

    def action_confirm(self):
        if self.mode == 'department':
            department_employees = self.env['hr.employee'].search([('department_id','=',self.department_id.id)])
            for department_employee in department_employees:
                self.env['hr.appraisal'].create({
                    'employee_id':department_employee.id,
                    'manager_ids':[(6, 0, [department_employees.parent_id[0].id])],
                    'department_id':self.department_id.id,
                    'appraisal_batch_id':self.appraisal_batch_id.id
                })
        elif self.mode == 'company':
            company_employees = self.env['hr.employee'].search([('company_id', '=', self.company_id.id)])
            for company_employee in company_employees:
                self.env['hr.appraisal'].create({
                    'employee_id': company_employee.id,
                    'appraisal_batch_id': self.appraisal_batch_id.id
                })

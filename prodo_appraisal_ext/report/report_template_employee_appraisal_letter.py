from odoo import models, api

class AppraisalReport(models.AbstractModel):
    _name = "report.prodo_appraisal_ext.template_employee_appraisal_letter"
    _description = "Appraisal Letter Report"

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env["hr.appraisal"].browse(docids)
        #
        # data['appraisal_history'] = [{'emp_name':self.employee_id.name,
        #                              'file_no': self.personal_file_no,
        #                              # 'emp_no': self.registration_number,
        #                              'designation': self.designation,
        #                              'location': self.location,
        #                              'department': dept,
        #                              'new_salary': float(self.gross_salary) + self.increment_amount,
        #                              # 'date': self.create_date.strftime('%B %d, %Y'),
        #                              'date': self.create_date.strftime('%B %d, %Y'),
        #                               'increment_amount': self.increment_amount,
        #                               'increment_designation': self.recommended_designation,
        #                               'increment_grade': self.recommended_grade,
        #                               'company': self.company_id.name,
        #                              }]
        # appraisal_history = self._prepare_appraisal_history(docs)
        # form = self._prepare_form_values(docs)
        company = docs.company_id.name

        return {
            'doc_ids': docids,
            'doc_model': 'hr.appraisal',
            'docs': docs,
            'company': company,
            'appraisal': docs,
        }
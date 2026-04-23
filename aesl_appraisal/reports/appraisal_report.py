from odoo import models, api

class AppraisalReport(models.AbstractModel):
    _name = "report.aesl_appraisal.template_employee_appraisal_letter123"
    _description = "Appraisal Letter Report"

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env["hr.contract"].browse(docids)
        company = docs.company_id.name
        contract = False
        increment = 0
        contract = self.env['hr.contract'].sudo().search([
            ('employee_id', '=', docs.employee_id.id),
            ('state', '=', 'open'),
        ], limit=1)

        contract_exp = self.env['hr.contract'].sudo().search([
            ('employee_id', '=', docs.employee_id.id),
            ('state','=','close'),
            ('date_end','=','2025-12-31')
        ], limit=1)

        if contract.wage != contract_exp.wage:
            increment = contract.wage - contract_exp.wage

        values = {
            'contract': contract,
            'increment' : increment,
            'wage': contract.wage if contract_exp and contract.wage != contract_exp.wage else False,
            'job_id': contract.job_id.name if contract.job_id != contract_exp.job_id else '',
            'grade': contract.x_studio_grade if contract.x_studio_grade != contract_exp.x_studio_grade else ''
        }

        return {
            'doc_ids': docids,
            'doc_model': 'hr.contract',
            'docs': docs,
            'company': company,
            'appraisal': docs,
            'values': values
        }
from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal
import logging
_logger = logging.getLogger(__name__)

class AppraisalPortal(http.Controller):

    @http.route(['/my/appraisal'], type='http', auth='user', methods=["POST", "GET"], website=True)
    def portal_my_appraisal(self, **kw):

        _logger.info("Portal appraisal route hit")

        user = request.env.user
        employee = user.employee_id

        _logger.info("User ID: %s | Employee: %s", user.id, employee.id if employee else None)

        contract = False
        increment = 0

        if employee:
            contract = request.env['hr.contract'].sudo().search([
                ('employee_id', '=', employee.id),
                ('state', '=', 'open'),
            ], limit=1)

            _logger.info("Running contract: %s | Wage: %s", contract.id if contract else None,
                         contract.wage if contract else None)


            # contract_exp = request.env['hr.contract'].sudo().search([
            #     ('employee_id', '=', employee.id),
            #     ('state', '=', 'close'),
            #     ('date_end', '=', '2025-12-31')
            # ], limit=1)

            contract_exp = request.env['hr.contract'].sudo().search([
                ('employee_id', '=', employee.id),
                ('state', '=', 'close')
            ], order='date_end desc', limit=1)

            _logger.info(
                "Expired contract: %s | Wage: %s",
                contract_exp.id if contract_exp else None,
                contract_exp.wage if contract_exp else None
            )

            if contract and contract_exp and contract.wage != contract_exp.wage:
                increment = contract.wage - contract_exp.wage
                _logger.info("Increment calculated: %s", increment)
            else:
                _logger.info("No increment or contract missing")

        #values = {
        #    'employee': employee,
        #    'contract': contract,
        #    'increment': increment,
        #    'wage': contract.wage if contract and contract_exp and contract.wage != contract_exp.wage else False,
        #    'job_id': contract.job_id.name if contract and contract_exp and contract.job_id != contract_exp.job_id else '',
        #    'grade': contract.x_studio_grade if contract and contract_exp and contract.x_studio_grade != contract_exp.x_studio_grade else ''
        #}

        values = {
            'employee': employee,
            'contract': contract,
            'increment': increment,
            'wage': contract.wage,
            'job_id': contract.job_id.name,
            'grade': contract.x_studio_grade
        }


        _logger.info("Portal appraisal values sent: %s", values)

        return request.render(
            'aesl_appraisal.portal_employee_contract',
            values
        )

    # @http.route(['/my/appraisal'], type='http', auth='user', website=True)
    # def portal_my_appraisal(self, **kw):
    #     user = request.env.user
    #     employee = user.employee_id
    #
    #     contract = False
    #     increment = 0
    #     if employee:
    #         contract = request.env['hr.contract'].sudo().search([
    #             ('employee_id', '=', employee.id),
    #             ('state', '=', 'open'),
    #         ], limit=1)
    #
    #         contract_exp = request.env['hr.contract'].sudo().search([
    #             ('employee_id', '=', employee.id),
    #             ('state','=','close'),
    #             ('date_end','=','2025-12-31')
    #         ], limit=1)
    #
    #         if contract.wage != contract_exp.wage:
    #             increment = contract.wage - contract_exp.wage
    #
    #     values = {
    #         'employee': employee,
    #         'contract': contract,
    #         'increment' : increment,
    #         'wage': contract.wage if contract_exp and contract.wage != contract_exp.wage else False,
    #         'job_id': contract.job_id.name if contract.job_id != contract_exp.job_id else '',
    #         'grade': contract.x_studio_grade if contract.x_studio_grade != contract_exp.x_studio_grade else ''
    #     }
    #     return request.render(
    #         'aesl_appraisal.portal_employee_contract',
    #         values
    #     )

    @http.route('/my/appraisal/print', type='http', auth='user', website=True)
    def portal_print_appraisal(self,**kw):

        user = request.env.user
        employee = user.employee_id
        # cont_id = request.env['hr.contract'].sudo().search(contract_id)

        if not employee:
            return request.redirect('/my')

        # Running contract
        contract = request.env['hr.contract'].sudo().search([
            ('employee_id', '=', employee.id),
            ('state', '=', 'open')
        ], limit=1)

        if not contract:
            return request.redirect('/my/appraisal')

        # Pass contract to PDF template
        data = {
            'contract': contract
        }

        report = request.env.ref(
            'aesl_appraisal.action_report_appraisal123'
        ).sudo()


        return self._show_report(model=contract, report_type='pdf', report_ref=report, download=True)
        # return report.report_action(model=contract, report_type='pdf', report_ref=report, download=True)
        # return report.report_action(contract)


    # @http.route('/my/appraisal/print/<int:appraisal_id>', type='http', auth='user', website=True)
    # def appraisal_letter_download(self, appraisal_id, **kw):
    #
    #     appraisal = request.env['hr.appraisal'].sudo().browse(appraisal_id)
    #     if not appraisal.exists():
    #         return request.redirect('/my')
    #
    #     report = request.env.ref(
    #         'aesl_appraisal.action_report_appraisal123'
    #     )
    #
    #     pdf_content, _ = report._render_qweb_pdf(
    #         res_ids=[appraisal.id],
    #         data={}
    #     )
    #
    #     return request.make_response(
    #         pdf_content,
    #         headers=[
    #             ('Content-Type', 'application/pdf'),
    #             ('Content-Disposition',
    #              'attachment; filename="Appraisal_Letter_%s.pdf"' % appraisal.name)
    #         ]
    #     )



    # def _prepare_home_portal_values(self, counters):
    #     values = super()._prepare_home_portal_values(counters)
    #
    #     # Get current user's employee
    #     employee = request.env.user.employee_ids
    #
    #     if employee:
    #         # Get active contract for the employee
    #         contract = request.env['hr.contract'].search([
    #             ('employee_id', '=', employee.id),
    #             ('state', '=', 'open')
    #         ], limit=1)
    #
    #         # Add contract count to portal values
    #         values['appraisal_count'] = 1 if contract else 0
    #
    #     return values
    #
    # @http.route('/my/appraisal', type='http', auth="user", website=True)
    # def my_appraisal(self, **kw):
    #     # Get current user
    #     user = request.env.user
    #
    #     # Get employee associated with the user
    #     employee = user.employee_ids
    #
    #     if not employee:
    #         # If no employee found, redirect to home
    #         return request.redirect('/my')
    #
    #     # Get active contract for the employee
    #     contract = request.env['hr.contract'].search([
    #         ('employee_id', '=', employee.id),
    #         ('state', '=', 'open')
    #     ], limit=1)
    #
    #     # Prepare template values
    #     values = {
    #         'contract': contract,
    #         'page_name': 'appraisal',
    #         'default_url': '/my/appraisal',
    #     }
    #
    #     # Add portal-specific values
    #     values = self._prepare_portal_layout_values(values)
    #
    #     return request.render("aesl_appraisal.portal_my_appraisal", values)

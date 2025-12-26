import calendar
import datetime
import time
from collections import defaultdict

from odoo.addons.portal.controllers.portal import CustomerPortal, pager
from pytz import timezone

from odoo import http, _, fields
from odoo.exceptions import AccessDenied, UserError
from odoo.http import request
from odoo.tools import float_round
from odoo.exceptions import UserError, ValidationError
from odoo.http import request, Response
import json

class AppraisalPortal(CustomerPortal):


    # -------------------------------------------------------------
    # LIST VIEW – ONLY SHOW RECORDS FOR CURRENT APPROVER
    # -------------------------------------------------------------
    @http.route(["/my/appraisal", "/my/appraisal/page/<int:page>"],
                type="http", auth="user", website=True)
    def portal_appraisal_list(self, page=1, group_by=None,**kw):

        user = request.env.user
        appraisal_obj = request.env["hr.appraisal"]

        # Only records waiting for the logged-in user
        domain = ['|',("current_approver_id", "=", user.id),("appraisal_employee_id", "=", user.id)]

        total = appraisal_obj.sudo().search_count(domain)
        appraisals = appraisal_obj.sudo().search(domain)
        for appraisal in appraisals:
            appraisal._leaves_count()

        # If grouping is enabled, apply grouping logic
        grouped_appraisal = False
        if group_by:
            grouped_appraisal = defaultdict(list)
            for appraisal in appraisals:
                if group_by == 'department':
                    # Group by department
                    group_key = appraisal.employee_id.department_id.name if appraisal.employee_id.department_id else 'No Department'
                elif group_by == 'appraisal_deadline':
                    # Group by appraisal deadline (assuming it's a date field)
                    group_key = appraisal.date_close.strftime(
                        '%B %Y') if appraisal.date_close else 'No Deadline'
                else:
                    group_key = 'Ungrouped'

                grouped_appraisal[group_key].append(appraisal)

        page_detail = pager(
            url='/my/appraisal',
            total=len(grouped_appraisal) if grouped_appraisal else len(appraisals),
            page=page,
            url_args={'group_by': group_by},
            step=35,
        )

        vals = {
            "page_name": "view_appraisal_page",
            "appraisals": appraisals,  # You should pass the grouped data here
            'grouped_appraisal': grouped_appraisal,
            'pager': page_detail,
            'group_by': group_by,
        }

        return request.render("prodo_user_portal.appraisal_list_view_portal", vals)

    # -------------------------------------------------------------
    # DETAIL PAGE
    # -------------------------------------------------------------
    @http.route("/my/appraisal/view/<int:appraisal_id>",
                type="http", auth="user", website=True)
    def portal_appraisal_detail(self, appraisal_id):

        appraisal = request.env["hr.appraisal"].sudo().browse(appraisal_id)
        if not appraisal.exists():
            return request.redirect("/my/appraisal")

        user = request.env.user
        desigantions = request.env["hr.job"].sudo().search([])

        vals = {
            "page_name": "view_appraisal_detail_page",
            "appraisal": appraisal,
            "user": user,
            "desigantions": desigantions,
        }
        return request.render("prodo_user_portal.appraisal_detail_page_portal", vals)

    # -------------------------------------------------------------
    # PORTAL SUBMIT – SINGLE ENTRY POINT
    # -------------------------------------------------------------
    @http.route(["/my/appraisal/view/save"],type="http", auth="user", website=True, methods=["POST"])
    def portal_appraisal_save(self, **post):

        appraisal_id = int(post.get("appraisal_id"))
        appraisal = request.env["hr.appraisal"].sudo().browse(appraisal_id)
        if not appraisal.exists():
            return request.redirect("/my/appraisal")

        user = request.env.user

        # ---- Manager adding their remarks or increment ----

        # ------------------------------------------------------------------
        # Save increment line from portal
        # ------------------------------------------------------------------
        increment_amount = float(post.get("increment_raise_amount") or 0)
        desig_id = int(post.get("recomm_desigantion_id") or 0)
        grades = post.get("recomm_grades") or ""

        vals_increment_line = False
        if increment_amount or desig_id or grades:
            vals_increment_line = {
                "increment_raise_amount": increment_amount,
                "recomm_desigantion_id": desig_id,
                "recomm_grades": grades,
            }
        #
        # if vals_write:
        #     appraisal.write(vals_write)

        # ------------------------------------------------------------------
        # CALL BACKEND ACTION BASED ON STATE
        # ------------------------------------------------------------------

        if post.get('action_type') == 'save':
            appraisal.save_recom_incrment(vals_increment_line)
            #
            # if vals_write:
            #     appraisal.write(vals_write)

            # ------------------------------------------------------------------
            # CALL BACKEND ACTION BASED ON STATE
            # ------------------------------------------------------------------
            if appraisal.state == "new" or appraisal.state == "pending" or appraisal.state == "executive":
                remark_text = post.get("remarks") or post.get("new_remark")
                if remark_text:
                    appraisal._save_manager_remark(remark_text)

                future_prospect_text = post.get("future_project") or ""
                if future_prospect_text:
                    appraisal._save_line_manager_prospect(future_prospect_text)

                # appraisal.save_recom_incrment(vals_increment_line)
        #
        # if vals_write:
        #     appraisal.write(vals_write)

        elif post.get('action_type') == 'unlink':
            # appraisal.unlink()
            return request.redirect(f"/my/appraisal/view/{appraisal.id}")

            # print("unlink_increament")
            # appraisal.unlink_remarks()
            # print("unlink_remarks")


        else:
            if appraisal.state == "new" or appraisal.state == "pending" or appraisal.state == "executive":
                remark_text = post.get("new_remark") or post.get("remarks")
                if remark_text:
                    appraisal._append_manager_remark(remark_text)

                future_prospect_text = post.get("future_project") or ""
                if future_prospect_text:
                    appraisal._append_line_manager_prospect(future_prospect_text)

                appraisal._portal_submit_manager(vals_increment_line)

            elif appraisal.state == "md":
                appraisal._portal_submit_md(vals_increment_line)

        # Redirect to list view (record should not appear again)
        return request.redirect("/my/appraisal")




        # -------------------------------------------------------------
        # PORTAL SUBMIT – SINGLE ENTRY POINT
        # -------------------------------------------------------------


    @http.route(["/my/appraisal/bulk/approve"], type="http", auth="user", website=True, methods=["POST"], csrf=False)
    def portal_appraisal_bulk_save(self, **post):
        data = json.loads(request.httprequest.data)

        appraisal_ids = data.get("appraisal_ids", [])

        if not appraisal_ids:
            return request.redirect("/my/appraisal")
        if isinstance(appraisal_ids, str):
            # If appraisal_ids is a string, convert it into a list of integers
            appraisal_ids = [int(id) for id in appraisal_ids.split(",") if id.strip().isdigit()]

        elif isinstance(appraisal_ids, list):
            # If it's already a list, we can directly convert each item into an integer
            appraisal_ids = [int(id) for id in appraisal_ids if isinstance(id, str) and id.isdigit()]

        appraisals = request.env["hr.appraisal"].sudo().browse(appraisal_ids)

        if not appraisals.exists():
            return request.redirect("/my/appraisal")  # Redirect if appraisals do not exist

        user = request.env.user
        for appraisal in appraisals:
            last_increment_line = appraisal.recomm_increment_lines_id.sudo().search([], limit=1, order='create_date desc')

            if not last_increment_line:
                return request.redirect("/my/appraisal")
            increment_amount = last_increment_line.increment_raise_amount
            desig_id = last_increment_line.recomm_desigantion_id.id
            grades = last_increment_line.recomm_grades

            # Iterate over the selected appraisals and save the increment line for each one
            # for appraisal in appraisals:
            vals_increment_line = {
                "increment_raise_amount": increment_amount,
                "recomm_desigantion_id": desig_id,
                "recomm_grades": grades,
            }

            if appraisal.state == "md":
                appraisal._portal_submit_md(vals_increment_line)
            else:
                appraisal._portal_submit_manager(vals_increment_line)  # Assuming this method saves the increment line


        return http.Response(
            json.dumps({"success": True, "message": "Appraisals approved successfully"}),
            content_type='application/json'
        )


    @http.route(["/my/form/save"], type="http", auth="user", website=True, methods=["POST"])
    def portal_appraisal_save_button(self, **post):

        appraisal_id = int(post.get("appraisal_id"))
        appraisal = request.env["hr.appraisal"].sudo().browse(appraisal_id)
        if not appraisal.exists():
            return request.redirect("/my/appraisal")

        user = request.env.user
        # ------------------------------------------------------------------
        # Save increment line from portal
        # ------------------------------------------------------------------
        increment_amount = float(post.get("increment_raise_amount") or 0)
        desig_id = int(post.get("recomm_desigantion_id") or 0)
        grades = post.get("recomm_grades") or ""

        vals_increment_line = False
        if increment_amount or desig_id or grades:
            vals_increment_line = {
                "increment_raise_amount": increment_amount,
                "recomm_desigantion_id": desig_id,
                "recomm_grades": grades,
            }

            appraisal.save_recom_incrment(vals_increment_line)
        #
        # if vals_write:
        #     appraisal.write(vals_write)

        # ------------------------------------------------------------------
        # CALL BACKEND ACTION BASED ON STATE
        # ------------------------------------------------------------------
        if appraisal.state == "new" or appraisal.state == "pending" or appraisal.state == "executive":
            remark_text = post.get("new_remark") or ""
            if remark_text:
                appraisal._save_manager_remark(remark_text)

            future_prospect_text = post.get("future_project") or ""
            if future_prospect_text:
                appraisal._save_line_manager_prospect(future_prospect_text)


            #
            # appraisal._portal_submit_manager(vals_increment_line)

        # elif appraisal.state
        #
        #
        # == "md":
        #     appraisal._portal_submit_md(vals_increment_line)

        # Redirect to list view (record should not appear again)
        return request.redirect("/my/appraisal")


    @http.route(["/my/appraisal/download/<int:appraisal_id>"], type="http", auth="user", website=True)
    def _appraisal_letter_download(self, appraisal_id, **kw):
        appraisal_id = request.env['hr.appraisal'].sudo().browse(appraisal_id)
        # action = appraisal_id.sudo().struct_id.sudo().report_id
        report_action = request.env.ref(
            "prodo_appraisal_ext.action_report_appraisal"
        ).sudo()
        return self._show_report(model=appraisal_id, report_type='pdf', report_ref=report_action, download=True)


    @http.route(['/my/revert/appraisal'], type='http', auth="user", website=True, methods=['POST'])
    def revert_apply_submit(self,**post):
        login_user = request.env.user.id
        revert_remarks = post.get("revert_remarks")
        appr_id = int(post.get('appraisal_id'))
        hr_appraisal = request.env['hr.appraisal'].sudo().browse(appr_id)
        if revert_remarks:
            hr_appraisal.action_revert_back(revert_remarks)
            hr_appraisal.revert_remarks = revert_remarks

        return request.redirect("/my/appraisal")
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

                future_prospect_text = post.get("future_prospect_remarks") or post.get("new_prospect")
                if future_prospect_text:
                    appraisal._save_line_manager_prospect(future_prospect_text)


                # appraisal.save_recom_incrment(vals_increment_line)
            request.session['my_appraisal_success'] = "Appraisal save successfully!"
        #
        # if vals_write:
        #     appraisal.write(vals_write)

        elif post.get('action_type') == 'unlink':
            # appraisal.unlink()
            request.session['my_appraisal_success'] = "Appraisal Discard successfully!"

            return request.redirect(f"/my/appraisal/view/{appraisal.id}")

            # print("unlink_increament")
            # appraisal.unlink_remarks()
            # print("unlink_remarks")


        else:
            if appraisal.state == "new" or appraisal.state == "pending" or appraisal.state == "executive":
                remark_text = post.get("new_remark") or post.get("remarks")
                if remark_text:
                    appraisal._append_manager_remark(remark_text)

                future_prospect_text = post.get("new_prospect")
                if future_prospect_text:
                    appraisal._append_line_manager_prospect(future_prospect_text)

                appraisal._portal_submit_manager(vals_increment_line)

            elif appraisal.state == "md":
                appraisal._portal_submit_md(vals_increment_line)

        request.session['my_appraisal_success'] = "Appraisal Save successfully!"

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

            future_prospect_text = post.get("new_prospect") or ""
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
            hr_appraisal._append_revert_remark(revert_remarks)
            # hr_appraisal.revert_remarks = revert_remarks

        return request.redirect("/my/appraisal")


class ApprovalPortal(CustomerPortal):

    @http.route(["/my/travel", "/my/travel/page/<int:page>"], type="http", auth="user", website=True)
    def portal_my_travel_requests(self, page=1, **kw):
        user = request.env.user
        request_obj = request.env["approval.request"]
        
        # User is either the owner or one of the approvers
        domain = ['|', ('request_owner_id', '=', user.id), ('approver_ids.user_id', '=', user.id)]
        
        total = request_obj.sudo().search_count(domain)
        # Simple search for now, pager can be added later if needed
        requests = request_obj.sudo().search(domain, order="create_date desc")
        
        vals = {
            "page_name": "travel_request_list_page",
            "requests": requests,
        }
        return request.render("prodo_user_portal.travel_request_list_view_portal", vals)

    @http.route("/my/travel/new", type="http", auth="user", website=True)
    def portal_travel_request_new(self, **kw):
        user = request.env.user
        employee = user.employee_id
        # Find categories that are suitable for travel
        categories = request.env['approval.category'].sudo().search([])
        
        vals = {
            "page_name": "travel_request_new_page",
            "categories": categories,
            "employee_name": employee.name,
            "employee_identification_id": employee.identification_id,
            "employee_department_id": employee.department_id.name if employee.department_id else "",
            "employee_work_location_id": employee.work_location_id.name if employee.work_location_id else "",
            "employee_job_id": employee.job_id.name if employee.job_id else "",
        }
        return request.render("prodo_user_portal.travel_request_form_portal", vals)

    @http.route("/my/travel/save", type="http", auth="user", website=True, methods=["POST"])
    def portal_travel_request_save(self, **post):
        user = request.env.user
        employee = user.employee_id
        
        try:
            # Prepare values, converting datetime-local format (T) to Odoo format
            raw_start = post.get('date_start')
            raw_end = post.get('date_end')
            date_start = raw_start.replace('T', ' ') if raw_start else False
            date_end = raw_end.replace('T', ' ') if raw_end else False

            vals = {
                'name': f"Travel Request - {employee.name}",
                'request_owner_id': user.id,
                'category_id': int(post.get('category_id')),
                'date_start': date_start,
                'date_end': date_end,
                'travel_mode': post.get('travel_mode'),
                'travel_request_type': post.get('travel_request_type'),
                'tickets_required': post.get('tickets_required'),
                'admin_remarks': post.get('admin_remarks'),
                'employee_id': employee.id,
            }
            
            travel_req = request.env['approval.request'].sudo().create(vals)
            
            # Create schedule lines from the form's grid
            for i in range(1, 7):
                dept = post.get(f'schedule_departure_from_{i}')
                arr = post.get(f'schedule_arrival_destination_{i}')
                date = post.get(f'schedule_arrival_date_{i}')
                time = post.get(f'schedule_arrival_time_{i}')
                
                if dept and arr and date and time:
                    request.env['approval.travel.schedule'].sudo().create({
                        'request_id': travel_req.id,
                        'departure_from': dept,
                        'arrival_destination': arr,
                        'arrival_date': date,
                        'arrival_time': time,
                    })
            
            # Confirm the request to trigger approver assignment
            travel_req.action_confirm()
            
        except UserError as e:
            # Store error in session to show on the form (if template supports it)
            request.session['travel_error'] = str(e)
            return request.redirect("/my/travel/new")
        except Exception as e:
            request.session['travel_error'] = _("An unexpected error occurred: %s") % str(e)
            return request.redirect("/my/travel/new")
            
        return request.redirect("/my/travel")

    @http.route("/my/travel/view/<int:request_id>", type="http", auth="user", website=True)
    def portal_travel_request_detail(self, request_id):
        request_rec = request.env["approval.request"].sudo().browse(request_id)
        if not request_rec.exists():
            return request.redirect("/my/travel")
            
        user = request.env.user
        employee = request_rec.employee_id
        
        is_owner = request_rec.request_owner_id == user
        is_approver = user.id in request_rec.approver_ids.mapped('user_id.id')
        is_editable = is_owner and request_rec.request_status == 'new'
        
        categories = request.env['approval.category'].sudo().search([])
        
        vals = {
            "page_name": "travel_request_detail_page",
            "request_rec": request_rec,
            "employee_name": employee.name,
            "employee_identification_id": employee.identification_id,
            "employee_department_id": employee.department_id.name if employee.department_id else "",
            "employee_work_location_id": employee.work_location_id.name if employee.work_location_id else "",
            "employee_job_id": employee.job_id.name if employee.job_id else "",
            "is_approver": is_approver,
            "is_editable": is_editable,
            "categories": categories,
        }
        return request.render("prodo_user_portal.travel_request_detail_template", vals)

    @http.route("/my/travel/approve/<int:request_id>", type="http", auth="user", website=True)
    def portal_travel_request_approve(self, request_id):
        request_rec = request.env["approval.request"].sudo().browse(request_id)
        if request_rec.exists():
            approver = request_rec.approver_ids.filtered(lambda a: a.user_id == request.env.user)
            if approver:
                request_rec.action_approve(approver=approver[0])
        return request.redirect(f"/my/travel/view/{request_id}?message=approved")

    @http.route("/my/travel/refuse/<int:request_id>", type="http", auth="user", website=True)
    def portal_travel_request_refuse(self, request_id):
        request_rec = request.env["approval.request"].sudo().browse(request_id)
        if request_rec.exists():
            approver = request_rec.approver_ids.filtered(lambda a: a.user_id == request.env.user)
            if approver:
                request_rec.action_refuse(approver=approver[0])
        return request.redirect(f"/my/travel/view/{request_id}?message=refused")
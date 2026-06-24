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
    def portal_my_travel_requests(self, page=1, group_by=None, **kw):
        user = request.env.user
        request_obj = request.env["approval.request"]
        
        # 1. My Own Requests
        my_requests = request_obj.sudo().search([('request_owner_id', '=', user.id)], order="create_date desc")
        
        # 2. Requests to Approve (where user is approver AND it's pending for them)
        approver_requests = request_obj.sudo().search([
            ('approver_ids.user_id', '=', user.id),
            ('user_status', '=', 'pending'),
            ('request_owner_id', '!=', user.id)
        ], order="create_date desc")
        
        # 3. Finance/Admin Tasks (only approved requests)
        user_finance_lines = request.env['approval.config.line'].sudo().search([
            ('employee_id.user_id', '=', user.id),
            ('line_type', '=', 'finance')
        ])
        
        finance_requests = request.env["approval.request"].sudo()
        if user_finance_lines:
            for line in user_finance_lines:
                finance_domain = [
                    ('travel_request_type', '=', line.config_id.config_type),
                    ('employee_location_id', 'in', line.work_location_ids.ids),
                    ('employee_department_id', '=', line.department_id.id),
                    ('request_status', '=', 'approved'),
                    ('request_owner_id', '!=', user.id)
                ]
                finance_requests |= request_obj.sudo().search(finance_domain)
        
        finance_requests = finance_requests.sorted(key=lambda r: r.create_date, reverse=True)
        
        # Combine all for default list view
        all_requests = (my_requests | approver_requests | finance_requests).sorted(key=lambda r: r.create_date, reverse=True)
        
        grouped_requests = {}
        if group_by:
            if group_by == 'my_requests':
                if my_requests:
                    grouped_requests['My Requests'] = my_requests
            elif group_by == 'approved_requests':
                if finance_requests:
                    grouped_requests['Approved Requests'] = finance_requests
            elif group_by == 'to_approve_requests':
                if approver_requests:
                    grouped_requests['Requests To Approve'] = approver_requests

        vals = {
            "page_name": "travel_request_list_page",
            "requests": all_requests,
            "grouped_requests": grouped_requests,
            "group_by": group_by,
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
                'company_id': employee.company_id.id or user.company_id.id,
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

    @http.route("/my/travel/update", type="http", auth="user", website=True, methods=["POST"])
    def portal_travel_request_update(self, **post):
        request_id = int(post.get('request_id'))
        travel_req = request.env['approval.request'].sudo().browse(request_id)
        if not travel_req.exists():
            return request.redirect("/my/travel")

        try:
            raw_start = post.get('date_start')
            raw_end = post.get('date_end')
            date_start = raw_start.replace('T', ' ') if raw_start else False
            date_end = raw_end.replace('T', ' ') if raw_end else False

            vals = {
                'category_id': int(post.get('category_id')),
                'date_start': date_start,
                'date_end': date_end,
                'travel_mode': post.get('travel_mode'),
                'travel_request_type': post.get('travel_request_type'),
                'tickets_required': post.get('tickets_required'),
                # admin_remarks yahan nahi — sirf Finance&Admin apni route se save karta hai
            }
            travel_req.write(vals)

            # Update schedule lines (Clear and Re-create for simplicity)
            travel_req.travel_schedule_ids.unlink()
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
            
            # Re-confirm to trigger workflow again (reset status to pending)
            travel_req.action_confirm()

        except Exception as e:
            request.session['travel_error'] = str(e)
            return request.redirect(f"/my/travel/view/{request_id}")

        return request.redirect(f"/my/travel/view/{request_id}")


    @http.route("/my/travel/view/<int:request_id>", type="http", auth="public", website=True)
    def portal_travel_request_detail(self, request_id):
        if request.env.user._is_public():
            return request.redirect('/web/login?redirect=/my/travel/view/%s' % request_id)
            
        request_rec = request.env["approval.request"].sudo().browse(request_id)
        if not request_rec.exists():
            return request.redirect("/my/travel")
            
        user = request.env.user
        employee = request_rec.employee_id
        
        is_owner = request_rec.request_owner_id == user
        # Buttons should only show if the current user is an approver AND their status is 'pending' (To Approve)
        is_approver = request_rec.user_status == 'pending'
        # Refused requests should also be editable so they can be fixed and re-submitted
        is_editable = is_owner and request_rec.request_status in ['new', 'refused']

        # Check if current user is Finance&Admin for this request (config se)
        is_finance_admin = False
        if request_rec.employee_id and request_rec.employee_id.work_location_id and request_rec.employee_id.department_id:
            c_type = request_rec.travel_request_type or 'domestic'
            finance_lines = request.env['approval.config.line'].sudo().search([
                ('config_id.config_type', '=', c_type),
                ('line_type', '=', 'finance'),
                ('work_location_ids', 'in', request_rec.employee_id.work_location_id.id),
                ('department_id', '=', request_rec.employee_id.department_id.id),
            ])
            finance_users = finance_lines.mapped('employee_id.user_id')
            if user in finance_users or user.has_group('base.group_system'):
                is_finance_admin = True

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
            "is_finance_admin": is_finance_admin,
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

    @http.route("/my/travel/save_remarks/<int:request_id>", type="http", auth="user", website=True, methods=["POST"])
    def portal_travel_save_remarks(self, request_id, **post):
        """ Finance&Admin sirf admin_remarks save karta hai — koi notification nahi jaati. """
        request_rec = request.env["approval.request"].sudo().browse(request_id)
        if not request_rec.exists():
            return request.redirect("/my/travel")

        user = request.env.user

        # Verify current user is Finance&Admin in config
        is_finance_admin = False
        if request_rec.employee_id and request_rec.employee_id.work_location_id and request_rec.employee_id.department_id:
            c_type = request_rec.travel_request_type or 'domestic'
            finance_lines = request.env['approval.config.line'].sudo().search([
                ('config_id.config_type', '=', c_type),
                ('line_type', '=', 'finance'),
                ('work_location_ids', 'in', request_rec.employee_id.work_location_id.id),
                ('department_id', '=', request_rec.employee_id.department_id.id),
            ])
            finance_users = finance_lines.mapped('employee_id.user_id')
            if user in finance_users or user.has_group('base.group_system'):
                is_finance_admin = True

        if not is_finance_admin:
            return request.redirect(f"/my/travel/view/{request_id}")

        # Silently save remarks — no notification triggered
        admin_remarks = post.get('admin_remarks') or ''
        request_rec.write({'admin_remarks': admin_remarks})

        return request.redirect(f"/my/travel/view/{request_id}?message=remarks_saved")

    @http.route("/my/travel/bulk_action", type="json", auth="user", methods=["POST"])
    def portal_travel_request_bulk_action(self, request_ids, action):
        user = request.env.user
        request_objs = request.env["approval.request"].sudo().browse(request_ids)
        
        count = 0
        for req in request_objs:
            # Only process if the user is a pending approver for this request
            approver = req.approver_ids.filtered(lambda a: a.user_id == user and a.status == 'pending')
            if approver:
                try:
                    if action == 'approve':
                        req.action_approve(approver=approver[0])
                    elif action == 'refuse':
                        req.action_refuse(approver=approver[0])
                    count += 1
                except Exception:
                    continue
        
        return {"success": True, "count": count}

    @http.route("/my/travel/expense/new/<int:request_id>", type="http", auth="user", website=True)
    def portal_travel_expense_new(self, request_id):
        request_rec = request.env["approval.request"].sudo().browse(request_id)
        if not request_rec.exists() or request_rec.request_status != 'approved':
            return request.redirect("/my/travel")
            
        employee = request_rec.employee_id
        
        trip_to = request_rec.travel_schedule_ids[0].arrival_destination if request_rec.travel_schedule_ids else (request_rec.location or "")
        
        vals = {
            "page_name": "travel_expense_page",
            "request_rec": request_rec,
            "employee_name": employee.name if employee else "",
            "employee_reg_no": employee.identification_id if employee else "",
            "department_name": employee.department_id.name if employee and employee.department_id else "",
            "designation_name": employee.job_id.name if employee and employee.job_id else "",
            "trip_to": trip_to,
            "purpose_of_trip": request_rec.category_id.name or "",
            "period_from": request_rec.date_start.strftime("%Y-%m-%d %H:%M") if request_rec.date_start else "",
            "period_to": request_rec.date_end.strftime("%Y-%m-%d %H:%M") if request_rec.date_end else "",
            "is_readonly": False,
        }
        return request.render("prodo_user_portal.travel_expense_form_portal", vals)

    @http.route("/my/travel/expense/view/<int:expense_id>", type="http", auth="user", website=True)
    def portal_travel_expense_view(self, expense_id):
        expense = request.env["approval.travel.expense"].sudo().browse(expense_id)
        if not expense.exists():
            return request.redirect("/my/travel")
            
        vals = {
            "page_name": "travel_expense_page",
            "request_rec": expense.request_id,
            "expense": expense,
            "employee_name": expense.employee_name,
            "employee_reg_no": expense.employee_reg_no,
            "department_name": expense.department_name,
            "designation_name": expense.designation_name,
            "trip_to": expense.trip_to,
            "purpose_of_trip": expense.purpose_of_trip,
            "period_from": expense.period_from.strftime("%Y-%m-%d %H:%M") if expense.period_from else "",
            "period_to": expense.period_to.strftime("%Y-%m-%d %H:%M") if expense.period_to else "",
            "is_readonly": True,
        }
        return request.render("prodo_user_portal.travel_expense_form_portal", vals)

    @http.route("/my/travel/expense/save", type="http", auth="user", website=True, methods=["POST"])
    def portal_travel_expense_save(self, **post):
        request_id = int(post.get('request_id', 0))
        request_rec = request.env["approval.request"].sudo().browse(request_id)
        
        if not request_rec.exists():
            return request.redirect("/my/travel")
            
        employee = request_rec.employee_id
        
        try:
            trip_to = request_rec.travel_schedule_ids[0].arrival_destination if request_rec.travel_schedule_ids else (request_rec.location or "")
            
            # Main Expense Record
            expense_vals = {
                'request_id': request_rec.id,
                'employee_id': employee.id if employee else False,
                'employee_name': employee.name if employee else "",
                'employee_reg_no': employee.identification_id if employee else "",
                'department_name': employee.department_id.name if employee and employee.department_id else "",
                'designation_name': employee.job_id.name if employee and employee.job_id else "",
                'trip_to': trip_to,
                'purpose_of_trip': request_rec.category_id.name or "",
                'period_from': request_rec.date_start,
                'period_to': request_rec.date_end,
                'date': post.get('expense_date'),
                'advance_by_company': float(post.get('advance_by_company', 0.0)),
                'items_paid_direct': float(post.get('items_paid_direct', 0.0)),
                'state': 'submitted',
            }
            expense = request.env['approval.travel.expense'].sudo().create(expense_vals)
            
            # Lines
            cols = ['fare', 'hotel', 'meals', 'taxi', 'laundry', 'telephone', 'other', 'daily']
            for i in range(1, 8):
                station_from = post.get(f'station_from_{i}')
                station_to = post.get(f'station_to_{i}')
                date_str = post.get(f'date_{i}')
                time_str = post.get(f'time_{i}')
                
                # Check if row has any data
                has_data = any([
                    station_from, station_to, date_str, time_str,
                    float(post.get(f'fare_{i}', 0.0) or 0.0), float(post.get(f'hotel_{i}', 0.0) or 0.0),
                    float(post.get(f'meals_{i}', 0.0) or 0.0), float(post.get(f'taxi_{i}', 0.0) or 0.0),
                    float(post.get(f'laundry_{i}', 0.0) or 0.0), float(post.get(f'telephone_{i}', 0.0) or 0.0),
                    float(post.get(f'other_{i}', 0.0) or 0.0), float(post.get(f'daily_{i}', 0.0) or 0.0)
                ])
                
                if has_data:
                    request.env['approval.travel.expense.line'].sudo().create({
                        'expense_id': expense.id,
                        'station_from': station_from,
                        'station_to': station_to,
                        'date_str': date_str,
                        'time_str': time_str,
                        'fare': float(post.get(f'fare_{i}', 0.0) or 0.0),
                        'hotel_room': float(post.get(f'hotel_{i}', 0.0) or 0.0),
                        'meals': float(post.get(f'meals_{i}', 0.0) or 0.0),
                        'taxi': float(post.get(f'taxi_{i}', 0.0) or 0.0),
                        'laundry': float(post.get(f'laundry_{i}', 0.0) or 0.0),
                        'telephone': float(post.get(f'telephone_{i}', 0.0) or 0.0),
                        'other_expense': float(post.get(f'other_{i}', 0.0) or 0.0),
                        'daily_allowance': float(post.get(f'daily_{i}', 0.0) or 0.0),
                    })
            
            # Trigger Email
            self._send_expense_notification(expense)

        except Exception as e:
            request.session['expense_error'] = str(e)
            return request.redirect(f"/my/travel/expense/new/{request_id}")
            
        return request.redirect(f"/my/travel/expense/view/{expense.id}")

    def _send_expense_notification(self, expense):
        config = request.env['approval.expense.config'].sudo().search([], limit=1)
        if not config:
            return
            
        recipients = []
        if config.expense_payable_id and config.expense_payable_id.work_email:
            recipients.append(config.expense_payable_id.work_email)
        if config.hr_id and config.hr_id.work_email:
            recipients.append(config.hr_id.work_email)
            
        if not recipients:
            return
            
        subject = f"Travel Expense Submitted: {expense.ref_no}"
        body = f"""
        <div style="font-family: Arial, sans-serif; font-size: 14px;">
            <h2 style="color: #8D0000;">Travel Expense Report Submitted</h2>
            <p>Dear Team,</p>
            <p>A new Travel Expense report has been submitted by <strong>{expense.employee_name}</strong> for Travel Request: <strong>{expense.ref_no}</strong>.</p>
            <table style="width: 100%; border-collapse: collapse; margin-top: 15px; margin-bottom: 15px;">
                <tr><td style="padding: 5px; font-weight: bold; width: 30%;">Trip To:</td><td style="padding: 5px;">{expense.trip_to}</td></tr>
                <tr><td style="padding: 5px; font-weight: bold;">Total Expense:</td><td style="padding: 5px;">{expense.total_expense}</td></tr>
                <tr><td style="padding: 5px; font-weight: bold;">Balance Due:</td><td style="padding: 5px; color: #d9534f; font-weight: bold;">{expense.balance_due}</td></tr>
            </table>
            <p>Please check the backend system to view the full details.</p>
            <p>Best Regards,<br/>AESL System</p>
        </div>
        """
        
        mail_values = {
            'subject': subject,
            'body_html': body,
            'email_to': ','.join(recipients),
            'email_from': request.env.company.email or request.env.user.email_formatted,
            'state': 'outgoing',
        }
        request.env['mail.mail'].sudo().create(mail_values).send()
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


class EmployeePortal(CustomerPortal):

    @http.route(['/my', '/my/home'], type='http', auth="user", website=True)
    def _pin_check_popup(self, **kw):
        user = request.env.user
        allow_pin_change = user.company_id.allow_pin_change

        values = {
            'allow_pin_change': allow_pin_change,
        }

        return request.render("portal.portal_my_home", values)

    @http.route(['/my/attendance', '/my/attendance/page/<int:page>'], type="http", methods=["POST", "GET"],
                website=True)
    def _attendance_list_view(self, page=1, sortby='check_in_desc', search="", search_in="check_in_search",
                              group_by=None, **kw):
        sorted_list = {
            'check_in_desc': {'label': 'Newest', 'order': 'check_in desc'},
            'check_in_asc': {'label': 'Oldest', 'order': 'check_in'},
        }

        user = request.env.user
        user_timezone = timezone(user.tz)
        date_format = (lambda lang: f"{lang.date_format} {lang.time_format}")(
            request.env['res.lang'].search([('code', '=', user.lang)], limit=1))
        attendance_obj = request.env['hr.attendance']
        is_manager = bool(request.env['hr.employee'].sudo().search([('parent_id.user_id', '=', user.id)], limit=1))
        subordinate = kw.get('subordinate') == '1'

        search_value = search
        if search != "":
            search_lower = search.lower().strip()
            for i in range(1, 13):
                month_name = calendar.month_name[i].lower()
                if month_name.startswith(search_lower):
                    search_value = f"-{i:02d}-"
                    break

        if subordinate:
            if search != "":
                domain = [
                    '&',
                    ('employee_id.parent_id.user_id.id', '=', user.id),
                    '|',
                    ('employee_id.name', 'ilike', search),
                    '|',
                    ('check_in', 'ilike', search_value),
                    ('check_out', 'ilike', search_value),
                ]
            else:
                domain = [
                    ('employee_id.parent_id.user_id.id', '=', user.id),
                ]
        elif (not is_manager and search != "") or search != "":
            domain = [
                ('employee_id.id', '=', user.employee_id.id),
                '|',
                ('check_in', 'ilike', search_value),
                ('check_out', 'ilike', search_value),
            ]
        else:
            domain = [
                ('employee_id', '=', user.employee_id.id),
            ]

        search_list = {
            'check_in_search': {
                'label': 'Search...',
                'input': 'check_in_search',
                'domain': domain,
            },
        }

        # if search_in == 'check_in_search':
        #     employees = employees_obj.sudo().search([('employee_id', '=', user.employee_id.id), search_domain], limit=80, order=default_order_by, offset=page_detail['offset'])
        #     search_domain = search_list[search_in]['domain']
        #     employees = employees_obj.sudo().search([('employee_id', '=', user.employee_id.id)])
        #     total_attendances = employees_obj.sudo().search_count([('employee_id', '=', user.employee_id.id)])
        # if search_in == 'check_in_search':

        default_order_by = sorted_list[sortby]['order']
        change_request_obj = request.env['my.change.request']
        attendances = attendance_obj.sudo().search(domain, order=default_order_by)
        grouped_attendances = False

        if group_by:
            grouped_attendances = defaultdict(list)
            for attendance in attendances:
                check_in = attendance.check_in.astimezone(user_timezone) if attendance.check_in else None

                if group_by == 'month':
                    group_key = check_in.strftime('%B %Y') if check_in else 'No Month'
                elif group_by == 'year':
                    group_key = check_in.strftime('%Y') if check_in else 'No Year'
                elif group_by == 'employee':
                    group_key = attendance.employee_id.name

                grouped_attendances[group_key].append(attendance)

            page_detail = pager(
                url='/my/attendance',
                total=len(grouped_attendances),
                page=page,
                url_args={
                    'sortby': sortby,
                    'search_in': search_in,
                    'search': search,
                    'group_by': group_by,
                    'subordinate': '1' if subordinate else '0',
                },
                step=35,
            )
        else:
            page_detail = pager(
                url='/my/attendance',
                total=attendance_obj.sudo().search_count(domain),
                page=page,
                url_args={
                    'sortby': sortby,
                    'search_in': search_in,
                    'search': search,
                    'group_by': group_by,
                    'subordinate': '1' if subordinate else '0',
                },
                step=35,
            )
            attendances = attendance_obj.sudo().search(
                domain,
                limit=35,
                offset=page_detail['offset'],
                order=default_order_by,
            )

        if request.httprequest.method == "POST":
            request_id: str = kw.get("id")

            new_check_in = str(kw.get("new_check_in"))
            new_check_out = str(kw.get("new_check_out"))
            check_in_x = datetime.datetime.strptime(new_check_in, "%Y-%m-%dT%H:%M")
            check_out_x = datetime.datetime.strptime(new_check_out, "%Y-%m-%dT%H:%M")
            name = f"{user.employee_id.name} from {check_in_x} to {check_out_x}"

            if not change_request_obj.sudo().search([('attendance_id.id', '=', request_id)]):
                change_request_id = change_request_obj.sudo().create({
                    "attendance_id": request_id,
                    "name": name,
                    "state": "first",
                    "reason": kw.get("reason"),
                    "description": kw.get("desc"),
                    "new_check_in": check_in_x,
                    "new_check_out": check_out_x,
                })
                attendance_obj.sudo().browse(int(request_id)).write({
                    "change_request": change_request_id,
                    "request_created": True
                })
        else:
            pass
        vals = {
            'grouped_attendances': grouped_attendances,
            'group_by': group_by,
            'is_manager': is_manager,
            'subordinate': subordinate,
            'attendances': attendances,
            'page_name': 'attendance_list_view',
            'pager': page_detail,
            'sortby': sortby,
            'searchbar_sortings': sorted_list,
            'search_in': search_in,
            'searchbar_inputs': search_list,
            'search': search,
            'timezone': user_timezone,
            'date_format': date_format,
        }

        return request.render("ivis_user_portal.employee_list_view_portal", vals)

    @http.route(['/my/leaves', '/my/leaves/page/<int:page>'], type="http", methods=["POST", "GET"], website=True)
    def _leaves_list_view(self, page=1, sortby='start_date', search="", search_in="All", group_by=None, **kw):
        sorted_list = {
            'timeoff_type': {'label': 'Time Off', 'order': 'holiday_status_id'},
            'start_date': {'label': 'Date', 'order': 'date_from desc'},
            'duration': {'label': 'Duration', 'order': 'number_of_days desc'},
            'status': {'label': 'Status', 'order': 'state'},
        }

        user = request.env.user
        date_format = request.env['res.lang'].search([('code', '=', user.lang)], limit=1).date_format
        date_today = datetime.date.today()
        is_manager = bool(request.env['hr.employee'].sudo().search([('parent_id.user_id', '=', user.id)], limit=1))

        subordinate = kw.get('subordinate') == '1'

        # search_domain = search_list[search_in]['domain']
        default_order_by = sorted_list[sortby]['order']
        leaves_obj = request.env['hr.leave']

        search_value = search
        if search != "":
            search_lower = search.lower().strip()
            for i in range(1, 13):
                month_name = calendar.month_name[i].lower()
                if month_name.startswith(search_lower):
                    search_value = f"-{i:02d}-"
                    break

        if subordinate:
            if search != "":
                domain = [
                    '&',
                    ('employee_id.parent_id.user_id.id', '=', user.id),
                    '|',
                    ('request_date_from', 'ilike', search_value),
                    '|',
                    ('request_date_to', 'ilike', search_value),
                    ('holiday_status_id.name', 'ilike', search),
                ]
            else:
                domain = [
                    ('employee_id.parent_id.user_id.id', '=', user.id),
                ]
        elif (not is_manager and search != "") or search != "":
            domain = [
                ('employee_id.id', '=', user.employee_id.id),
                '|',
                ('request_date_from', 'ilike', search_value),
                '|',
                ('request_date_to', 'ilike', search_value),
                ('holiday_status_id.name', 'ilike', search),
            ]
        else:
            domain = [
                ('employee_id', '=', user.employee_id.id),
            ]

        search_list = {
            'All': {
                'label': 'Search...',
                'input': 'All',
                'domain': domain
            },
        }

        current_year = datetime.date.today().year
        leaves_allocation_obj = request.env['hr.leave.allocation']
        allocated_leave_ids = leaves_allocation_obj.sudo().search([
            ('employee_id.user_id', '=', request.env.user.id),
            ('state', '=', 'validate'),
            ('date_from', '<=', f'{current_year}-12-31'),
            ('date_to', '>=', f'{current_year}-01-01'),
        ]).mapped('holiday_status_id.id')

        leaves_types = request.env['hr.leave.type'].sudo().search([
            '|',
            ('id', 'in', allocated_leave_ids),
            ('requires_allocation', '=', 'no')
        ])

        leaves = leaves_obj.sudo().search(domain, order=default_order_by)
        grouped_leaves = False

        if group_by:
            grouped_leaves = defaultdict(list)
            for leave in leaves:
                date_from = leave.request_date_from

                if group_by == 'month':
                    group_key = date_from.strftime('%B %Y') if date_from else 'No Month'
                elif group_by == 'year':
                    group_key = date_from.strftime('%Y') if date_from else 'No Year'
                elif group_by == 'type':
                    group_key = leave.holiday_status_id.name
                elif group_by == 'employee':
                    group_key = leave.employee_id.name

                grouped_leaves[group_key].append(leave)

            page_detail = pager(
                url='/my/leaves',
                total=len(grouped_leaves),
                page=page,
                url_args={
                    'sortby': sortby,
                    'search_in': search_in,
                    'search': search,
                    'group_by': group_by,
                    'subordinate': '1' if subordinate else '0',
                },
                step=35,
            )
        else:
            total_leaves = leaves_obj.sudo().search_count(domain)
            page_detail = pager(
                url='/my/leaves',
                total=total_leaves,
                page=page,
                url_args={
                    'sortby': sortby,
                    'search_in': search_in,
                    'search': search,
                    'group_by': group_by,
                    'subordinate': '1' if subordinate else '0',
                },
                step=35,
            )
            leaves = leaves_obj.sudo().search(
                domain,
                limit=35,
                offset=page_detail['offset'],
                order=default_order_by,
            )

        leaves_allocation = leaves_allocation_obj.sudo().search([('employee_id', '=', request.env.user.employee_id.id)])

        for record in leaves_types:
            name = record.name
            if record.requires_allocation == "yes":
                name = "{name} ({count})".format(
                    name=name,
                    count=_('%g remaining out of %g') % (
                        float_round(record.virtual_remaining_leaves, precision_digits=2) or 0.0,
                        float_round(record.max_leaves, precision_digits=2) or 0.0,
                    ) + (_(' hours') if record.request_unit == 'hour' else _(' days')),
                )
            record.display_name = name

        if request.httprequest.method == "POST":
            date_from_x = kw.get("date_from")
            custom_time1 = "03:00:00"
            fmt_from = datetime.datetime.strptime(f"{date_from_x} {custom_time1}", "%Y-%m-%d %H:%M:%S")

            if kw.get("date_to") and not kw.get("half_day"):
                date_to_x = kw.get("date_to")
                custom_time2 = "12:00:00"
                fmt_to = datetime.datetime.strptime(f"{date_to_x} {custom_time2}", "%Y-%m-%d %H:%M:%S")

            if kw.get('half_day') and kw.get('date_from_period'):
                leaves_obj.sudo().create({
                    "employee_id": request.env.user.employee_id.id,
                    # "holiday_type": 'employee',
                    "holiday_status_id": int(kw.get("timeoff")),
                    "private_name": kw.get("desc"),
                    "request_unit_half": True,
                    "request_date_from_period": kw.get("date_from_period"),
                    "duration_display": kw.get("duration"),
                    "state": "confirm",
                    "request_date_from": kw.get("date_from"),
                    "request_date_to": kw.get("date_from")
                })
            else:
                leaves_obj.sudo().create({
                    "employee_id": request.env.user.employee_id.id,
                    # "holiday_type": 'employee',
                    "holiday_status_id": int(kw.get("timeoff")),
                    "private_name": kw.get("desc"),
                    "date_from": fmt_from,
                    "date_to": fmt_to,
                    "duration_display": kw.get("duration"),
                    "state": "confirm",
                    "request_date_from": kw.get("date_from"),
                    "request_date_to": kw.get("date_to")
                })

            return """
                <script>
                    window.history.back();
                </script>
            """

        manage_leaves_count = request.env['hr.leave'].sudo().search_count([
            ("can_approve", "!=", False),
            ("state", "=", "confirm")
        ])

        leave_lines_map = {}

        for leave in leaves:
            lines = []
            if leave.employee_id and leave.request_date_from:
                fiscal_start = leave.employee_id.contract_id.get_fiscal_date_start(leave.request_date_from)
                fiscal_end = leave.employee_id.contract_id.get_fiscal_date_end(leave.request_date_from)

                leave_types = request.env['hr.leave.type'].search([])

                for leave_type in leave_types:
                    availed = request.env['hr.leave'].sudo().search([
                        ('employee_id', '=', leave.employee_id.id),
                        ('holiday_status_id', '=', leave_type.id),
                        ('state', '=', 'validate'),
                        ('request_date_from', '>=', fiscal_start),
                        ('request_date_to', '<=', fiscal_end),
                        ('id', '!=', leave.id),
                    ])
                    availed_leave = sum(availed.mapped('number_of_days')) or 0.0

                    if leave_type.requires_allocation == 'yes':
                        allocated = request.env['hr.leave.allocation'].sudo().search([
                            ('employee_id', '=', leave.employee_id.id),
                            ('holiday_status_id', '=', leave_type.id),
                            ('state', '=', 'validate'),
                            ('date_from', '<=', fiscal_end),
                            ('date_to', '>=', fiscal_start),
                        ])
                        available_leave = sum(allocated.mapped('number_of_days_display')) or 0.0
                        balance_leave = available_leave - availed_leave
                    else:
                        available_leave = 0.0
                        balance_leave = 0.0

                    lines.append({
                        'leave_type': leave_type.name,
                        'available_leave': available_leave,
                        'availed_leave': availed_leave,
                        'balance_leave': balance_leave,
                    })

            leave_lines_map[leave.id] = lines

        error_message = request.session.pop('leave_error', None)
        vals = {
            'leaves': leaves,
            'grouped_leaves': grouped_leaves,
            'leave_lines_map': leave_lines_map,
            'group_by': group_by,
            'is_manager': is_manager,
            'subordinate': subordinate,
            'leaves_allocation': leaves_allocation,
            'leaves_types': leaves_types,
            'page_name': 'leave_list_view',
            'pager': page_detail,
            'sortby': sortby,
            'searchbar_sortings': sorted_list,
            'search_in': search_in,
            'searchbar_inputs': search_list,
            'search': search,
            'date_today': date_today,
            'manage_leaves_count': manage_leaves_count,
            'date_format': date_format,
            'error_message': error_message,
        }

        return request.render("ivis_user_portal.leave_list_view_portal", vals)

    @http.route(['/my/payslips', '/my/payslips/page/<int:page>'], type="http", website=True)
    def _payslip_list_view(self, page=1, sortby='number_desc', search="", search_in="All", group_by=None, **kw):
        user_timezone = timezone(request.env.user.tz)
        sorted_list = {
            'number_desc': {'label': 'Newest', 'order': 'number desc'},
            'number_asc': {'label': 'Oldest', 'order': 'number'}
        }
        default_order_by = sorted_list[sortby]['order']

        payslips_obj = request.env["hr.payslip"]

        domain = [
            ('employee_id', '=', request.env.user.employee_id.id),
            '|',
            ('state', '=', 'done'),
            ('state', '=', 'paid'), '|', '|',
            ('payslip_run_id.name', 'ilike', search),
            ('number', 'ilike', search),
            ('net_wage', 'ilike', search)
        ]
        search_list = {
            'All': {
                'label': 'Search...',
                'input': 'All',
                'domain': domain,
            },
        }

        total_payslips = payslips_obj.sudo().search_count(domain)
        page_detail = pager(url='/my/payslips', total=total_payslips, page=page,
                            url_args={'sortby': sortby, 'search_in': search_in, 'search': search}, step=12)
        payslips = payslips_obj.sudo().search(domain, limit=12, order=default_order_by, offset=page_detail['offset'])

        grouped_payslips = defaultdict(list)
        if group_by:
            for payslip in payslips:
                date_from = payslip.date_from if payslip.date_from else None

                if group_by == 'month':
                    group_key = date_from.strftime('%B %Y') if date_from else 'No Month'
                elif group_by == 'year':
                    group_key = date_from.strftime('%Y') if date_from else 'No Year'
                grouped_payslips[group_key].append(payslip)

        vals = {
            'payslips': payslips,
            'grouped_payslips': grouped_payslips,
            'group_by': group_by,
            'page_name': 'payslip_list_view',
            'pager': page_detail,
            'sortby': sortby,
            'searchbar_sortings': sorted_list,
            'search_in': search_in,
            'searchbar_inputs': search_list,
            'search': search,
        }

        return request.render("ivis_user_portal.payslip_list_view_portal", vals)

    @http.route(["/my/payslips/view/<model('hr.payslip'):payslip_id>"], type="http", auth="user", website=True)
    def _payslip_view(self, payslip_id, **kw):
        # payslips_obj = request.env["hr.payslip"]
        # payslips = payslips_obj.sudo().search([("employee_id", '=', request.env.user.employee_id.id)])

        vals = {'this_payslip': payslip_id, 'page_name': 'payslip_view_page'}

        return request.render("ivis_user_portal.payslip_view_page_portal", vals)

    @http.route(["/my/payslips/download/<model('hr.payslip'):payslip_id>"], type="http", auth="user", website=True)
    def _payslip_download(self, payslip_id, **kw):
        action = payslip_id.sudo().struct_id.sudo().report_id
        report_action = action if action else "hr_payroll.report_payslip_lang"
        return self._show_report(model=payslip_id, report_type='pdf', report_ref=report_action, download=True)

    @http.route(["/my/payslips/html/<model('hr.payslip'):payslip_id>"], type="http", auth="user", website=True)
    def _payslip_html(self, payslip_id, **kw):
        action = payslip_id.sudo().struct_id.sudo().report_id
        report_action = action if action else "hr_payroll.report_payslip_lang"
        return self._show_report(model=payslip_id, report_type='html', report_ref=report_action, download=True)

    @http.route(["/my/loans", "/my/loans/page/<int:page>"], type="http", methods=["POST", "GET"], website=True)
    def _loan_list_view(self, page=1, sortby="date_applied", search="", search_in="All", group_by=None, **kw):
        sorted_list = {
            'number': {'label': 'Number', 'order': 'name'},
            'date_applied': {'label': 'Date', 'order': 'date_applied desc'},
            'requested_amount': {'label': 'Amount', 'order': 'principal_amount desc'},
            'status': {'label': 'Status', 'order': 'state'}
        }
        default_order_by = sorted_list[sortby]['order']

        loans_obj = request.env['employee.loan.details']

        domain = [
            ('employee_id', '=', request.env.user.employee_id.id),
            '|', '|', '|', '|', '|', '|',
            ('name', 'ilike', search),
            ('date_applied', 'ilike', search),
            ('loan_type.name', 'ilike', search),
            ('date_approved', 'ilike', search),
            ('actual_principal_amount', 'ilike', search),
            ('principal_amount', 'ilike', search),
            ('final_total', 'ilike', search)
        ]
        search_list = {
            'All': {
                'label': 'Search...',
                'input': 'All',
                'domain': domain,
            },
        }

        total_loans = loans_obj.sudo().search_count(domain)
        page_detail = pager(url='/my/loans', total=total_loans, page=page,
                            url_args={'sortby': sortby, 'search_in': search_in, 'search': search}, step=80)
        loans = loans_obj.sudo().search(domain, limit=80, order=default_order_by, offset=page_detail['offset'])
        loan_types = request.env['loan.type'].sudo().search([])
        date_today = (datetime.date.today()).strftime("%Y/%m/%d")

        grouped_loans = defaultdict(list)
        if group_by:
            for loan in loans:
                date_from = loan.date_applied if loan.date_applied else None

                if group_by == 'month':
                    group_key = date_from.strftime('%B %Y') if date_from else 'No Month'
                elif group_by == 'year':
                    group_key = date_from.strftime('%Y') if date_from else 'No Year'
                grouped_loans[group_key].append(loan)

        if request.httprequest.method == "POST":
            app_date = datetime.date.today()
            loans_obj.sudo().create({
                "employee_id": request.env.user.employee_id.id,
                "user_id": request.env.user.id,
                "state": "draft",
                "date_applied": app_date,
                "date_disb": app_date,
                "loan_type": int(kw.get("loan-type")),
                "principal_amount": int(kw.get("requested-amount")),
                "actual_principal_amount": 0,
                "installment_type": "month_wise",
            })

            return """
                <script>
                    window.history.back();
                </script>
            """

        vals = {
            'loans': loans,
            'grouped_loans': grouped_loans,
            'group_by': group_by,
            'loan_types': loan_types,
            'date_today': date_today,
            'page_name': 'loan_list_view',
            'pager': page_detail,
            'sortby': sortby,
            'searchbar_sortings': sorted_list,
            'search_in': search_in,
            'searchbar_inputs': search_list,
            'search': search
        }

        return request.render("ivis_user_portal.loan_list_view_portal", vals)

    @http.route(["/my/attendance/request/<model('hr.attendance'):attendance_id>"], type="http", auth="user",
                website=True)
    def _attendance_change_request(self, attendance_id, **kw):
        vals = {"this_attendance": attendance_id, "page_name": "change_request_popup"}
        return request.render("ivis_user_portal.change_request_popup_portal", vals)

    @staticmethod
    def _get_geoip_response(mode, latitude=False, longitude=False):
        return {
            'city': request.geoip.city.name or _('Unknown'),
            'country_name': request.geoip.country.name or request.geoip.continent.name or _('Unknown'),
            'latitude': latitude or request.geoip.location.latitude or False,
            'longitude': longitude or request.geoip.location.longitude or False,
            'ip_address': request.geoip.ip,
            'browser': request.httprequest.user_agent.browser,
            'mode': mode
        }

    @staticmethod
    def _get_employee_info_response(employee):
        response = {}
        if employee:
            response = {
                'id': employee.id,
                'employee_name': employee.name,
                'employee_avatar': employee.image_1920,
                'hours_today': float_round(employee.hours_today, precision_digits=2),
                'total_overtime': float_round(employee.total_overtime, precision_digits=2),
                'last_attendance_worked_hours': float_round(employee.last_attendance_worked_hours, precision_digits=2),
                'last_check_in': employee.last_check_in,
                'attendance_state': employee.attendance_state,
                'hours_previously_today': float_round(employee.hours_previously_today, precision_digits=2),
                'kiosk_delay': employee.company_id.attendance_kiosk_delay * 1000,
                'attendance': {
                    'check_in': employee.last_attendance_id.check_in,
                    'check_out': employee.last_attendance_id.check_out
                },
                'overtime_today': request.env['hr.attendance.overtime'].sudo().search([
                    ('employee_id', '=', employee.id),
                    ('date', '=', datetime.date.today()),
                    ('adjustment', '=', False),
                ]).duration or 0,
                'use_pin': employee.company_id.attendance_kiosk_use_pin,
                'display_systray': employee.company_id.attendance_from_systray,
                'display_overtime': employee.company_id.hr_attendance_display_overtime
            }
        return response

    @http.route('/my/attendance/systray_check_in_out', type="json", auth="user")
    def systray_attendance(self, latitude=False, longitude=False):
        employee = request.env.user.employee_id
        geo_ip_response = self._get_geoip_response(mode='systray', latitude=latitude, longitude=longitude)
        employee._attendance_action_change(geo_ip_response)
        return self._get_employee_info_response(employee)

    @http.route('/my/attendance/attendance_user_data', type="json", auth="user")
    def user_attendance_data(self):
        employee = request.env.user.employee_id
        return self._get_employee_info_response(employee)

    @http.route('/my/leaves/check_duration', type="json", auth="user")
    def duration_check(self, date_from, date_to, half_day, period):
        leaves = request.env['hr.leave'].sudo().search([('employee_id', '=', request.env.user.employee_id.id)])

        for record in leaves:
            fmt_from = record.date_from.strftime("%Y-%m-%d")
            if half_day and period:
                if (date_from == fmt_from and not record.request_unit_half):
                    return False
                if (date_from == fmt_from and record.request_unit_half):
                    if (period == record.request_date_from_period):
                        return False

            fmt_to = record.date_to.strftime("%Y-%m-%d")
            if (date_from <= fmt_to) and (date_to >= fmt_from):
                return False
        return True

    @http.route(['/my/profile'], type="http", website=True)
    def _profile_form_view(self, **kw):
        profile_obj = request.env['hr.employee']
        profile = profile_obj.sudo().search([('id', '=', request.env.user.employee_id.id)])
        parent_chain = []
        parent = profile.parent_id
        while parent:
            parent_chain.append(parent.id)
            parent = parent.parent_id
        parent_chain.reverse()

        vals = {'profile': profile, 'page_name': 'profile_form_view', 'parent_chain_ids': parent_chain}
        return request.render("ivis_user_portal.profile_sidebar_portal", vals)

    @http.route(["/my/profile/edit"], type="http", methods=["POST", "GET"], auth="user", website=True)
    def _edit_employee_profile(self, **kw):
        profile_list_obj = request.env['hr.employee']
        profile_list = profile_list_obj.sudo().search([('id', '=', request.env.user.employee_id.id)])

        vals = {'profile': profile_list, 'page_name': 'profile_edit_page'}

        if request.httprequest.method == "POST":
            update_vals = {}

            if kw.get("name"):
                update_vals["name"] = kw.get("name")
            if kw.get("email"):
                update_vals["private_email"] = kw.get("email")

            if update_vals:
                profile_list.write(update_vals)
                return request.redirect("/my/profile")

        return request.render('ivis_user_portal.profile_edit_portal', vals)

    @http.route(['/change_pin'], type='http', methods=["POST"], auth='user', website=True, csrf=False)
    def change_employee_pin(self, **kw):
        current_pin = kw.get('current_pin')
        new_pin = kw.get('new_pin')
        confirm_pin = kw.get('confirm_pin')

        if not all([current_pin, new_pin, confirm_pin]):
            raise UserError("Please provide all required PINs.")

        if new_pin != confirm_pin:
            raise UserError("New PIN and confirm PIN must be identical.")

        employee = request.env['hr.employee'].sudo().search([('user_id', '=', request.env.user.id)], limit=1)
        if not employee:
            raise UserError("No employee record found for the current user.")

        if employee.pin != current_pin:
            raise UserError("Incorrect current PIN.")

        employee.sudo().write({'pin': new_pin})

        return request.redirect('/web')

    @http.route(['/my'], type='http', methods=["POST"], auth='public', website=True, csrf=False)
    def _password_reset(self, **kw):
        current_password = kw.get('current_password')
        new_password = kw.get('new_password')
        confirm_password = kw.get('confirm_password')

        if not all([current_password, new_password, confirm_password]):
            raise UserError("Please provide all required passwords.")

        if new_password != confirm_password:
            raise UserError("New password and confirm password must be identical.")

        user = request.env.user
        if not user:
            raise UserError("No authenticated user found.")

        try:
            user._check_credentials(current_password, {'interactive': True})
        except AccessDenied:
            raise UserError("Incorrect current password.")

        request.session['identity-check-last'] = time.time()

        cpo_obj = request.env['change.password.own'].sudo().create({
            'new_password': new_password,
            'confirm_password': confirm_password
        })
        cpo_obj.change_password()

        return request.redirect('/web')

    @http.route(['/leave/cancel'], type='json', auth='public', website=True)
    def _leave_cancel(self, **kw):
        leave = int(kw.get('leave_id'))
        leave_id = request.env['hr.leave'].sudo().browse(leave)
        if leave_id.state == 'confirm':
            leave_id.action_refuse()
        return True

    @http.route(['/leave/approve'], type='json', auth='public', website=True)
    def _leave_approve(self, **kw):
        leave = int(kw.get('leave_id'))
        leave_id = request.env['hr.leave'].sudo().browse(leave)

        employee = request.env.user.employee_id
        if leave_id.state == 'confirm':
            # leave_id.sudo().write({'state': 'validate', 'second_approver_id': employee.id})
            leave_id.sudo().action_approve()
        return True

    @http.route(['/my/leaves/manage', '/my/leaves/manage/page/<int:page>'], type='http', auth='public', website=True)
    def _leaves_manage(self, page=1, sortby='start_date', search="", search_in="All", group_by=None, **kw):
        date_today = datetime.date.today()
        user = request.env.user
        date_format = request.env['res.lang'].search([('code', '=', user.lang)], limit=1).date_format
        user_timezone = timezone(request.env.user.tz)

        sorted_list = {
            'timeoff_type': {'label': 'Time Off', 'order': 'holiday_status_id'},
            'start_date': {'label': 'Date', 'order': 'date_from desc'},
            'duration': {'label': 'Duration', 'order': 'number_of_days desc'},
            'status': {'label': 'Status', 'order': 'state'},
        }

        default_order_by = sorted_list[sortby]['order']

        if search != "":
            domain = [
                ("employee_id.user_id", "!=", request.env.user.id),
                ('employee_id.name', 'ilike', search),
                ("can_approve", "!=", False)
            ]
        else:
            domain = [
                ("employee_id.user_id", "!=", request.env.user.id),
                ("can_approve", "!=", False),
                # ("state", "=", 'confirm'),
            ]

        search_list = {
            'check_in_search': {
                'label': 'Search...',
                'input': 'All',
                'domain': domain,
            },
        }

        leaves_obj = request.env['hr.leave']
        total_leaves = leaves_obj.sudo().search_count(domain)
        page_detail = pager(url='/my/leaves/manage', total=total_leaves, page=page,
                            url_args={'sortby': sortby, 'search_in': search_in, 'search': search}, step=80)

        filtered_leaves = leaves_obj.sudo().search(domain, limit=80, order=default_order_by,
                                                   offset=page_detail['offset'])

        grouped_leaves = defaultdict(list)

        if group_by:
            for leave in filtered_leaves:
                date_from = leave.date_from.astimezone(user_timezone) if leave.date_from else None

                if group_by == 'month':
                    group_key = date_from.strftime('%B %Y') if date_from else 'No Month'
                elif group_by == 'year':
                    group_key = date_from.strftime('%Y') if date_from else 'No Year'
                elif group_by == 'type':
                    group_key = leave.holiday_status_id.name
                elif group_by == 'subordinate':
                    group_key = leave.employee_id.name if leave.employee_id else 'No Sub-Ordinate'
                grouped_leaves[group_key].append(leave)

        leave_lines_map = {}

        for leave in filtered_leaves:
            lines = []
            if leave.employee_id and leave.request_date_from:
                fiscal_start = leave.employee_id.contract_id.get_fiscal_date_start(leave.request_date_from)
                fiscal_end = leave.employee_id.contract_id.get_fiscal_date_end(leave.request_date_from)

                leave_types = request.env['hr.leave.type'].search([])

                for leave_type in leave_types:
                    availed = request.env['hr.leave'].sudo().search([
                        ('employee_id', '=', leave.employee_id.id),
                        ('holiday_status_id', '=', leave_type.id),
                        ('state', '=', 'validate'),
                        ('request_date_from', '>=', fiscal_start),
                        ('request_date_to', '<=', fiscal_end),
                        ('id', '!=', leave.id),
                    ])
                    availed_leave = sum(availed.mapped('number_of_days')) or 0.0

                    if leave_type.requires_allocation == 'yes':
                        allocated = request.env['hr.leave.allocation'].sudo().search([
                            ('employee_id', '=', leave.employee_id.id),
                            ('holiday_status_id', '=', leave_type.id),
                            ('state', '=', 'validate'),
                            ('date_from', '<=', fiscal_end),
                            ('date_to', '>=', fiscal_start),
                        ])
                        available_leave = sum(allocated.mapped('number_of_days_display')) or 0.0
                        balance_leave = available_leave - availed_leave
                    else:
                        available_leave = 0.0
                        balance_leave = 0.0

                    lines.append({
                        'leave_type': leave_type.name,
                        'available_leave': available_leave,
                        'availed_leave': availed_leave,
                        'balance_leave': balance_leave,
                    })

            leave_lines_map[leave.id] = lines

        vals = {
            'leaves': filtered_leaves,
            'grouped_leaves': grouped_leaves,
            'leave_lines_map': leave_lines_map,
            'group_by': group_by,
            'date_today': date_today,
            'date_format': date_format,
            'sortby': sortby,
            'searchbar_sortings': sorted_list,
            'pager': page_detail,
            'search_in': search_in,
            'searchbar_inputs': search_list,
            'search': search,
        }

        return request.render("ivis_user_portal.leaves_manage_portal", vals)

    @http.route('/my/leaves/check_halfday', type="json", auth="user")
    def _check_halfday(self, holiday_status_id, **kw):
        if not holiday_status_id:
            return False
        holiday_status = request.env['hr.leave.type'].sudo().search([('id', '=', holiday_status_id)])
        if holiday_status.request_unit == 'hour':
            return True
        return False

    @http.route(["/my/appraisal", '/my/appraisal/page/<int:page>'], type="http", methods=["POST", "GET"], website=True)
    def _appraisal_list_view(self, page=1, sortby="create_date", search="", search_in="All", **kw):
        sorted_list = {
            'create_date': {'label': 'Created On', 'order': 'create_date'},
            'date_close': {'label': 'Appraisal Deadline', 'order': 'date_close desc'},
            'status': {'label': 'Status', 'order': 'state'}
        }

        user = request.env.user
        default_order_by = sorted_list[sortby]['order']

        appraisal_obj = request.env['appraisal.system']

        is_manager = bool(request.env['hr.employee'].sudo().search([('parent_id.user_id', '=', user.id)], limit=1))
        employee = request.env['hr.employee'].sudo().search([('user_id', '=', user.id)], limit=1)

        subordinate = kw.get('subordinate') == '1'

        if subordinate and employee:
            all_subordinates = self._get_all_subordinate_employees(employee)
            domain = [('employee_id', 'in', all_subordinates.ids), ('state', 'not in', ['draft', 'cancel'])]
        else:
            domain = [('employee_id', '=', employee.id), ('state', 'not in', ['draft', 'cancel'])]

        search_list = {
            'All': {
                'label': 'Search...',
                'input': 'All',
                'domain': domain,
            },
        }

        total_appraisals = appraisal_obj.sudo().search_count(domain)
        page_detail = pager(url='/my/appraisal', total=total_appraisals, page=page,
                            url_args={'sortby': sortby, 'search_in': search_in, 'search': search,
                                      'subordinate': '1' if subordinate else '0', }, step=35)
        appraisals = appraisal_obj.sudo().search(domain, limit=35, order=default_order_by, offset=page_detail['offset'])
        date_today = (datetime.date.today()).strftime("%Y/%m/%d")

        vals = {
            'appraisals': appraisals,
            'date_today': date_today,
            'is_manager': is_manager,
            'subordinate': subordinate,
            'pager': page_detail,
            'sortby': sortby,
            'searchbar_sortings': sorted_list,
            'search_in': search_in,
            'searchbar_inputs': search_list,
            'search': search,
            'page_name': 'view_appraisal_page'
        }

        return request.render("ivis_user_portal.appraisal_list_view_portal", vals)

    def _get_all_subordinate_employees(self, employee):
        Employee = request.env['hr.employee'].sudo()
        subordinates = Employee.browse()
        stack = Employee.browse([employee.id])
        while stack:
            current_employee = stack[-1]
            stack = stack[:-1]
            direct_subs = Employee.search([('parent_id', '=', current_employee.id)])
            subordinates += direct_subs
            stack += direct_subs
        return subordinates

    @http.route(["/my/appraisal/view/<int:appraisal_id>"], type="http", methods=["POST", "GET"], website=True)
    def _appraisal_view(self, appraisal_id, **kw):
        appraisal_obj = request.env["appraisal.system"]
        appraisal_data = appraisal_obj.sudo().search([("id", '=', appraisal_id)])
        user = request.env.user

        desigantions = request.env['hr.job'].sudo().search([])
        vals = {'appraisal': appraisal_data, 'page_name': 'view_appraisal_detail_page', 'user': user,
                'desigantions': desigantions}

        return request.render("ivis_user_portal.appraisal_detail_page_portal", vals)

    @http.route(['/my/appraisal/view/save'], type='http', auth="user", website=True, methods=['POST'])
    def portal_appraisal_save(self, **post):
        appraisal_id = int(post.get("appraisal_id"))
        appraisal_obj = request.env["appraisal.system"].sudo().browse(appraisal_id)
        if not appraisal_obj.exists():
            return request.redirect('/my/appraisal')

        vals = {}
        keys = [
            "remarks", "remarks_2", "remarks_3", "remarks_4", "remarks_5",
            "future_project", "total_points", "given_points", "leave_points",
            "availed_points", "bonus_amount", "date_effective"
        ]
        vals.update({
            key: post.get(key) for key in keys if post.get(key)
        })

        vals_lines = {
            "increment_raise_amount": post.get("increment_raise_amount") or 0,
            "recomm_desigantion_id": post.get("recomm_desigantion_id") or False,
            "recomm_grades": post.get("recomm_grades") or "",
        }

        if appraisal_obj.state == 'new':
            self._update_action_confirm(appraisal_obj, vals, vals_lines)
        elif appraisal_obj.state == 'pending':
            self._update_action_confirm2(appraisal_obj, vals, vals_lines)
        elif appraisal_obj.state == 'pending2':
            self._update_action_confirm3(appraisal_obj, vals, vals_lines)
        elif appraisal_obj.state == 'pending3':
            self._update_action_done(appraisal_obj, vals, vals_lines)
        elif appraisal_obj.state == 'pending4':
            self._update_action_confirm4(appraisal_obj, vals, vals_lines)

        return request.redirect('/my/appraisal/view/%s' % appraisal_id)

    def _update_action_confirm(self, appraisal_obj, vals, vals_lines):
        login_user = request.env.user.id
        manager_user = request.env['res.users'].search([('id', '=', 414)])
        manager = appraisal_obj.find_managers(appraisal_obj.employee_id)
        if len(appraisal_obj.manager_ids) <= 2:
            vals.update({'is_md_state': True})
        elif len(appraisal_obj.manager_ids) <= 3:
            vals.update({'is_exec_state': True})

        if appraisal_obj.employee_id.parent_id.user_id.id == login_user:
            vals.update({
                'doc_state': 'draft',
                'state': appraisal_obj.state,
                'appraisal_last_approver_id': login_user,
                'name_of_reporting_officer': login_user,
                'ro_submit_date': datetime.date.today(),
            })
            if login_user == 663 or login_user == 626:
                vals.update({
                    'last_state': appraisal_obj.state,
                    'state': 'pending4',
                    'is_manager': True,
                    'is_exec_state': True,
                    'appraisal_approver_id': manager_user.id
                })
            elif len(appraisal_obj.manager_ids) == 2 or (
            (not (manager.get('manager3')) and (not manager.get('manager4')) and (not manager.get('manager5')))):
                vals.update({
                    'last_state': appraisal_obj.state,
                    'state': 'pending3',
                    'is_md_state': True,
                    'appraisal_approver_id': appraisal_obj.employee_id.parent_id.parent_id.user_id.id
                })
            elif len(appraisal_obj.manager_ids) == 3:
                vals.update({
                    'last_state': appraisal_obj.state,
                    'state': 'pending4',
                    'is_exec_state': True,
                    'appraisal_approver_id': appraisal_obj.employee_id.parent_id.parent_id.parent_id.user_id.id
                })
            elif len(appraisal_obj.manager_ids) == 4:
                vals.update({
                    'last_state': appraisal_obj.state,
                    'state': 'pending2',
                    'is_manager2': True,
                    'is_manager3': True,
                    'appraisal_approver_id': appraisal_obj.employee_id.parent_id.parent_id.user_id.id
                })
            else:
                vals.update({
                    'last_state': appraisal_obj.state,
                    'state': 'pending',
                    'is_manager': True,
                    'is_manager2': True,
                    'appraisal_approver_id': appraisal_obj.employee_id.parent_id.parent_id.user_id.id
                })
            appraisal_obj.write(vals)

            if vals_lines['increment_raise_amount'] != 0:
                vals_lines.update({
                    'increment_raise_by': login_user,
                    'incremented_date': fields.Datetime.now(),
                    'state': appraisal_obj.state,
                    'increment_raise_id': appraisal_obj.id
                })
                request.env["increment.raise.lines"].create(vals_lines)
        else:
            raise ValidationError(_('Please let Mr. %s fill the form.') % appraisal_obj.employee_id.parent_id.user_id.name)

    def _update_action_confirm2(self, appraisal_obj, vals, vals_lines):
        login_user = request.env.user.id
        manager_user = request.env['res.users'].search([('id', '=', 414)])
        manager = appraisal_obj.find_managers(appraisal_obj.employee_id)
        if len(appraisal_obj.manager_ids) <= 3:
            vals.update({'is_md_state': True})
        elif len(appraisal_obj.manager_ids) <= 4:
            vals.update({'is_exec_state': True})

        if login_user == 663 or login_user == 626:
            vals.update({
                'last_state': appraisal_obj.state,
                'state': 'pending4',
                'is_manager': True,
                'is_exec_state': True,
                'appraisal_approver_id': manager_user.id
            })
            appraisal_obj.write(vals)
            if vals_lines['increment_raise_amount'] != 0:
                vals_lines.update({
                    'increment_raise_by': login_user,
                    'incremented_date': fields.Datetime.now(),
                    'state': appraisal_obj.state,
                    'increment_raise_id': appraisal_obj.id
                })
                request.env["increment.raise.lines"].create(vals_lines)

        elif appraisal_obj.employee_id.parent_id.parent_id.user_id.id == login_user:
            if not manager.get('manager4'):
                vals.update({
                    'last_state': appraisal_obj.state,
                    'state': 'pending3',
                    'is_md_state': True,
                    'appraisal_approver_id': appraisal_obj.employee_id.parent_id.parent_id.parent_id.user_id.id
                })
            else:
                vals.update({
                    'last_state': appraisal_obj.state,
                    'state': 'pending2',
                    'is_manager3': True,
                    'appraisal_approver_id': appraisal_obj.employee_id.parent_id.parent_id.parent_id.user_id.id
                })
            appraisal_obj.write(vals)

            if vals_lines['increment_raise_amount'] != 0:
                vals_lines.update({
                    'increment_raise_by': login_user,
                    'incremented_date': fields.Datetime.now(),
                    'state': appraisal_obj.state,
                    'increment_raise_id': appraisal_obj.id
                })
                request.env["increment.raise.lines"].create(vals_lines)
        else:
            raise ValidationError(
                _('Please let Mr. %s proceed the form.') % appraisal_obj.employee_id.parent_id.parent_id.user_id.name)

    def _update_action_confirm3(self, appraisal_obj, vals, vals_lines):
        login_user = request.env.user.id
        manager_user = request.env['res.users'].search([('id', '=', 414)])
        manager = appraisal_obj.find_managers(appraisal_obj.employee_id)

        if appraisal_obj.appraisal_approver_id.id == login_user:
            vals.update({
                'doc_state': 'draft',
                'last_state': appraisal_obj.state,
                'state': 'pending4',
                'is_manager3': True,
                'appraisal_last_approver_id': login_user,
            })
            if login_user == 663:
                vals.update({
                    'appraisal_approver_id': manager_user.id,
                })
            else:
                vals.update({
                    'appraisal_approver_id': appraisal_obj.appraisal_approver_id.employee_id.parent_id.user_id.id
                })
            appraisal_obj.write(vals)

            if vals_lines['increment_raise_amount'] != 0:
                vals_lines.update({
                    'increment_raise_by': login_user,
                    'incremented_date': fields.Datetime.now(),
                    'state': appraisal_obj.state,
                    'increment_raise_id': appraisal_obj.id
                })
                request.env["increment.raise.lines"].create(vals_lines)

        else:
            raise ValidationError(_('Please let Mr. %s proceed the form.') % appraisal_obj.appraisal_approver_id.name)

    def _update_action_done(self, appraisal_obj, vals, vals_lines):
        login_user = request.env.user.id

        if login_user != 408:
            raise ValidationError(_('Mr.Syed Feisal Ali will complete/done the Appraisal.'))
        else:
            vals.update({
                'doc_state': 'done',
                'last_state': appraisal_obj.state,
                'state': 'done',
                'appraisal_last_approver_id': login_user,
                'countersignedby_name': login_user,
                'countersignature_date': fields.Datetime.now(),
                'recomm_increment': appraisal_obj.recomm_increment_lines_id[-1].increment_raise_amount,
            })
            appraisal_obj.write(vals)

            if vals_lines['increment_raise_amount'] != 0:
                vals_lines.update({
                    'increment_raise_by': login_user,
                    'incremented_date': fields.Datetime.now(),
                    'state': appraisal_obj.state,
                    'increment_raise_id': appraisal_obj.id
                })
                request.env["increment.raise.lines"].create(vals_lines)

    def _update_action_confirm4(self, appraisal_obj, vals, vals_lines):
        login_user = request.env.user.id
        manager_user = request.env['res.users'].search([('id', '=', 414)])

        if login_user == 414:
            vals.update({
                'doc_state': 'draft',
                'last_state': appraisal_obj.state,
                'state': 'pending3',
                'appraisal_last_approver_id': login_user,
                'is_exec_state': True,
                'appraisal_approver_id': manager_user.id,
                'recomm_increment': appraisal_obj.recomm_increment_lines_id[-1].increment_raise_amount,
            })

            appraisal_obj.write(vals)

            if vals_lines['increment_raise_amount'] != 0:
                vals_lines.update({
                    'increment_raise_by': login_user,
                    'incremented_date': fields.Datetime.now(),
                    'state': appraisal_obj.state,
                    'increment_raise_id': appraisal_obj.id
                })
                request.env["increment.raise.lines"].create(vals_lines)
        else:
            raise ValidationError(_('Please let Mr. Ahad proceed the form.'))

    @http.route(['/my/leaves/apply'], type='http', auth="user", website=True, methods=['POST'])
    def leave_apply_submit(self, **post):
        login_user = request.env.user.id
        leave_type_id = int(post.get("timeoff"))
        leave_duration = float(post.get("duration") or 0.0)

        leave_type = request.env['hr.leave.type'].sudo().browse(leave_type_id)
        remaining_days = float_round(leave_type.virtual_remaining_leaves, precision_digits=2) or 0.0
        print('remaining_days', remaining_days)

        employee = request.env['hr.employee'].sudo().search([('user_id', '=', login_user)], limit=1)
        if not employee:
            request.session['leave_error'] = _("No employee record linked to your account. Please contact HR.")
            return request.redirect('/my/leaves')

        # Validation
        if leave_type.requires_allocation == "yes" and leave_duration > remaining_days:
            request.session['leave_error'] = _(
                "You cannot apply for %s days because you only have %s days remaining."
            ) % (leave_duration, remaining_days)
            return request.redirect('/my/leaves')

        vals = {
            'employee_id': employee.id,
            'holiday_status_id': leave_type_id,
            'name': post.get("desc") or '',
            'request_date_from': post.get("date_from"),
            'request_date_from_period': post.get("date_from_period"),
            'request_date_to': post.get("date_to"),
            'request_unit_half': True if post.get("half_day") else False,
            'duration_display': leave_duration,
            'state': 'confirm',
        }

        request.env['hr.leave'].sudo().create(vals)

        return request.redirect('/my/leaves')
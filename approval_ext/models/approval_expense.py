# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError
import logging
_logger = logging.getLogger(__name__)

class ApprovalExpenseConfig(models.Model):
    _name = 'approval.expense.config'
    _description = 'Global Travel Expense Configuration'

    name = fields.Char(string='Name', default='Global Expense Configuration', required=True)
    region_id = fields.Many2one('hr.work.location', string='Region')
    expense_payable_id = fields.Many2one('hr.employee', string='Expense Payable Employee', required=True)
    hr_id = fields.Many2one('hr.employee', string='HR Employee', required=True)


class ApprovalTravelExpense(models.Model):
    _name = 'approval.travel.expense'
    _description = 'Travel Expense Report'
    _rec_name = 'ref_no'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # state = fields.Selection([
    #     ('draft', 'Draft'),
    #     ('draft', 'Draft'),
    #     ('submitted', 'Pending HR'),
    #     ('hr_approved', 'Pending Payable Officer'),
    #     ('approved', 'Approved'),
    #     ('refused', 'Refused'),
    # ], string='Status', default='draft', required=True, tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Pending Manager'),
        ('manager_approved', 'Pending HR'),
        ('hr_approved', 'Pending Finance'),
        ('approved', 'Approved'),
        ('refused', 'Refused'),
    ], string='Status', default='draft', required=True, tracking=True)
    # --- 2. HR fields ke upar ye 3 naye fields add karein ---
    manager_approver_id = fields.Many2one('hr.employee', string='Reporting Manager', readonly=True, copy=False)
    manager_date = fields.Datetime(string='Manager Action Date', readonly=True, copy=False)
    manager_remarks = fields.Text(string='Manager Remarks', readonly=True, copy=False)

    hr_approver_id = fields.Many2one('hr.employee', string='HR Approver', readonly=True, copy=False)
    hr_date = fields.Datetime(string='HR Action Date', readonly=True, copy=False)
    hr_remarks = fields.Text(string='HR Remarks', readonly=True, copy=False)

    payable_approver_id = fields.Many2one('hr.employee', string='Payable Officer', readonly=True, copy=False)
    payable_date = fields.Datetime(string='Payable Action Date', readonly=True, copy=False)
    payable_remarks = fields.Text(string='Payable Remarks', readonly=True, copy=False)

    # ---------- approval helpers ----------
    def _get_config(self):
        self.ensure_one()
        Config = self.env['approval.expense.config'].sudo()
        region = self.employee_id.work_location_id
        cfg = Config.search([('region_id', '=', region.id)], limit=1) if region else Config
        return cfg or Config.search([], limit=1)

    def _current_employee(self):
        return self.env['hr.employee'].sudo().search([('user_id', '=', self.env.user.id)], limit=1)

    def _is_role(self, role):
        # """role: 'hr' or 'payable'"""
        # self.ensure_one()
        # cfg = self._get_config()
        # emp = self._current_employee()
        # target = cfg.hr_id if role == 'hr' else cfg.expense_payable_id
        # return bool(emp) and emp == target
        """role: 'manager', 'hr' or 'payable'"""
        self.ensure_one()
        emp = self._current_employee()
        if not emp:
            return False
        if role == 'manager':
            manager = self.employee_id.parent_id
            return bool(manager) and emp == manager
        cfg = self._get_config()
        target = cfg.hr_id if role == 'hr' else cfg.expense_payable_id
        return emp == target
    # ---------- actions ----------
        # --- 4. action_approve + action_refuse replace karein ---
    def action_approve(self, remarks=''):
        for rec in self:
            emp = rec._current_employee()
            now = fields.Datetime.now()
            if rec.state == 'submitted':
                if not rec._is_role('manager'):
                    raise UserError(_("Only the Reporting Manager can approve at this stage."))
                rec.write({'state': 'manager_approved', 'manager_approver_id': emp.id,
                           'manager_date': now, 'manager_remarks': remarks})
            elif rec.state == 'manager_approved':
                if not rec._is_role('hr'):
                    raise UserError(_("Only the HR approver can approve at this stage."))
                rec.write({'state': 'hr_approved', 'hr_approver_id': emp.id,
                           'hr_date': now, 'hr_remarks': remarks})
            elif rec.state == 'hr_approved':
                if not rec._is_role('payable'):
                    raise UserError(_("Only the Finance approver can approve at this stage."))
                rec.write({'state': 'approved', 'payable_approver_id': emp.id,
                           'payable_date': now, 'payable_remarks': remarks})
            else:
                raise UserError(_("This expense is not waiting for approval."))
            rec._send_expense_notification()

    # def action_refuse(self, remarks=''):
    #     for rec in self:
    #         if not (remarks or '').strip():
    #             raise UserError(_("Please enter remarks to refuse."))
    #         emp = rec._current_employee()
    #         if rec.state == 'submitted' and rec._is_role('hr'):
    #             rec.write({'state': 'refused', 'hr_approver_id': emp.id,
    #                        'hr_date': fields.Datetime.now(), 'hr_remarks': remarks})
    #         elif rec.state == 'hr_approved' and rec._is_role('payable'):
    #             rec.write({'state': 'refused', 'payable_approver_id': emp.id,
    #                        'payable_date': fields.Datetime.now(), 'payable_remarks': remarks})
    #         else:
    #             raise UserError(_("You are not allowed to refuse this expense at this stage."))

    def action_refuse(self, remarks=''):
        for rec in self:
            if not (remarks or '').strip():
                raise UserError(_("Please enter remarks to refuse."))
            emp = rec._current_employee()
            now = fields.Datetime.now()
            if rec.state == 'submitted' and rec._is_role('manager'):
                rec.write({'state': 'refused', 'manager_approver_id': emp.id,
                           'manager_date': now, 'manager_remarks': remarks})
            elif rec.state == 'manager_approved' and rec._is_role('hr'):
                rec.write({'state': 'refused', 'hr_approver_id': emp.id,
                           'hr_date': now, 'hr_remarks': remarks})
            elif rec.state == 'hr_approved' and rec._is_role('payable'):
                rec.write({'state': 'refused', 'payable_approver_id': emp.id,
                           'payable_date': now, 'payable_remarks': remarks})
            else:
                raise UserError(_("You are not allowed to refuse this expense at this stage."))
            rec._send_expense_notification()

        # ---------- paste this right after action_refuse (same indentation, inside ApprovalTravelExpense) ----------

    def _employee_email(self, emp):
        if not emp:
            return False
        return (emp.work_email
                or (emp.user_id.partner_id.email if emp.user_id else False)
                or emp.private_email)

    def _get_role_emails(self, role):
        """role: 'hr' or 'payable'"""
        self.ensure_one()
        cfg = self._get_config()
        emp = cfg.hr_id if role == 'hr' else cfg.expense_payable_id
        return [self._employee_email(emp)]

            # --- 5. _send_expense_notification replace karein (baqi mail methods waise hi) ---
    def _send_expense_notification(self):
        for rec in self:
            if rec.state == 'submitted':
                emails = [rec._employee_email(rec.employee_id.parent_id)]
                subject = "Travel Expense Awaiting Manager Approval"
                message = "A travel expense has been submitted and is waiting for your approval."
            elif rec.state == 'manager_approved':
                emails = rec._get_role_emails('hr')
                subject = "Travel Expense Awaiting HR Approval"
                message = "The Reporting Manager has approved this expense. It is now waiting for HR approval."
            elif rec.state == 'hr_approved':
                emails = rec._get_role_emails('payable')
                subject = "Travel Expense Awaiting Finance Approval"
                message = "HR has approved this expense. It is now waiting for Finance approval."
            elif rec.state == 'approved':
                emails = [rec._employee_email(rec.employee_id)]
                subject = "Travel Expense Approved"
                message = "Your travel expense has been fully approved."
            elif rec.state == 'refused':
                emails = [rec._employee_email(rec.employee_id)]
                subject = "Travel Expense Refused"
                message = "Your travel expense has been refused. Please check the remarks."
            else:
                continue
            try:
                rec._send_expense_mail(rec, emails, subject, message)
            except Exception:
                _logger.exception("Expense mail failed for %s", rec.id)
    def _send_expense_mail(self, expense, emails, subject, message):
        emails = [e for e in emails if e]
        if not emails:
            _logger.warning("No recipient emails for expense %s", expense.id)
            return
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        if not base_url or 'localhost' in base_url or '127.0.0.1' in base_url:
            base_url = 'http://odoo.aesl.com.pk:8018'
        url = f"{base_url}/my/travel/expense/view/{expense.id}"
        HRurl = f"{base_url}/odoo/action-959/{expense.id}"

        body = f"""
        <div style="font-family: Arial, sans-serif; font-size: 14px;">
            <h2 style="color: #8D0000;">{subject}</h2>
            <p>{message}</p>
            <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
                <tr><td style="padding: 5px; font-weight: bold; width: 30%;">Employee:</td><td style="padding: 5px;">{expense.employee_name}</td></tr>
                <tr><td style="padding: 5px; font-weight: bold;">Trip To:</td><td style="padding: 5px;">{expense.trip_to}</td></tr>
                <tr><td style="padding: 5px; font-weight: bold;">Total Expense:</td><td style="padding: 5px;">{expense.total_expense}</td></tr>
                <tr><td style="padding: 5px; font-weight: bold;">Balance Due:</td><td style="padding: 5px;">{expense.balance_due}</td></tr>
            </table>
            <p><a href="{url}" style="background-color: #8D0000; color: #fff; padding: 10px 18px; text-decoration: none; border-radius: 4px;">View Expense Report</a></p>
            <p><a href="{HRurl}" style="background-color: #8D0000; color: #fff; padding: 10px 18px; text-decoration: none; border-radius: 4px;">HR View Expense Report</a></p>
            <p>Best Regards,</p>
        </div>"""

        company = self.env.company
        email_from = (company.email_formatted
                      or self.env.user.email_formatted
                      or self.env['ir.config_parameter'].sudo().get_param('mail.default.from'))

        mail = self.env['mail.mail'].sudo().create({
            'subject': f"{subject}: {expense.ref_no}",
            'body_html': body,
            'email_to': ','.join(emails),
            'email_from': email_from,
            'auto_delete': True,
        })
        mail.send(raise_exception=False)

    # request_id = fields.Many2one('approval.request', string='Original Travel Request', required=True, ondelete='cascade')
    # ref_no = fields.Char(string='Ref No', related='request_id.name', store=True)

    # CHANGED: optional now
    request_id = fields.Many2one('approval.request', string='Original Travel Request',
                                 ondelete='set null', index=True)
    # CHANGED: no longer related to request_id.name
    ref_no = fields.Char(string='Ref No', readonly=True, copy=False, default='New', index=True)

    _sql_constraints = [
        ('request_unique', 'unique(request_id)',
         'A travel expense already exists for this travel request.'),
    ]

    # Employee Details Snapshot
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    employee_name = fields.Char(string='Employee Name')
    employee_reg_no = fields.Char(string='Employee No.')
    department_name = fields.Char(string='Department')
    designation_name = fields.Char(string='Designation')
    
    # Trip Details Snapshot
    trip_to = fields.Char(string='Trip To')
    purpose_of_trip = fields.Char(string='Purpose of Trip')
    period_from = fields.Datetime(string='Period From')
    period_to = fields.Datetime(string='Period To')
    
    # Manual Details
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    expense_line_ids = fields.One2many('approval.travel.expense.line', 'expense_id', string='Expense Lines')
    
    total_expense = fields.Float(string='Total Expense', compute='_compute_totals', store=True)
    advance_by_company = fields.Float(string='Less: Advance by Company')
    items_paid_direct = fields.Float(string='Items to be paid direct by the Company')
    balance_due = fields.Float(string='Balance Due to Company/Me', compute='_compute_totals', store=True)

    @api.depends('expense_line_ids.total_amount', 'advance_by_company', 'items_paid_direct')
    def _compute_totals(self):
        for rec in self:
            tot = sum(rec.expense_line_ids.mapped('total_amount'))
            rec.total_expense = tot
            rec.balance_due = tot - rec.advance_by_company - rec.items_paid_direct

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('ref_no') or vals.get('ref_no') == 'New':
                if vals.get('request_id'):
                    vals['ref_no'] = self.env['approval.request'].browse(vals['request_id']).name
                else:
                    vals['ref_no'] = self.env['ir.sequence'].next_by_code('approval.travel.expense') or 'New'
        return super().create(vals_list)


class ApprovalTravelExpenseLine(models.Model):
    _name = 'approval.travel.expense.line'
    _description = 'Travel Expense Line'

    expense_id = fields.Many2one('approval.travel.expense', string='Expense Report', ondelete='cascade')
    
    station_from = fields.Char(string='From')
    station_to = fields.Char(string='To')
    date_str = fields.Char(string='Date')
    time_str = fields.Char(string='Time')
    
    fare = fields.Float(string='Fare')
    fare_desc = fields.Char(string='Fare Description')
    fare_curr = fields.Char(string='Fare Currency')

    hotel_room = fields.Float(string='Hotel Room')
    hotel_desc = fields.Char(string='Hotel Description')
    hotel_curr = fields.Char(string='Hotel Currency')

    meals = fields.Float(string='Meals')
    meals_desc = fields.Char(string='Meals Description')
    meals_curr = fields.Char(string='Meals Currency')

    taxi = fields.Float(string='Taxi')
    taxi_desc = fields.Char(string='Taxi Description')
    taxi_curr = fields.Char(string='Taxi Currency')

    laundry = fields.Float(string='Laundry')
    laundry_desc = fields.Char(string='Laundry Description')
    laundry_curr = fields.Char(string='Laundry Currency')

    telephone = fields.Float(string='Telephone')
    telephone_desc = fields.Char(string='Telephone Description')
    telephone_curr = fields.Char(string='Telephone Currency')

    other_expense = fields.Float(string='Other Expense')
    other_desc = fields.Char(string='Other Description')
    other_curr = fields.Char(string='Other Currency')

    daily_allowance = fields.Float(string='Daily Allowance')
    daily_desc = fields.Char(string='Daily Description')
    daily_curr = fields.Char(string='Daily Currency')
    
    description = fields.Char(string='Description')
    currency = fields.Char(string='Currency')
    
    total_amount = fields.Float(string='Total', compute='_compute_total', store=True)

    @api.depends('fare', 'hotel_room', 'meals', 'taxi', 'laundry', 'telephone', 'other_expense', 'daily_allowance')
    def _compute_total(self):
        for line in self:
            line.total_amount = sum([
                line.fare, line.hotel_room, line.meals, line.taxi, 
                line.laundry, line.telephone, line.other_expense, line.daily_allowance
            ])

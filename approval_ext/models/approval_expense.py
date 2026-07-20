# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

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

    request_id = fields.Many2one('approval.request', string='Original Travel Request', required=True, ondelete='cascade')
    ref_no = fields.Char(string='Ref No', related='request_id.name', store=True)
    
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
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted')
    ], string='Status', default='draft', required=True)

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


class ApprovalTravelExpenseLine(models.Model):
    _name = 'approval.travel.expense.line'
    _description = 'Travel Expense Line'

    expense_id = fields.Many2one('approval.travel.expense', string='Expense Report', ondelete='cascade')
    
    station_from = fields.Char(string='From')
    station_to = fields.Char(string='To')
    date_str = fields.Char(string='Date')
    time_str = fields.Char(string='Time')
    
    fare = fields.Float(string='Fare')
    hotel_room = fields.Float(string='Hotel Room')
    meals = fields.Float(string='Meals')
    taxi = fields.Float(string='Taxi')
    laundry = fields.Float(string='Laundry')
    telephone = fields.Float(string='Telephone')
    other_expense = fields.Float(string='Other Expense')
    daily_allowance = fields.Float(string='Daily Allowance')
    
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

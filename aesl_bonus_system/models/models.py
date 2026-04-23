# -*- coding: utf-8 -*-

from odoo import models, fields, api


class employeeBonusSystem(models.Model):
    _inherit = 'employee.bonus'
    _description = 'Employee Bonus System'

    emp_name = fields.Char()
    grade = fields.Char()
    total_points = fields.Integer() #Total Points
    given_points = fields.Integer() #By MD
    leave_points = fields.Integer()
    proportional_points = fields.Float()
    availed_points = fields.Integer()
    department_id = fields.Many2one('hr.department', string="Department", readonly=True)
    region_id = fields.Many2one('hr.work.location', "Region", readonly=True)
    prev_gross_salary = fields.Float('Gross Salary')
    appraisal_id = fields.Many2one('appraisal.system','Appraisal Reference')


    def open_wizard(self):
        list = []
        for i in self:
            list.append(i)

    @api.constrains('given_points')
    def action_recalc_bonus(self):
        if self.given_points:
            availed_points = self.given_points + self.leave_points
            availed_ttl_points = availed_points / self.total_points
            bonus_amount = availed_ttl_points * 3 * self.prev_gross_salary * round(self.proportional_points,2)
            self.availed_points = availed_points
            self.bonus_amount = round(bonus_amount)


#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100

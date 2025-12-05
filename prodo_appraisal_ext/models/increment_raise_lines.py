from odoo import models, fields, api, _


class IncrementRaiseLines(models.Model):
    _name = 'increment.raise.lines'
    _description = 'Lines'

    increment_raise_id = fields.Many2one('hr.appraisal', string='Increment Raise Lines', required=True, index=True, ondelete='cascade')
    increment_raise_amount = fields.Float(string="Increment")
    recomm_desigantion_id = fields.Many2one('hr.job', string='Designation')
    recomm_grades = fields.Integer(string='Grade')
    increment_raise_by = fields.Many2one('res.users', string="Recommended By")

    incremented_date = fields.Date('Date')
    is_manager2 = fields.Boolean()
    is_manager3 = fields.Boolean()
    is_manager4 = fields.Boolean()
    is_manager5 = fields.Boolean()
    state = fields.Char()
    check_access_team_id = fields.Boolean('Check Access', compute='_compute_access_team_id')

    # employee_id = fields.Many2one(
    #     'hr.employee',
    #     string='Employee',
    #     required=True
    # )
    #
    manager_id = fields.Many2one(
        'hr.employee',
        string='Manager',
        store=True
    )

    # @api.depends('employee_id')
    # def _compute_manager_id(self):
    #     for rec in self:
    #         rec.manager_id = rec.employee_id.parent_id.id if rec.employee_id.parent_id else False

    @api.depends('create_uid')
    def _compute_access_team_id(self):
        list = []
        for rec in self:
             manager_uid = rec.filtered(lambda x: x.create_uid.id == self.env.user.id)
             if manager_uid:
                 rec.check_access_team_id = True
             else:
                 rec.check_access_team_id = False



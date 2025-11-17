from odoo import models, fields, api


class IncrementRaiseLines(models.Model):
    _name = 'increment.raise.lines'
    _description = 'Lines'

    increment_raise_id = fields.Many2one('appraisal.system', string='Increment Raise Lines', required=True, index=True,
                                         ondelete='cascade')
    increment_raise_amount = fields.Float(string="Increment")
    recomm_desigantion_id = fields.Many2one('hr.job', string='Designation')
    recomm_grades = fields.Integer(string='Grade')
    increment_raise_by = fields.Many2one('res.users', string="Recommended By")
    incremented_date = fields.Date('Date')
    state = fields.Char()
    check_access_team_id = fields.Boolean('Check Access', compute='_compute_access_team_id')

    @api.depends('increment_raise_by')
    def _compute_access_team_id(self):
        list = []
        for rec in self:
            list.append(rec.increment_raise_by.id)
            if rec.increment_raise_by.id not in list:
                rec.check_access_team_id = True
            elif not rec.increment_raise_by.id:
                rec.check_access_team_id = True
            else:
                rec.check_access_team_id = rec.increment_raise_by.id == self.env.uid == self.increment_raise_id.appraisal_approver_id.id

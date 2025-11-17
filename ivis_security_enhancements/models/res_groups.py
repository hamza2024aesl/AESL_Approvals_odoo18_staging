from odoo import models, fields


class ResGroupsInherit(models.Model):
    _inherit = "res.groups"

    menu_access_restrict = fields.Many2many('ir.ui.menu', 'ir_ui_menu_group_restrict_rel', 'gres_id', 'menu_id',
                                            string='Restrict Access Menu')

    def create(self, values):
        self.env['ir.ui.menu'].clear_caches()
        return super(ResGroupsInherit, self).create(values)

    def write(self, values):
        self.env['ir.ui.menu'].clear_caches()
        return super(ResGroupsInherit, self).write(values)

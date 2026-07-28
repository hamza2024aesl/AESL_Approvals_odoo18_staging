# -*- coding: utf-8 -*-
from odoo import api, models

class HrWorkEntry(models.Model):
    _inherit = "hr.work.entry"

    @api.model_create_multi
    def create(self, vals_list):
        return self.browse()

    def write(self, vals):
        return True
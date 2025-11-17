import json
import logging
from odoo import models

_logger = logging.getLogger(__name__)


class IrUiViewInherit(models.Model):
    _inherit = 'ir.ui.view'

    def _postprocess_access_rights(self, tree):
        base_model = tree.get('model_access_rights')
        xpath_nodes = tree.xpath('//*[@model_access_rights]')
        result = super(IrUiViewInherit, self)._postprocess_access_rights(tree)

        if self.env.user._is_superuser():
            return result

        if not base_model:
            return result

        Model = self.env['ir.model'].sudo().search([('model', '=', base_model)], limit=1)
        if not Model:
            return result

        fields_security = Model.field_security_ids

        for field_security in fields_security:
            if not (self.env.user.groups_id & field_security.group_ids):
                continue

            for node in xpath_nodes:
                for field_node in node.xpath(".//field[@name='%s']" % field_security.field_id.name):
                    if field_security.set_invisible:
                        field_node.set('invisible', '1')
                    if field_security.set_readonly:
                        field_node.set('readonly', '1')
                    if field_security.field_type == 'many2one' and field_security.rewrite_options:
                        options = {
                            'no_open': field_security.set_no_open,
                            'no_create': field_security.set_no_create,
                            'no_quick_create': field_security.set_no_quick_create,
                            'no_create_edit': field_security.set_no_create_edit,
                        }
                        existing_options = json.loads(field_node.get('options', '{}'))
                        existing_options.update(options)
                        field_node.set('options', json.dumps(existing_options))

                for button_node in node.xpath(".//button | .//a"):
                    if any(field.get('name') == field_security.field_id.name for field in
                           button_node.xpath(".//field")):
                        if field_security.hide_stat_button:
                            button_node.set('invisible', '1')

        return result

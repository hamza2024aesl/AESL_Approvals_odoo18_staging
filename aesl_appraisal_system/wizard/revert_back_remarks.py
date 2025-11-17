from odoo import models, fields, api

class AppraisalWizard(models.TransientModel):
    _name = 'appraisal.wizard'
    _description = 'Appraisal Remarks Wizard'

    remarks = fields.Text(string='Remarks')

    def action_confirm(self):
        # Get the active record and call the action_reset_back
        active_id = self.env.context.get('active_id')
        appraisal = self.env['appraisal.system'].browse(active_id)
        appraisal_remarks = self.remarks
        # appraisal.action_reset_back()

        if appraisal:
            # Remarks ko context mein set karte hain
            appraisal.with_context(appraisal_remarks=appraisal_remarks).action_reset_back()

            return {
                'type': 'ir.actions.act_window',
                'name': 'view.appraisal.system.tree',
                'res_model': 'appraisal.system',
                'view_mode': 'list,form',
                'domain': [],  # Optional: add any filters if needed
                'context': {
                    'group_by': ['state', 'appraisal_approver_id'],  # Grouping fields
                },
                'target': 'current',  # Replaces the current view
            }

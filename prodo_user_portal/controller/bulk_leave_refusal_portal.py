from odoo import http
from odoo.http import request
import logging
_logger = logging.getLogger(__name__)

class ProdoLeavePortal(http.Controller):

    @http.route('/leave/refuse/bulk', type='json', auth='user', website=True)
    def leave_refuse_bulk(self, leave_ids=None, refuse_reason="Refused by Manager", **kwargs):
        if not leave_ids:
            return {'success': False, 'error': 'No leaves selected.'}

        Leave = request.env['hr.leave'].sudo()
        leaves = Leave.browse(leave_ids).exists()

        # Optional: sirf wahi leaves refuse karein jo user manage kar sakta hai
        # leaves = leaves.filtered(lambda l: l.can_be_managed_by(request.env.user))

        refused = 0
        for leave in leaves:
            try:
                leave.write({'refuse_reason': refuse_reason})
                leave.action_refuse()
                # Refuse reason ko chatter me likhne ke liye (optional)
                if hasattr(leave, 'message_post'):
                    leave.message_post(body=refuse_reason)
                refused += 1
            except Exception as e:
                # Log rakhein, lekin baaki leaves process karte rahein
                _logger.exception("Bulk refuse failed for leave %s: %s", leave.id, e)

        return {'success': True, 'refused': refused}
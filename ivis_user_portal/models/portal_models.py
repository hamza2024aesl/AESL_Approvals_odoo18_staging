from odoo import models, fields, api


class HrEmployeeInherit(models.Model):
    _inherit = "hr.employee"

    def get_obj_from_id(self, id):
        print("\033[1;31m", id)
        return self.env["hr.employee"].browse(id)

class InvoiceInherit(models.Model):
    _inherit = "account.move"


class HrAttendanceInherit(models.Model):
    _inherit = "hr.attendance"

    def my_function(self, customStr):
        print("PYthonCalled")
        if customStr:
            print(customStr, self)
        pass

class HrLeaveAllocationInherit(models.Model):
    _inherit = "hr.leave.allocation"


class HrPayslipInherit(models.Model):
    _name = "hr.payslip"
    _inherit = ["hr.payslip", "portal.mixin"]

    def _compute_access_url(self):
        super()._compute_access_url()
        # for move in self.filtered(lambda move: move.is_invoice()):
        for move in self.env["hr.payslip"].search([]):
            move.access_url = '/my/payslips/%s' % (move.id)

    def _get_report_base_filename(self):
        return self.name

    def portal_action_print_payslip(self, payslip_id):
        print(payslip_id, payslip_id.ids)
        return {
            'name': 'Payslip',
            'type': 'ir.actions.act_url',
            'url': '/print/payslips?list_ids=%(list_ids)s' % {'list_ids': ','.join(str(x) for x in payslip_id.ids)},
        }

#
# class MyChangeRequestInherit(models.Model):
#     _inherit = ["my.change.request"]


class HrEmployeeLoanInherit(models.Model):
    _inherit = ["employee.loan.details"]
    
    
class LoanTypeInherit(models.Model):
    _inherit = ["loan.type"]


class InheritMailActivity(models.Model):
    _inherit = ["mail.activity"]


class InheritMailActivityType(models.Model):
    _inherit = ["mail.activity.type"]


class InheritCalendarEvent(models.Model):
    _inherit = ["calendar.event"]


class InheritCalendarAttendee(models.Model):
    _inherit = ["calendar.attendee"]

class ResCompanyInherit(models.Model):
    _inherit = ["res.company"]

    allow_portal_attendance = fields.Boolean(string="Allow Portal Attendance")
    allow_portal_leaves_management = fields.Boolean(string="Allow Portal Leaves Management")
    allow_change_request = fields.Boolean(string="Allow Change Request")
    allow_pin_change = fields.Boolean(string="Allow Portal Pin Change")

class ResConfigSettingInherit(models.TransientModel):
    _inherit = ["res.config.settings"]

    allow_portal_attendance = fields.Boolean(string="Allow Portal Attendance", related="company_id.allow_portal_attendance", readonly=False)
    allow_portal_leaves_management = fields.Boolean(string="Allow Portal Leaves Management", related="company_id.allow_portal_leaves_management", readonly=False)
    allow_change_request = fields.Boolean(string="Allow Change Request", related="company_id.allow_change_request", readonly=False)
    allow_pin_change = fields.Boolean(string="Allow Portal Pin Change", related="company_id.allow_pin_change", readonly=False)

class HrLeaveTypeInherit(models.Model):
    _inherit = ["hr.leave.type"]

class AppraisalSystemInherit(models.Model):
    _inherit = "appraisal.system"

class IncrementRaiseLinesInherit(models.Model):
    _inherit = "increment.raise.lines"
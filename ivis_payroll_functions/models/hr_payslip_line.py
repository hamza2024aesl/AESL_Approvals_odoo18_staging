from odoo import fields, models


class HrPayslipLineInherit(models.Model):
    _inherit = 'hr.payslip.line'

    date_from = fields.Date(related='slip_id.date_from', store=True)
    date_to = fields.Date(related='slip_id.date_to', store=True)
    payslip_run_id = fields.Char('Payslip Batches',
                                 related='slip_id.payslip_run_id.name',
                                 store=True)
    department_id = fields.Many2one('hr.department', related='employee_id.department_id', store=True)
    job_id = fields.Many2one('hr.job', related='employee_id.job_id', store=True)
    work_location = fields.Char(related='employee_id.work_location_name', store=True)
    employee_code = fields.Char(related='employee_id.identification_id', store=True)

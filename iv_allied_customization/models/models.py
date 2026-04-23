from datetime import datetime, timedelta
from odoo import models, fields, api


class MachineDataInherit(models.Model):
    _inherit = 'machine.data'

    date_convert = fields.Char()
    time_convert = fields.Char()
    type_convert = fields.Char()

    @api.model
    def create(self, vals_list):
        res = super(MachineDataInherit, self).create(vals_list)
        if res.type_convert == '01':
            res.type = 'in'
        elif res.type_convert == '02':
            res.type = 'out'

        hour = '0' + res.time_convert[:1] if len(res.time_convert) == 3 else res.time_convert[:2]
        min = res.time_convert[1:] if len(res.time_convert) == 3 else res.time_convert[2:]
        res.date = datetime.strptime(res.date_convert, "%Y%m%d").date()
        date_time_str = res.date_convert[:4] + '-' + res.date_convert[4:6] + '-' + res.date_convert[
                                                                                   6:] + ' ' + hour + ':' + min + ':00'
        res.time = datetime.strptime(date_time_str, '%Y-%m-%d %H:%M:%S') + timedelta(hours=-5)
        employees = self.env['hr.employee'].search([('registration_number', '=', res.employee_code)])
        if employees:
            res.update({'employee_name': employees.id})
        else:
            res.unlink()
        return res


class PayrollBatchInherit(models.Model):
    _inherit = 'hr.payslip.run'

    def unlink(self):
        if self.state != 'close':
            self.env.cr.execute("""UPDATE hr_payslip SET state='draft' WHERE id in %s""", (tuple(self.slip_ids.ids),))
            self.state = 'draft'
        return super(PayrollBatchInherit, self).unlink()

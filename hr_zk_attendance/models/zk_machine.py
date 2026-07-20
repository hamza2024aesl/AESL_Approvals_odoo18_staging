# -*- coding: utf-8 -*-
###################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#    Copyright (C) 2020-TODAY Cybrosys Technologies(<http://www.cybrosys.com>).
#    Author: cybrosys(<https://www.cybrosys.com>)
#
#    This program is free software: you can modify
#    it under the terms of the GNU Affero General Public License (AGPL) as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###################################################################################
import logging
# import datetime
from datetime import timedelta
from struct import unpack

import pytz
from dateutil.relativedelta import relativedelta

from odoo import _
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from .zkconst import *

_logger = logging.getLogger(__name__)
try:
    from zk import ZK, const
except ImportError:
    _logger.error("Please Install pyzk library.")

_logger = logging.getLogger(__name__)


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    device_id = fields.Char(string='Biometric Device ID')
    # status = fields.Selection([('Missed Check In', 'Missed Check In'), ('Missed Check Out', 'Missed Check Out'), ('OK', 'OK')], string='Status')
    check_in_date = fields.Date(compute="_compute_date_time")
    check_out_date = fields.Date(compute="_compute_date_time")
    check_in_time = fields.Char(compute="_compute_date_time")
    check_out_time = fields.Char(compute="_compute_date_time")

    @api.depends('check_in', 'check_out')
    def _compute_date_time(self):
        for rec in self:
            if rec.check_in:
                rec.check_in_date = rec.check_in.date()
                check_in_extended_hours = rec.check_in + relativedelta(hours=5)
                rec.check_in_time = str(check_in_extended_hours.time())
            else:
                rec.check_in_date = False
                rec.check_in_time = False
            if rec.check_out:
                rec.check_out_date = rec.check_out.date()
                check_out_extended_hours = rec.check_out + relativedelta(hours=5)
                rec.check_out_time = str(check_out_extended_hours.time())
            else:
                rec.check_out_date = False
                rec.check_out_time = False


class ZkMachine(models.Model):
    _name = 'zk.machine'
    _description = 'ZK Machine'

    name = fields.Char(string='Machine Name', required=True)
    device_ip = fields.Char(string='Device IP', required=True,
                            help='The IP address of the Device')
    port_no = fields.Integer(string='Port No', required=True)
    address_id = fields.Many2one('res.partner', string='Working Address')
    is_attendance_machine = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id.id)

    def action_test_connection(self):
        """Checking the connection status"""
        zk = ZK(self.device_ip, port=self.port_no, timeout=30,
                password=False, ommit_ping=False)
        try:
            if zk.connect():
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': 'Successfully Connected',
                        'type': 'success',
                        'sticky': False
                    }
                }
        except Exception as error:
            raise ValidationError(f'{error}')

    def device_connect(self, zk):
        try:
            conn = zk.connect()
            return conn
        except:
            return False

    def clear_attendance(self):
        for info in self:
            try:
                machine_ip = info.device_ip
                zk_port = info.port_no
                timeout = 30
                try:
                    zk = ZK(machine_ip, port=zk_port, timeout=timeout, password=0, force_udp=False, ommit_ping=False)
                except NameError:
                    raise UserError(_("Please install it with 'pip3 install pyzk'."))
                conn = self.device_connect(zk)
                if conn:
                    conn.enable_device()
                    clear_data = zk.get_attendance()
                    if clear_data:
                        # conn.clear_attendance()
                        self._cr.execute("""delete from zk_machine_attendance""")
                        conn.disconnect()
                        raise UserError(_('Attendance Records Deleted.'))
                    else:
                        raise UserError(_('Unable to clear Attendance log. Are you sure attendance log is not empty.'))
                else:
                    raise UserError(
                        _('Unable to connect to Attendance Device. Please use Test Connection button to verify.'))
            except:
                raise ValidationError(
                    'Unable to clear Attendance log. Are you sure attendance device is connected & record is not empty.')

    def getSizeUser(self, zk):
        """Checks a returned packet to see if it returned CMD_PREPARE_DATA,
        indicating that data packets are to be sent

        Returns the amount of bytes that are going to be sent"""
        command = unpack('HHHH', zk.data_recv[:8])[0]
        if command == CMD_PREPARE_DATA:
            size = unpack('I', zk.data_recv[8:12])[0]
            print("size", size)
            return size
        else:
            return False

    def zkgetuser(self, zk):
        """Start a connection with the time clock"""
        try:
            users = zk.get_users()
            print(users)
            return users
        except:
            return False

    @api.model
    def cron_download(self):
        machines = self.env['zk.machine'].search([])
        for machine in machines:
            machine.download_attendance()

    def download_attendance(self):
        _logger.info("++++++++++++Cron Executed++++++++++++++++++++++")
        allow_log = False
        check_param = self.env['ir.config_parameter'].search([('key', '=', 'attendance.log')], limit=1)
        check_param_filter_date = self.env['ir.config_parameter'].search([('key', '=', 'fetch.attendance.date')],
                                                                         limit=1)
        if check_param and str(check_param.value).lower() == 'true':
            allow_log = True
        date_check = False
        if check_param_filter_date:  # dateformat should be YYYY-MM-DD
            date_check = datetime.strptime(
                str(check_param_filter_date.value), "%Y-%m-%d")
        zk_attendance = self.env['zk.machine.attendance']
        att_obj = self.env['hr.attendance']
        for info in self:
            machine_ip = info.device_ip
            zk_port = info.port_no
            timeout = 15
            try:
                zk = ZK(machine_ip, port=zk_port, timeout=timeout, password=0, force_udp=False, ommit_ping=False)
            except NameError:
                raise UserError(_("Pyzk module not Found. Please install it with 'pip3 install pyzk'."))
            conn = self.device_connect(zk)
            if conn:
                # conn.disable_device() #Device Cannot be used during this time.
                attendance = conn.get_attendance()
                if attendance:
                    for each in attendance:
                        if isinstance(date_check, datetime) and each.timestamp >= date_check or not date_check:
                            atten_time = each.timestamp
                            atten_time = datetime.strptime(atten_time.strftime('%Y-%m-%d %H:%M:%S'),
                                                           '%Y-%m-%d %H:%M:%S')
                            # atten_date = atten_time.date()
                            local_tz = pytz.timezone(
                                self.env.user.partner_id.tz or 'GMT')
                            local_dt = local_tz.localize(atten_time, is_dst=None)
                            utc_dt = local_dt.astimezone(pytz.utc)
                            utc_dt = utc_dt.strftime("%Y-%m-%d %H:%M:%S")
                            atten_time = datetime.strptime(
                                utc_dt, "%Y-%m-%d %H:%M:%S")
                            atten_date = (atten_time + timedelta(hours=5)).date()
                            atten_time = fields.Datetime.to_string(atten_time)
                            get_user_id = self.env['hr.employee'].search(
                                [('device_id', '=', each.user_id), ('active', '=', True)], limit=1)
                            if get_user_id:
                                duplicate_atten_ids = zk_attendance.search(
                                    [('device_id', '=', each.user_id), ('punching_time', '=', atten_time)])
                                if duplicate_atten_ids:
                                    continue
                                else:
                                    zk_attendance.create({'employee_id': get_user_id.id,
                                                          'device_id': each.user_id,
                                                          'attendance_type': str(each.status),
                                                          'punch_type': str(each.punch),
                                                          'punching_time': atten_time,
                                                          'punching_date': atten_date,
                                                          'address_id': info.address_id.id,
                                                          'is_attendance_machine': info.is_attendance_machine,
                                                          'atten_mode': 'Device',
                                                          'machine_code': info.name})
                # zk.enableDevice()
                conn.disconnect
                return True
            else:
                raise UserError(_('Unable to get the attendance log, please try again later.'))
        else:
            raise UserError(_('Unable to connect, please check the parameters and network connections.'))

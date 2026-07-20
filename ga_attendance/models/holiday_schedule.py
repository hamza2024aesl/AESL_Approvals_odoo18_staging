from datetime import datetime
from odoo import fields, models, api


class HolidaysSchedule(models.Model):
    _name = 'holidays.schedule'

    name = fields.Char('Description')
    date = fields.Date('Date')
    passed = fields.Boolean('Passed?', readonly=True)
    recurring = fields.Boolean('Recurring?')

    def process(self):
        if self.recurring:
            date = datetime.strptime(self.date, '%Y-%m-%d')
            self.date = date.replace(year=date.year + 1)
        else:
            self.passed = True

    @api.model
    def isHoliday(self, date):
        '''It expects date of string type. Then it processes it and tell whether a holiday lies on this date or not.'''
        match = self.search([('date', '=', date)])
        if match:
            return match
        else:
            return False

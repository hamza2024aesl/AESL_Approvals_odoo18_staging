# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import date, datetime, time
from datetime import timedelta
from dateutil.relativedelta import relativedelta

class AppraisalBatches(models.Model):
    _name = 'appraisal.batches'
    _description = 'Appraisal System Batch'

    name = fields.Char(required=True)
    date_start = fields.Date(string='Date From', required=True, help="start date",
                             default=lambda self: fields.Date.to_string(date.today().replace(day=1)))
    date_end = fields.Date(string='Date To', required=True, help="End date",
                           default=lambda self: fields.Date.to_string(
                               (datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()))

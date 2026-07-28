# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import date, datetime, time
from datetime import timedelta
from dateutil.relativedelta import relativedelta

class AppraisalSystemRun(models.Model):
    _name = 'appraisal.system.run'
    _description = 'Appraisal System Batch'

    name = fields.Char(required=True)
    # appraisal_ids = fields.One2many('appraisal.system', 'appraisal_run_id', string='Appraisals', readonly=True,
    #                            states={'draft': [('readonly', False)]})
    # state = fields.Selection([
    #     ('draft', 'Draft'),
    #     ('close', 'Close'),
    # ], string='Status', index=True, readonly=True, copy=False, default='draft')
    date_start = fields.Date(string='Date From', required=True, help="start date",
                             default=lambda self: fields.Date.to_string(date.today().replace(day=1)))
    date_end = fields.Date(string='Date To', required=True, help="End date",
                           default=lambda self: fields.Date.to_string(
                               (datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()))

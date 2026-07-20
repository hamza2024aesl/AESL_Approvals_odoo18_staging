from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api


class FamilyRecord(models.Model):
    _name = 'family.record'
    _description = "Employee's Family"

    name = fields.Char("Name", required=True)
    date_of_birth = fields.Date("Date of Birth")
    member_id = fields.Many2one('hr.employee', "Employee")
    gender = fields.Selection([('male', 'Male'), ('female', 'Female')], "Gender")
    relation = fields.Selection(
        [('son', 'Son'), ('daughter', 'Daughter'), ('father', 'Father'), ('mother', 'Mother'), ('wife', 'Wife'),
         ('husband', 'Husband')], "Relation")
    age_till_today = fields.Char(compute='get_fam_age', string='Age (as of today)')
    telephone_fam = fields.Char("Phone")
    fam_cnic = fields.Char(string="CNIC No")
    cnic_issuance = fields.Date(string="CNIC Issu.Date")
    fam_cnic_expiry = fields.Date(string="CNIC Exp. Date")
    next_kin = fields.Boolean(string="Next of Kin")
    is_insured = fields.Boolean(string="Insured")
    is_emergency = fields.Boolean(string="Emergency")

    @api.depends('date_of_birth')
    def get_fam_age(self):
        for rec in self:
            if rec.date_of_birth:
                fmt = '%Y-%m-%d'
                current_date = datetime.today()
                date_of_birth = datetime.strptime(str(rec.date_of_birth), fmt)
                relative_delta = relativedelta(current_date, date_of_birth)

                days = str(relative_delta.days)
                months = str(relative_delta.months)
                years = str(relative_delta.years)

                if days == False or days == None:
                    days = 0
                if months == False or months == None:
                    months = 0
                if years == False or years == None:
                    years = 0
                rec.age_till_today = str(years) + " Years " + str(months) + " Months " + str(days) + " Days"
            else:
                rec.age_till_today = ''

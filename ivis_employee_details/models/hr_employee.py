import datetime
import re
from datetime import datetime

from dateutil.relativedelta import relativedelta

from odoo import api, models, fields, _
from odoo.exceptions import ValidationError


class HrEmployeeInherit(models.Model):
    _inherit = 'hr.employee'

    identification_id = fields.Char(string='Employee Code', groups="hr.group_hr_user", tracking=True)
    father_name = fields.Char(string="Father's Name")
    badge_id = fields.Char(string="Badge ID")
    old_cnic = fields.Char(string="Old NIC No")
    cnic_issuance = fields.Date(string="CNIC Issuance Date")
    cnic_expiry = fields.Date(string="CNIC Expiry Date")
    passport_expiry = fields.Date(string="Passport Expiry")
    ntn = fields.Char(string="NTN")
    x_studio_field_uRb4K = fields.Char(string="GP Reg. Number")
    x_studio_personal_file_number = fields.Char(string="Personal File Number")
    age_at_today = fields.Char(string='Age (as of today)', compute='get_age')
    domicile_city = fields.Many2one('res.city', string="Domicile City")
    caste = fields.Char(string="Cast")
    religion = fields.Selection([
        ('Islam', 'Islam'),
        ('Christainity', 'Christainity'),
        ('Hinduism', 'Hinduism'),
        ('None', 'None')
    ], string='Religion', default='')
    blood_group = fields.Selection([
        ('O-', 'O-'), ('O+', 'O+'),
        ('A-', 'A-'), ('A+', 'A+'),
        ('B-', 'B-'), ('B+', 'B+'),
        ('AB-', 'AB-'), ('AB+', 'AB+')
    ], string="Blood Group")
    is_handicap = fields.Boolean()
    disability_type = fields.Char(string="Disability Detail")
    Is_commit_crime = fields.Boolean(string="Crime ever convicted", default=False)
    is_dual_nationality = fields.Boolean(default=False)
    other_nationality = fields.Many2one('res.country')
    kid_allowance = fields.Boolean(string="Kid Allowance")
    colony_allowance = fields.Boolean(string="Colony Allowance")
    colony = fields.Char(string="Colony")
    att_allowance = fields.Boolean(string="Att Allowance")
    is_mess_allowed = fields.Boolean(string="Is Mess Allowed")
    club_member = fields.Boolean(string="Club Member")
    transport_type = fields.Selection([
        ('Bus', 'Bus'),
        ('Coach', 'Coach'),
        ('None', 'None')
    ], string='Transport Type', default='')
    account_id = fields.Many2one('account.analytic.account', string='Analytic Account', copy=True)
    appointment_date = fields.Date(string='Appointment Date')
    confirmation_date = fields.Date(string='Confirmation Date')
    resignation_date = fields.Date(string='Resignation Date')
    exit_date = fields.Date(string='Exit Date')
    leave_reason = fields.Text(string="Leaving Reason")
    leave_type = fields.Selection([
        ('resign', 'Resign'),
        ('terminate', 'Terminate')
    ])
    is_resign = fields.Boolean(string='IS_Resign')
    is_final_settlement = fields.Boolean(string="Is Final Settlement")
    notice_period = fields.Boolean(string="Notice Period")
    is_faculty = fields.Boolean()
    family_code = fields.Char(string="Family Code")
    division = fields.Char(string="Division")
    x_studio_grade = fields.Char(
        string="Grade",
        related='contract_id.x_studio_grade',
        store=True,
        readonly=True,
    )
    company_percent = fields.Float(string='Company Percent')
    salary_deduct_per_month = fields.Float(string='Salary Deduction per month')
    salary_deduct_per_year = fields.Float(string='Salary Deduction per year')
    fam_member_ids = fields.One2many('family.record', 'member_id', string='Family Members')
    certification_ids = fields.One2many('certification.record', 'certificate_id', string='Certifications',
                                        help="Certifications")
    letter_ids = fields.One2many('letter.letter', 'letter_id', string='Letters', help="Letters")
    insurance_ids = fields.One2many('insurance.record', 'insurance_id', string='Insurance')
    payslip_eobi = fields.One2many('employee.eobi', 'employee_id')

    def _compute_display_name(self):
        for record in self:
            if record.identification_id:
                record.display_name = f"{record.name} ({record.identification_id})"
            else:
                record.display_name = record.name

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100) -> list[tuple[int, str]]:
        args = args or []

        if name:
            domain = [
                         '|',
                         ('identification_id', operator, name),
                         ('name', operator, name)
                     ] + args

            records = self.search(domain, limit=limit)
            records.fetch(['display_name'])

            return [(record.id, record.display_name) for record in records]

        return super().name_search(name, args, operator, limit)

    def process_retirement(self):
        scheduler_line_ids = self.search([])
        for scheduler in scheduler_line_ids:
            if scheduler.birthday:
                dt = scheduler.birthday
                d_str = str(dt)
                d1 = datetime.strptime(d_str, "%Y-%m-%d").date()
                d2 = datetime.today()
                rd = relativedelta(d2, d1)
                age = str(rd.years)
                int_age = int(age)
                if int_age == 60:
                    temp = self.env.ref('ivis_employee_details.retire_alert')
                    rec = self.env['mail.template'].browse(temp.id)
                    rec.send_mail(scheduler.id, force_send=True)

    def compute_funds(self):
        employee_contract = self.env['hr.contract'].search([('employee_id', '=', self.id), ('state', '=', 'open')])
        for contract in employee_contract:
            employee_payslip = self.env['hr.payslip'].search(
                [('contract_id', '=', contract.id), ('state', '=', 'done')], order='date_from asc')
            self.payslip_eobi.unlink()
            payMonth = ''
            total = 0
            pay_rule_name = ''
            rule_name = ''
            code = ''
            for payslip in employee_payslip.line_ids.filtered(lambda l: (l.code == 'EOBI')):
                payMonth = datetime.strptime(str(payslip.date_from), '%Y-%m-%d').strftime('%B')
                total += payslip.total
                pay_rule_name = payslip.salary_rule_id.name
                rule_name = payslip.name
                code = payslip.code
            if payMonth:
                self.payslip_eobi.create(
                    {'employee_id': self.id, 'rules': pay_rule_name, 'ruleName': rule_name, 'code': code,
                     'total': total, 'month': payMonth})

    def getEmpStatus(self, type):
        contract = self.env['hr.contract'].search([('employee_id', '=', self.id), ('state', '=', 'open')], limit=1)
        if type == 'type':
            return contract.emp_type
        if type == 'wage':
            return contract.wage

    def getRelativeName(self, relation):
        for line in self.fam_member_ids.filtered(lambda x: x.relation == relation):
            return line.name

    def getSuposeDOB(self):
        for line in self.fam_member_ids.filtered(lambda x: x.relation == 'wife'):
            return line.date_of_birth

    def getDepdentDetail(self):
        lst = []
        for line in self.fam_member_ids.filtered(lambda x: x.relation not in ('mother', 'father')):
            lst.append({'name': line.name, 'date_of_birth': line.date_of_birth})
        return lst

    def dates_line(self):
        for rec in self:
            contract_start = self.env['hr.contract'].search([('employee_id', '=', rec.id)], order='date_start', limit=1)
            if contract_start:
                rec.appointment_date = contract_start.date_start

            contract_trial = self.env['hr.contract'].search([('employee_id', '=', rec.id)], order='trial_date_end', limit=1)
            if contract_trial:
                rec.confirmation_date = contract_trial.trial_date_end

    @api.onchange('fam_member_ids')
    def unique_relations(self):
        for rec in self:
            relation_list = []
            for line in rec.fam_member_ids:
                if line.relation == 'father' or line.relation == 'mother' or line.relation == 'husband':
                    if line.relation not in relation_list:
                        relation_list.append(line.relation)
                    elif line.relation in relation_list:
                        raise ValidationError(_("Warning! You cannot select this relation more than one."))

    @api.constrains('ssn_id')
    def cnic_constrains(self):
        cnic = []
        employees = self.env['hr.employee'].search([('id', '!=', self.id)])
        for x in employees:
            if x.ssn_id:
                cnic.append(x.ssn_id)
        for n in cnic:
            if n == self.ssn_id:
                raise ValidationError("This CNIC is already in used by some other employee!")

    @api.onchange('ssn_id')
    def validate_cnic(self):
        if self.ssn_id:
            if self.validate_nic(self.ssn_id):
                raise ValidationError(_("Invalid CNIC Format"))

    def validate_nic(self, nic):
        if not (re.match('^[0-9+]{5}-[0-9+]{7}-[0-9]{1}$', nic)):
            return True
        return False

    # _sql_constraints = [
    #     ('name_uniq', 'unique(identification_id)', 'This CNIC is already in used by some other employee!'),
    # ]

    _sql_constraints = [
        ('name_uniq', 'unique(barcode)', 'This Badge Id is already in used by some other employee!'),
    ]

    _sql_constraints = [
        ('name_uniq', 'unique(old_cnic)', 'This Old CNIC is already in used by some other employee!'),
    ]

    _sql_constraints = [
        ('name_uniq', 'unique(family_code)', 'This Family is already in used by some other employee!'),
    ]

    @api.depends('birthday')
    def get_age(self):
        if self.birthday:
            fmt = '%Y-%m-%d'
            current_date = datetime.today()
            birthday = datetime.strptime(str(self.birthday), fmt)
            relative_delta = relativedelta(current_date, birthday)

            days = str(relative_delta.days)
            months = str(relative_delta.months)
            years = str(relative_delta.years)

            if days == False or days == None:
                days = 0
            if months == False or months == None:
                months = 0
            if years == False or years == None:
                years = 0
            self.age_at_today = str(years) + " Years " + str(months) + " Months " + str(days) + " Days"
        else:
            self.age_at_today = False

    @api.constrains('birthday')
    def _check_birthdate(self):
        for record in self:
            if record.birthday:
                if record.birthday > fields.Date.today():
                    raise ValidationError(_(
                        "Birth Date can't be greater than current date!"))

    maximum_rate = fields.Integer(default=100)

    # @api.constrains('identification_id')
    # def cnic_constrains(self):
    #     cnic = []
    #     employees = self.env['hr.employee'].search([('id','!=',self.id)])
    #     for x in employees:
    #         if x.identification_id:
    #             cnic.append(x.identification_id)
    #     for n in cnic:
    #         if n == self.identification_id:
    #             raise ValidationError("Already Defined")

    # def write(self, vals):
    #     res = super(inherit_employee, self).write(vals)
    #     employees = self.env['hr.employee'].search([('id', '=', self.id)])
    #     for emp in employees:
    #         temp_id = self.env.ref('ivis_employee_details.email_alert_mail').id
    #         temp = self.env['mail.template'].browse(temp_id)
    #         temp.send_mail(emp.id, force_send=True)
    #     return res

    # def get_dates(self):
    # employee_rec = self.env['hr.contract'].search([('employee_id', '=', self.id)], order='date_start asc', limit=1)
    # if not employee_rec:
    #     return False
    # #self.appointment_date = employee_rec.date_start
    # self.confirmation_date = employee_rec.trial_date_end
    # employee_record = self.env['hr.contract'].search([('employee_id', '=', self.id)], order='date_end desc', limit=1)
    # if not employee_record:
    #     return False
    # self.exit_date = employee_record.date_end

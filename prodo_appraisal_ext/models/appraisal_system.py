from odoo import models, fields, api, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError
from dateutil import relativedelta

from datetime import date
from datetime import datetime



class AppraisalSystem(models.Model):
    _name = 'appraisal.system'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Appraisal System Custom'

    name = fields.Char(default=_('New'))

    def _get_default_employee(self):
        # if not self.env.user.has_group('aesl_appraisal_system.group_user_appraisals'):
        return self.env.user.employee_id

    appraisal_type = fields.Selection([
        ('employee', 'By Employee'),
        ('company', 'By Company'),
        ('department', 'By Department')],
        string='Appraisal Mode', readonly=False, required=True, default='employee')
    mode_company_id = fields.Many2one(
        'res.company', compute='_compute_from_holiday_type', store=True, string='Company Mode', readonly=False)
    department_id = fields.Many2one(
        'hr.department', string='Department')
    company_id = fields.Many2one('res.company', store=True)
    # company_id = fields.Many2one('res.company', store=True,related='employee_id.company_id')
    employee_id = fields.Many2one(
        'hr.employee', required=True, string='Name', index=True,
        default=_get_default_employee)
    image_128 = fields.Image()
    image_1920 = fields.Image()
    departments = fields.Many2one('hr.department', string='Department')
    manager_ids = fields.Many2many(
        'hr.employee',
        'hr_appraisal_manager_rel',
        'hr_appraisal_id',
        'manager_id',
        string='Managers',
        store = True
    )
    registration_number = fields.Char(string="Emp. No.")
    birthday = fields.Date(string="Birth Date")
    grade = fields.Char('Grade')
    appointment_date = fields.Date('Appointment Date')
    gross_salary = fields.Float('Gross Salary')
    personal_file_number = fields.Char('Personal File Number')
    location = fields.Char('Location')
    education = fields.Char('Qualification')
    cl_count = fields.Float('Casual leave availed')
    sl_count = fields.Float('Sick leave availed')
    earned_leaves_balance = fields.Float('Earned leave Balance')
    emp_type = fields.Char()
    #job_id = fields.Many2one('hr.job', string='Designation')
    job_id = fields.Many2one('hr.job', string='Designation', related='employee_id.job_id')
    state = fields.Selection(
        [('draft', 'Draft'),
         ('new', 'Line Manager'),
         ('pending', 'Manager'),
         ('pending2', 'Director'),
         ('pending4', 'Executive'),
         ('pending3', 'MD'),
         ('done', 'HR'),
         ('cancel', "Cancelled")],
        string='Status', tracking=True, required=True, copy=False,
        default='draft', index=True, group_expand='_group_expand_states')
    date_close = fields.Date(
        string='Appraisal Deadline', required=True,
        default=lambda self: datetime.date.today().replace(day=1) + relativedelta(months=+1, days=-1))

    courtesy_tact = fields.Selection([
        ('outstanding', 'Outstanding'),
        ('above_average', 'Above Average'),
        ('average', 'Average'),
        ('below_average', 'Below Average')],
        string="Courtesy, Tact, Poise, Control and Temperament:   "
    )
    understanding_ability = fields.Selection([
        ('outstanding', 'Outstanding'),
        ('above_average', 'Above Average'),
        ('average', 'Average'),
        ('below_average', 'Below Average')],
        string="Ability to understand ideas, facts, and principles:   "
    )

    self_starting_energy = fields.Selection([
        ('outstanding', 'Outstanding'),
        ('above_average', 'Above Average'),
        ('average', 'Average'),
        ('below_average', 'Below Average')],
        string="Self starting energy and ability to plan:   "
    )

    assignment_performance = fields.Selection([
        ('outstanding', 'Outstanding'),
        ('above_average', 'Above Average'),
        ('average', 'Average'),
        ('below_average', 'Below Average')],
        string="Ability to perform assignments immediately:   "
    )

    job_knowledge = fields.Selection([
        ('outstanding', 'Outstanding'),
        ('above_average', 'Above Average'),
        ('average', 'Average'),
        ('below_average', 'Below Average')],
        string="Knowledge of all phases of job/trade:   "
    )

    job_done = fields.Selection([
        ('outstanding', 'Outstanding'),
        ('above_average', 'Above Average'),
        ('average', 'Average'),
        ('below_average', 'Below Average')],
        string="Does he get the job done:   "
    )

    remarks = fields.Text('Remarks:', size=10)
    remarks_2 = fields.Text('Remarks', size=10)
    remarks_3 = fields.Text('Remarks', size=50)
    remarks_4 = fields.Text('Remarks', size=50)
    remarks_5 = fields.Text('Remarks', size=50)
    future_project = fields.Text('Future Prospect')
    accomplishment = fields.Text('Accomplishment')
    to_confirmation = fields.Selection([
        ('yes', 'YES'),
        ('no', 'NO')],
        string="To be Confirmed?", default="yes")

    recomm_increment = fields.Float('Increase Recommended?', tracking=True)
    recomm_increment_lines_id = fields.One2many('increment.raise.lines', 'increment_raise_id',
                                                string='Increase Recommended Lines',
                                                required=True, index=True, ondelete='cascade')
    recomm_job_id = fields.Many2one('hr.job', string='Designation Recommended?')
    recomm_grade = fields.Integer(string='Grade Recommended?')
    # signature_of_reporting_officer = fields.Binary("Signature of Reporting Officer", store=True)
    name_of_reporting_officer = fields.Many2one('res.users', string='Reporting Officer')
    ro_submit_date = fields.Date("RO Submit Date")
    # countersignedBy = fields.Binary("Countersigned By", store=True)
    countersignedby_name = fields.Many2one('res.users', string='Countersigned By')
    countersignature_date = fields.Date("Countersignature Date")
    is_md_state = fields.Boolean(default=False)
    is_manager = fields.Boolean(default=False)
    is_manager2 = fields.Boolean(default=False)
    is_manager3 = fields.Boolean(default=False)
    is_hr_confirm = fields.Boolean(default=False)
    is_exec_state = fields.Boolean(default=False)
    appraisal_approver_id = fields.Many2one('res.users', string='Approver Name')
    appraisal_last_approver_id = fields.Many2one('res.users', string='Last Approver Name')
    last_state = fields.Char()
    doc_state = fields.Selection([
        ('draft', 'Draft'),
        ('save', 'Save'),
        ('done','Done'),('revert','Revert'),('publish','Publish')],default='draft'
    )
    recommend_raise_amount = fields.Float(string="Recom. Increment")
    recommend_designation_id = fields.Many2one('hr.job', string='Designation')
    recommend_grades = fields.Integer(string='Recom. Grade', group_operator=False)
    increase_percentage = fields.Float(string='Increment (%)', group_operator=False)
    x_css = fields.Html(sanitize=False,compute='_compute_css',store=False)

    appraisal_run_ids = fields.Many2one('appraisal.system.run', string='Appraisal Batch',required=True, ondelete='cascade')

    # Fields for Bonus
    total_points = fields.Integer() #Total Points
    given_points = fields.Integer() #By MD
    leave_points = fields.Integer()
    proportional_points = fields.Float()
    availed_points = fields.Integer()
    bonus_amount = fields.Integer()
    date_effective = fields.Date()

    def _compute_css(self):
        for rec in self:
        # To Remove Edit Option
            if rec.state == 'done':
                rec.x_css = '<style>.o_form_button_edit {display: none !important;}</style>'
            else:
                rec.x_css = False


    def _group_expand_states(self, states, domain, order):
        return [key for key, val in self._fields['state'].selection]

    @api.depends('appraisal_type')
    def _compute_from_appraisal_type(self):
        for appraisal in self:
            if appraisal.appraisal_type == 'employee':
                if not appraisal.employee_id:
                    appraisal.employee_id = self.env.user.employee_id
                appraisal.mode_company_id = False
            if appraisal.appraisal_type == 'company':
                appraisal.employee_id = False
                if not appraisal.mode_company_id:
                    appraisal.mode_company_id = self.env.company
            elif appraisal.appraisal_type == 'department':
                appraisal.employee_id = False
                appraisal.mode_company_id = False
            elif not appraisal.employee_id and not appraisal._origin.employee_id:
                appraisal.employee_id = self.env.context.get('default_employee_id') or self.env.user.employee_id

    def _leaves_count(self, employee):
        first = date(2020, 1, 1)
        last = date(2050, 12, 31)
        for emp in employee:
            sl_type_id = self.env['hr.leave.type'].search(
                [('company_id', '=', emp.company_id.id), ('code', '=', 'SL')]).id
            cl_type_id = self.env['hr.leave.type'].search(
                [('company_id', '=', emp.company_id.id), ('code', '=', 'CL')]).id
            pl_type_id = self.env['hr.leave.type'].search(
                [('company_id', '=', emp.company_id.id), ('code', '=', 'PL')]).id

            employee_leaves = self.env['hr.leave'].search([
                ('employee_id', '=', emp.id), ('date_from', '>=', first), ('date_to', '<=', last),
                ('state', '=', 'validate')
            ])
            employee_allocations = self.env['hr.leave.allocation'].search([
                ('employee_id', '=', emp.id), ('write_date', '>=', first), ('write_date', '<=', last),
                ('state', '=', 'validate')
            ])
            sick_leaves_count = sum(
                employee_leaves.filtered(lambda x: x.holiday_status_id.id == sl_type_id).mapped('number_of_days'))
            casual_leaves_count = sum(
                employee_leaves.filtered(lambda x: x.holiday_status_id.id == cl_type_id).mapped('number_of_days'))
            annual_leaves_count = sum(
                employee_leaves.filtered(lambda x: x.holiday_status_id.id == pl_type_id).mapped('number_of_days'))
            annual_allocation_count = sum(
                employee_allocations.filtered(lambda x: x.holiday_status_id.id == pl_type_id).mapped('number_of_days'))
            return {
                'sick_leaves_count': sick_leaves_count,
                'casual_leaves_count': casual_leaves_count,
                'earned_leaves_balance': annual_allocation_count - annual_leaves_count
            }

    @api.onchange('remarks','remarks_2','remarks_3','remarks_4','remarks_5',)
    def _onchange_departments(self):
        if self.remarks:
            if len(self.remarks) >= 30:
                raise ValidationError(_("Please enter the remarks limited"))
        if self.remarks_2:
            if len(self.remarks) >= 20:
                raise ValidationError(_("Please enter the remarks limited"))
        if self.remarks_3:
            if len(self.remarks) >= 20:
                raise ValidationError(_("Please enter the remarks limited"))
        if self.remarks_4:
            if len(self.remarks_4) >= 20:
                raise ValidationError(_("Please enter the remarks limited"))
        if self.remarks_5:
            if len(self.remarks_5) >= 20:
                raise ValidationError(_("Please enter the remarks limited"))



    @api.onchange('departments')
    def _onchange_departments(self):
        for appr_dept in self:
            if appr_dept.appraisal_type == 'department':
                leaves_data = appr_dept._leaves_count(appr_dept.employee_id)
                manager_hierarchy = appr_dept._get_all_parents(appr_dept.departments.member_ids[0])
                appr_dept.manager_ids = [(6, 0, manager_hierarchy)]
                appr_dept.employee_id = appr_dept.departments.member_ids[0].id
                appr_dept.company_id = appr_dept.departments.company_id.id
                appr_dept.education = appr_dept.employee_id.academic_ids.degree_id.name
                appr_dept.department_id = appr_dept.departments
                appr_dept.mode_company_id = appr_dept.departments.company_id.id
                # appr_dept.job_id = appr_dept.employee_id.job_id.id
                appr_dept.departments = appr_dept.departments
                appr_dept.registration_number = appr_dept.employee_id.registration_number
                appr_dept.grade = appr_dept.employee_id.x_studio_grade
                appr_dept.appointment_date = appr_dept.employee_id.appointment_date
                appr_dept.birthday = appr_dept.employee_id.birthday
                appr_dept.gross_salary = appr_dept.employee_id.contract_id.wage
                appr_dept.personal_file_number = appr_dept.employee_id.x_studio_personal_file_number
                appr_dept.location = appr_dept.employee_id.location_id.emp_location
                # appr_dept.name_of_reporting_officer = appr_dept.employee_id.parent_id.user_id
                appr_dept.emp_type = appr_dept.employee_id.contract_id.emp_type
                appr_dept.cl_count = leaves_data.get("casual_leaves_count") if leaves_data else 0.0
                appr_dept.sl_count = leaves_data.get("sick_leaves_count") if leaves_data else 0.0
                appr_dept.earned_leaves_balance = leaves_data.get("earned_leaves_balance") if leaves_data else 0.0

    def _get_all_parents(self, employee):
        """Recursively fetch all parent managers from bottom to top."""
        managers = []
        current_employee = employee

        # Traverse up the hierarchy until we reach the top-level manager (no parent)
        while current_employee.parent_id:
            managers.append(current_employee.parent_id.id)  # Add the parent's ID to the list
            current_employee = current_employee.parent_id  # Move to the next parent (up the hierarchy)

        return managers

    def create_appraisal_requests(self):
        """Creates appraisal requests based on selected mode."""
        Appraisal = self.env['appraisal.system'].sudo()  # Use sudo to avoid recursive create calls
        if self.appraisal_type == 'employee' and self.employee_id:
            # Get the list of all parent managers for the selected employee
            manager_hierarchy = self._get_all_parents(self.employee_id)
            leaves_data = self._leaves_count(self.employee_id)
            # Create a single appraisal for the selected employee
            Appraisal.create({
                'appraisal_run_ids': self.appraisal_run_ids.id,
                'employee_id': self.employee_id.id,
                'department_id': self.employee_id.department_id.id,
                'mode_company_id': self.employee_id.company_id.id,
                'company_id': self.employee_id.company_id.id,
                'education': self.employee_id.academic_ids[0].degree_id.name if self.employee_id.academic_ids else False,
                'manager_ids': [(6, 0, manager_hierarchy)],
                'registration_number': self.employee_id.registration_number,
                # 'job_id': self.employee_id.job_id.id,
                'grade': self.employee_id.x_studio_grade,
                'appointment_date': self.employee_id.appointment_date,
                'location': self.employee_id.location_id.emp_location,
                'birthday': self.employee_id.birthday,
                'gross_salary': self.employee_id.contract_id.wage,
                'personal_file_number': self.employee_id.x_studio_personal_file_number,
                # 'name_of_reporting_officer': self.employee_id.parent_id.name,
                'emp_type': self.employee_id.contract_id.emp_type,
                'cl_count': leaves_data.get("casual_leaves_count"),
                'sl_count': leaves_data.get("sick_leaves_count"),
                'earned_leaves_balance': leaves_data.get("earned_leaves_balance")
            })
        elif self.appraisal_type == 'department' and self.departments:
            # Get all employees in the selected department and create an appraisal for each
            employees = self.env['hr.employee'].search([('department_id', '=', self.departments.id)])
            for employee in employees:
                leaves_data = self._leaves_count(employee)
                manager_hierarchy = self._get_all_parents(employee)
                Appraisal.create({
                    'appraisal_run_ids': self.appraisal_run_ids.id,
                    'employee_id': employee.id,
                    'department_id': employee.department_id.id,
                    'mode_company_id': employee.company_id.id,
                    'manager_ids': [(6, 0, manager_hierarchy)],
                    'registration_number': employee.registration_number,
                    # 'job_id': employee.employee_id.job_id.id,
                    'education': employee.academic_ids[0].degree_id.name if employee.academic_ids else False,
                    'grade': employee.x_studio_grade,
                    'appointment_date': employee.appointment_date,
                    'birthday': employee.birthday,
                    'gross_salary': employee.contract_id.wage,
                    'personal_file_number': employee.x_studio_personal_file_number,
                    'location': employee.location_id.emp_location,
                    # 'name_of_reporting_officer': employee.parent_id.name,
                    'emp_type': employee.contract_id.emp_type,
                    'cl_count': leaves_data.get("casual_leaves_count"),
                    'sl_count': leaves_data.get("sick_leaves_count"),
                    'earned_leaves_balance': leaves_data.get("earned_leaves_balance")
                })
        elif self.appraisal_type == 'company' and self.mode_company_id:
            # Get all employees in the company and create an appraisal for each
            employees = self.env['hr.employee'].search([('company_id', '=', self.mode_company_id.id)])
            for employee in employees:
                leaves_data = self._leaves_count(employee)
                manager_hierarchy = self._get_all_parents(employee)
                Appraisal.create({
                    'appraisal_run_ids': self.appraisal_run_ids.id,
                    'employee_id': employee.id,
                    'department_id': employee.department_id.id,
                    'mode_company_id': employee.company_id.id,
                    'manager_ids': [(6, 0, manager_hierarchy)],
                    'registration_number': employee.registration_number,
                    # 'job_id': employee.employee_id.job_id.id,
                    'education': employee.academic_ids[0].degree_id.name if employee.academic_ids else False,
                    'grade': employee.x_studio_grade,
                    'appointment_date': employee.appointment_date,
                    'birthday': employee.birthday,
                    'gross_salary': employee.contract_id.wage,
                    'personal_file_number': employee.x_studio_personal_file_number,
                    'location': employee.location_id.emp_location,
                    # 'name_of_reporting_officer': employee.parent_id.name,
                    'emp_type': employee.contract_id.emp_type,
                    'cl_count': leaves_data.get("casual_leaves_count"),
                    'sl_count': leaves_data.get("sick_leaves_count"),
                    'earned_leaves_balance': leaves_data.get("earned_leaves_balance")
                })

    @api.constrains('recomm_increment_lines_id')
    def onchange_recomm_line(self):
        if self.recomm_increment_lines_id:
            for rec in self.recomm_increment_lines_id:
                if not rec.increment_raise_by:
                    rec.sudo().unlink()

    @api.onchange('state')
    def onchange_state(self):
        if self.state:
            self.doc_state = 'draft'


    def find_managers(self, employee):
        manager = employee.parent_id
        manager2 = manager.parent_id if manager else None
        manager3 = manager2.parent_id if manager2 else None
        manager4 = manager3.parent_id if manager3 else None
        manager5 = manager4.parent_id if manager4 else None

        return {
            'manager1': manager,
            'manager2': manager2,
            'manager3': manager3,
            'manager4': manager4,
            'manager5': manager5
        }

#    def action_reset_back(self):
#        self.doc_state = 'draft'
#        login_user = self.env['res.users'].browse(self.env.context.get('uid'))
#        action_type = ''
#        last_state = self.last_state
#        last_approver = self.sudo().appraisal_last_approver_id.id
#        remarks = self.env.context.get('appraisal_remarks')
#        if remarks and login_user == self.appraisal_approver_id:
#            filtered_lines = self.recomm_increment_lines_id.filtered(
#                lambda line: line.increment_raise_by.id == login_user.id)
#            if not filtered_lines:
#                self.sudo().state = self.recomm_increment_lines_id[-1].state
#                action_type = f"Reverted to {self.recomm_increment_lines_id[-1].state}"
#                if action_type and remarks:
#                    self.message_post(
#                        body=f"Action: {action_type}<br/>Remarks: {remarks}",
#                        subtype_xmlid='mail.mt_note'  # Ye ensure karta hai ke message as a note post ho
#                    )
#                self.sudo().appraisal_approver_id = self.recomm_increment_lines_id[-1].increment_raise_by.id
#                return {
#                    'type': 'ir.actions.act_window',
#                    'name': 'view.appraisal.system.tree',
#                    'res_model': 'appraisal.system',
#                    'view_mode': 'tree,form',
#                    'domain': [],  # Optional: add any filters if needed
#                    'context': {
#                        'group_by': ['state', 'appraisal_approver_id'],  # Grouping fields
#                    },
#                    'target': 'current',  # Replaces the current view
#                }
#            else:
#                filtered_lines_manager = self.sudo().recomm_increment_lines_id.filtered(
#                    lambda line: line.increment_raise_by.employee_id.parent_id.user_id.id == login_user.id)
#                if filtered_lines_manager:
#                    self.state = filtered_lines_manager.state
#                    action_type = f"Reverted to {filtered_lines_manager.state}"
#                    if action_type and remarks:
#                        self.message_post(
#                            body=f"Action: {action_type}<br/>Remarks: {remarks}",
#                            subtype_xmlid='mail.mt_note'  # Ye ensure karta hai ke message as a note post ho
#                        )
#                    self.sudo().appraisal_approver_id = filtered_lines_manager.increment_raise_by.id
#                    return {
#                        'type': 'ir.actions.act_window',
#                        'name': 'view.appraisal.system.tree',
#                        'res_model': 'appraisal.system',
#                        'view_mode': 'tree,form',
#                    'domain': [],  # Optional: add any filters if needed
#                    'context': {
#                        'group_by': ['state', 'appraisal_approver_id'],  # Grouping fields
#                    },
#                        'target': 'current',  # Replaces the current view
#                    }


 #       return {
 #           'type': 'ir.actions.act_window',
 #           'name': 'Appraisal Remarks',
 #           'res_model': 'appraisal.wizard',
 #           'view_mode': 'form',
 #           'target': 'new',
 #           'context': {
 #               'active_id': self.id,
 #           },
 #       }

    def action_reset_back(self):
        if len(self) > 2:
            for rec in self:
                rec.doc_state = 'revert'
                login_user = rec.env['res.users'].browse(rec.env.context.get('uid'))
                action_type = ''
                last_state = rec.last_state
                last_approver = rec.sudo().appraisal_last_approver_id.id
                if login_user == rec.appraisal_approver_id:
                    filtered_lines = rec.recomm_increment_lines_id.filtered(
                        lambda line: line.increment_raise_by.id == login_user.id)
                    if not filtered_lines:
                        rec.sudo().state = rec.recomm_increment_lines_id[-1].state
                        rec.sudo().appraisal_approver_id = rec.recomm_increment_lines_id[-1].increment_raise_by.id
                    else:
                        filtered_lines_manager = rec.sudo().recomm_increment_lines_id.filtered(
                            lambda line: line.increment_raise_by.employee_id.parent_id.user_id.id == login_user.id)
                        if filtered_lines_manager:
                            rec.state = filtered_lines_manager.state
                            rec.sudo().appraisal_approver_id = filtered_lines_manager.increment_raise_by.id
        else:
            for rec in self:
                rec.doc_state = 'revert'
                login_user = rec.env['res.users'].browse(rec.env.context.get('uid'))
                action_type = ''
                last_state = rec.last_state
                last_approver = rec.sudo().appraisal_last_approver_id.id
                remarks = rec.env.context.get('appraisal_remarks')
                if remarks and login_user == rec.appraisal_approver_id:
                    filtered_lines = rec.recomm_increment_lines_id.filtered(
                        lambda line: line.increment_raise_by.id == login_user.id)
                    if not filtered_lines:
                        rec.sudo().state = rec.recomm_increment_lines_id[-1].state
                        action_type = f"Reverted to {rec.recomm_increment_lines_id[-1].state}"
                        if action_type and remarks:
                            rec.message_post(
                                body=f"Action: {action_type}<br/>Remarks: {remarks}",
                                subtype_xmlid='mail.mt_note'  # Ye ensure karta hai ke message as a note post ho
                            )
                        rec.sudo().appraisal_approver_id = rec.recomm_increment_lines_id[-1].increment_raise_by.id
                        return {
                            'type': 'ir.actions.act_window',
                            'name': 'view.appraisal.system.tree',
                            'res_model': 'appraisal.system',
                            'view_mode': 'tree,form',
                            'domain': [],  # Optional: add any filters if needed
                            'context': {
                                'group_by': ['state', 'appraisal_approver_id'],  # Grouping fields
                            },
                            'target': 'current',  # Replaces the current view
                        }
                    else:
                        filtered_lines_manager = rec.sudo().recomm_increment_lines_id.filtered(
                            lambda line: line.increment_raise_by.employee_id.parent_id.user_id.id == login_user.id)
                        if filtered_lines_manager:
                            rec.state = filtered_lines_manager.state
                            action_type = f"Reverted to {filtered_lines_manager.state}"
                            if action_type and remarks:
                                rec.message_post(
                                    body=f"Action: {action_type}<br/>Remarks: {remarks}",
                                    subtype_xmlid='mail.mt_note'  # Ye ensure karta hai ke message as a note post ho
                                )
                            rec.sudo().appraisal_approver_id = filtered_lines_manager.increment_raise_by.id
                            return {
                                'type': 'ir.actions.act_window',
                                'name': 'view.appraisal.system.tree',
                                'res_model': 'appraisal.system',
                                'view_mode': 'tree,form',
                                'domain': [],  # Optional: add any filters if needed
                                'context': {
                                    'group_by': ['state', 'appraisal_approver_id'],  # Grouping fields
                                },
                                'target': 'current',  # Replaces the current view
                            }


                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Appraisal Remarks',
                    'res_model': 'appraisal.wizard',
                    'view_mode': 'form',
                    'target': 'new',
                    'context': {
                        'active_id': rec.id,
                    },
                }

    def action_cancel(self):
        login_user = self.env['res.users'].browse(self.env.context.get('uid'))
        manager = self.find_managers(self.employee_id)

        if login_user.has_group('aesl_appraisal_system.group_hr_manager_appraisal_3'):
            self.write({
                'state': 'cancel',
                'appraisal_approver_id': login_user.id
            })

        if self.state == 'new':
            if not manager.get('manager1').user_id == login_user:
                raise UserError("You are not authorized to cancel this Appraisal.")
            else:
                self.write({
                    'state': 'cancel',
                    'date_final_interview': False
                })

        elif self.state == 'pending':
            if not manager.get('manager2').user_id == login_user:
                raise UserError("You are not authorized to cancel this Appraisal.")
            else:
                self.write({
                    'state': 'cancel',
                    'date_final_interview': False
                })

        elif self.state == 'pending2':
            if not manager.get('manager3').user_id == login_user:
                raise UserError("You are not authorized to cancel this Appraisal.")
            else:
                self.write({
                    'state': 'cancel',
                    'date_final_interview': False
                })

        elif self.state == 'pending3':
            if not manager.get('manager4').user_id == login_user:
                raise UserError("You are not authorized to cancel this Appraisal.")
            else:
                self.write({
                    'state': 'cancel',
                    'date_final_interview': False
                })
        else:
            raise UserError("You are not authorized to cancel this Appraisal.")
        # if self.state == 'cancel':
        #     self.send_appraisal(self.state)
        self.mapped('meeting_id').unlink()
        self.activity_unlink(['mail.mail_activity_data_meeting', 'mail.mail_activity_data_todo'])
        self.send_appraisal()

    def send_appraisal(self):
        login_user = self.env['res.users'].browse(self.env.context.get('uid'))
        hr_user = self.env['res.users'].search([('id', '=', 7)])
        employee = hr_user
        # managerss = self.find_managers(self.employee_id)
        appraisal_status = self.state
        for appraisal in self:
            # employee_mail_template = appraisal.company_id.appraisal_confirm_employee_mail_template
            # hr_mail_template = appraisal.company_id.appraisal_confirm_hr_mail_template
            if appraisal_status == 'draft':
                managers_mail_template = self.env.ref('aesl_appraisal_system.mail_template_request_appraisals_manager')
            elif appraisal_status in ['new', 'pending', 'pending2', 'pending3']:
                # managers_mail_template = appraisal.company_id.appraisal_confirm_manager_mail_template
                managers_mail_template = self.env.ref('aesl_appraisal_system.mail_template_confirm_appraisals_manager')
            elif appraisal_status == 'cancel':
                managers_mail_template = self.env.ref('aesl_appraisal_system.mail_template_appraisals_cancel_manager')
            elif appraisal_status == 'done':
                managers_mail_template = self.env.ref('aesl_appraisal_system.mail_template_appraisals_done_manager')
            else:
                return
            for manager in self.manager_ids:
                if self.state == 'draft' or login_user.has_group(
                        'aesl_appraisal_system.group_hr_manager_appraisal') or (login_user.id == 7):
                    # employee = managerss.get('manager1')
                    employee = self.employee_id.parent_id
                elif (login_user == manager.user_id):
                    if (login_user.login not in ['0000063', '0000071']):
                        employee = manager.parent_id
                    else:
                        employee = appraisal.create_uid
                else:
                    employee = appraisal.create_uid

            mail_template = managers_mail_template

            # mapped_data = {
            #     # **{appraisal.employee_id: employee_mail_template},
            #     **{manager: managers_mail_template for manager in appraisal.manager_ids}
            # }
            # for employee, mail_template in mapped_data.items():
            if not (employee.work_email or self.env.user.email):
                continue
            ctx = {
                'employee_to_name': appraisal.create_uid.name if appraisal_status in ['cancel',
                                                                                      'done'] else employee.name,
                'recipient_users': appraisal.create_uid if appraisal_status in ['cancel', 'done'] else employee.user_id,
                'url': '/mail/view?model=%s&res_id=%s' % ('appraisal.system', appraisal.id),
            }
            RenderMixin = self.env['mail.render.mixin'].with_context(**ctx)
            subject = \
                RenderMixin._render_template(mail_template.subject, 'appraisal.system', appraisal.ids,
                                             post_process=True)[
                    appraisal.id]
            body = \
                RenderMixin._render_template(mail_template.body_html, 'appraisal.system', appraisal.ids,
                                             post_process=True)[
                    appraisal.id]
            # post the message
            mail_values = {
                'email_from': self.env.user.email_formatted,
                'author_id': self.env.user.partner_id.id,
                'model': None,
                'res_id': None,
                'subject': subject,
                'body_html': body,
                'auto_delete': True,
                'email_to': appraisal.create_uid.email if appraisal_status in ['cancel',
                                                                               'done'] else employee.work_email
            }
            try:
                template = self.env.ref('mail.mail_notification_light', raise_if_not_found=True)
            except ValueError:
                _logger.warning(
                    'QWeb template mail.mail_notification_light not found when sending appraisal confirmed mails. Sending without layouting.')
            else:
                template_ctx = {
                    'message': self.env['mail.message'].sudo().new(
                        dict(body=mail_values['body_html'], record_name=employee.name)),
                    'model_description': self.env['ir.model']._get('appraisal.system').display_name,
                    'company': self.env.company,
                }
                body = template._render(template_ctx, engine='ir.qweb', minimal_qcontext=True)
                mail_values['body_html'] = self.env['mail.render.mixin']._replace_local_links(body)
            self.env['mail.mail'].sudo().create(mail_values)

            # if employee.user_id:
            #     appraisal.activity_schedule(
            #         'mail.mail_activity_data_todo', appraisal.date_close,
            #         summary=_('Appraisal Form to Fill'),
            #         note=_('Fill appraisal for <a href="#" data-oe-model="%s" data-oe-id="%s">%s</a>') % (
            #             appraisal.employee_id._name, appraisal.employee_id.id, appraisal.employee_id.display_name),
            #         user_id=employee.user_id.id)

    @api.model
    def create(self, vals):
        seq_date = vals.get('create_date', fields.Datetime.now())
        vals['name'] = self.env['ir.sequence'].next_by_code(
            'appraisal.system', sequence_date=seq_date) or _('New')

        """Override the create method to allow only 'Hasan Saeed' from the 'Appraisal/Administrator' group to create records."""
        login_user = self.env['res.users'].browse(self.env.context.get('uid'))
        if 'remarks' in vals and vals['remarks']:
            vals['remarks'] += f"\nBy: {login_user.name} {fields.Datetime.now().strftime('%a, %d-%b-%Y')}"
        elif 'remarks_2' in vals and vals['remarks_2']:
            vals['remarks_2'] += f"\nBy: {login_user.name} {fields.Datetime.now().strftime('%a, %d-%b-%Y')}"
        elif 'remarks_3' in vals and vals['remarks_3']:
            vals['remarks_3'] += f"\nBy: {login_user.name} {fields.Datetime.now().strftime('%a, %d-%b-%Y')}"
        elif 'remarks_4' in vals and vals['remarks_4']:
            vals['remarks_4'] += f"\nBy: {login_user.name} {fields.Datetime.now().strftime('%a, %d-%b-%Y')}"
        elif 'remarks_5' in vals and vals['remarks_5']:
            vals['remarks_5'] += f"\nBy: {login_user.name} {fields.Datetime.now().strftime('%a, %d-%b-%Y')}"
        else:
            pass

        # Set a context flag to avoid recursive appraisal creation
        if not self.env.context.get('skip_appraisal_creation', False):
            # vals['appraisal_triggered'] = True  # Add this just as a safeguard or indicator
            record = super(AppraisalSystem, self).with_context(skip_appraisal_creation=True).create(vals)
            record.create_appraisal_requests()
            return record
        else:
            return super(AppraisalSystem, self).create(vals)

        self.check_anomynous_records_appraisal()

    # @api.onchange('remarks','remarks_2','remarks_3','remarks_4')
    # def remarks_onchange(self):
    #     login_user = self.env['res.users'].browse(self.env.context.get('uid'))
    #     if self.remarks:
    #         self.remarks += f"\n**{login_user.name}**"
    #     elif self.remarks_2:
    #         self.remarks_2 += f"\n**{login_user.name}**"
    #     elif self.remarks_3:
    #         self.remarks_3 += f"\n**{login_user.name}**"
    #     elif self.remarks_4:
    #         self.remarks_4 += f"\n**{login_user.name}**"
    #     else:
    #         pass

    def write(self, vals):
        login_user = self.env['res.users'].browse(self.env.context.get('uid'))
        my_list = ['remarks','remarks_2','remarks_3','remarks_4','remarks_5']
        if any(key in vals for key in my_list):
            self.doc_state = 'save'
        if 'recomm_increment_lines_id' in vals:
            filtered_lines = self.recomm_increment_lines_id.filtered(
                lambda line: line.increment_raise_by.id == login_user.id)
            if filtered_lines:
                for inner_list in vals.get("recomm_increment_lines_id", []):
                    # Loop through the elements of the inner list
                    for element in inner_list:
                        # Check if the element is a dictionary and contains the key
                        if isinstance(element, dict) and "increment_raise_amount" in element:
                            self.recommend_raise_amount = element["increment_raise_amount"]
                            self.increase_percentage = (self.recommend_raise_amount / self.gross_salary * 100)
                        if isinstance(element, dict) and "recomm_desigantion_id" in element:
                            self.recommend_designation_id = element["recomm_desigantion_id"]
                        if isinstance(element, dict) and "recomm_grades" in element:
                            self.recommend_grades = element["recomm_grades"]

                if vals['recomm_increment_lines_id'][0][0] == 0:
                    raise ValidationError(_('You Can not add more lines'))

            if vals['recomm_increment_lines_id'][0][-1]:
                self.recommend_raise_amount = vals['recomm_increment_lines_id'][0][-1].get('increment_raise_amount') if vals['recomm_increment_lines_id'][0][-1].get('increment_raise_amount') else self.recommend_raise_amount
                self.recommend_designation_id = vals['recomm_increment_lines_id'][0][-1].get('recomm_desigantion_id') if vals['recomm_increment_lines_id'][0][-1].get('recomm_desigantion_id') else self.recommend_designation_id
                self.increase_percentage = ((vals['recomm_increment_lines_id'][0][-1].get('increment_raise_amount') / self.gross_salary * 100) if vals['recomm_increment_lines_id'][0][-1].get('increment_raise_amount') else 0)
                self.recommend_grades = vals['recomm_increment_lines_id'][0][-1].get('recomm_grades') if vals['recomm_increment_lines_id'][0][-1].get('recomm_grades') else self.recommend_grades
                if 'state' in vals['recomm_increment_lines_id'][0][-1] and vals['recomm_increment_lines_id'][0][-1]['state']:
                    vals['recomm_increment_lines_id'][0][-1].update(
                        {'increment_raise_by': login_user.id, 'incremented_date': fields.Datetime.now(),'state':vals['recomm_increment_lines_id'][0][-1]['state']})
                else:
                    vals['recomm_increment_lines_id'][0][-1].update(
                        {'increment_raise_by': login_user.id, 'incremented_date': fields.Datetime.now(),
                         'state': self.state})

#        if 'remarks' in vals and vals['remarks']:
#            if len(vals['remarks']) >= 1300:
#                raise ValidationError(_('Please enter the remarks limited'))
#            else:
#                vals['remarks'] += f"\nBy: {login_user.name} {fields.Datetime.now().strftime('%a, %d-%b-%Y')}"
#        if 'remarks_2' in vals and vals['remarks_2']:
#            if len(vals['remarks_2']) >= 320:
#                raise ValidationError(_('Please enter the remarks limited'))
#            else:
#                vals['remarks_2'] += f"\nBy: {login_user.name} {fields.Datetime.now().strftime('%a, %d-%b-%Y')}"
#        if 'remarks_3' in vals and vals['remarks_3']:
#            if len(vals['remarks_3']) >= 320:
#                raise ValidationError(_('Please enter the remarks limited'))
#            else:
#                vals['remarks_3'] += f"\nBy: {login_user.name} {fields.Datetime.now().strftime('%a, %d-%b-%Y')}"

#        if 'remarks_4' in vals and vals['remarks_4']:
#            if len(vals['remarks_4']) >= 320:
#                raise ValidationError(_('Please enter the remarks limited'))
#            else:
#                vals['remarks_4'] += f"\nBy: {login_user.name} {fields.Datetime.now().strftime('%a, %d-%b-%Y')}"

#        if 'remarks_5' in vals and vals['remarks_5']:
#            if len(vals['remarks_5']) >= 1300:
#                raise ValidationError(_('Please enter the remarks limited'))
#            else:
#                vals['remarks_5'] += f"\nBy: {login_user.name} {fields.Datetime.now().strftime('%a, %d-%b-%Y')}"


#        if 'future_project' in vals and vals['future_project']:
#            if len(vals['future_project']) >= 490:
#                raise ValidationError(_('Please enter the future prospect limited'))
#            else:
#                vals['future_project'] += f"\nBy: {login_user.name} {fields.Datetime.now().strftime('%a, %d-%b-%Y')}"


        if 'remarks' in vals and vals['remarks']:
            # if len(vals['remarks']) >= 1300:
            #     raise ValidationError(_('Please enter the remarks limited'))
            # else:
            vals['remarks'] += f"\nBy: {login_user.name} {fields.Datetime.now().strftime('%a, %d-%b-%Y')}"
        if 'remarks_2' in vals and vals['remarks_2']:
            # if len(vals['remarks_2']) >= 320:
            #     raise ValidationError(_('Please enter the remarks limited'))
            # else:
            vals['remarks_2'] += f"\nBy: {login_user.name} {fields.Datetime.now().strftime('%a, %d-%b-%Y')}"
        if 'remarks_3' in vals and vals['remarks_3']:
            # if len(vals['remarks_3']) >= 320:
            #     raise ValidationError(_('Please enter the remarks limited'))
            # else:
            vals['remarks_3'] += f"\nBy: {login_user.name} {fields.Datetime.now().strftime('%a, %d-%b-%Y')}"

        if 'remarks_4' in vals and vals['remarks_4']:
            # if len(vals['remarks_4']) >= 320:
            #     raise ValidationError(_('Please enter the remarks limited'))
            # else:
            vals['remarks_4'] += f"\nBy: {login_user.name} {fields.Datetime.now().strftime('%a, %d-%b-%Y')}"

        if 'remarks_5' in vals and vals['remarks_5']:
            # if len(vals['remarks_5']) >= 1300:
            #     raise ValidationError(_('Please enter the remarks limited'))
            # else:
            vals['remarks_5'] += f"\nBy: {login_user.name} {fields.Datetime.now().strftime('%a, %d-%b-%Y')}"


        if 'future_project' in vals and vals['future_project']:
            # if len(vals['future_project']) >= 500:
            #     raise ValidationError(_('Please enter the future prospect limited'))
            # else:
            vals['future_project'] += f"\nBy: {login_user.name} {fields.Datetime.now().strftime('%a, %d-%b-%Y')}"


        if not self.is_manager:
            if self.state == 'draft' and login_user.has_group('aesl_appraisal_system.group_hr_manager_appraisal_3'):
                pass
            elif self.state == 'new' and self.employee_id.parent_id.user_id != login_user:
                if not self.env.context.get('appraisal_remarks'):
                    raise ValidationError(_('You Are Not Allowed!'))
        result = super(AppraisalSystem, self).write(vals)
        return result

    def unlink(self):
        if any(appraisal.state not in ['draft', 'cancel'] for appraisal in self):
            raise UserError(_("You cannot delete appraisal which is not in draft or canceled state"))
        return super(AppraisalSystem, self).unlink()

    def check_anomynous_records_appraisal(self):
        appraisals = self.env['appraisal.system'].search([('emp_type', 'not in', ['probation', 'permanent'])])
        for apr_rec in appraisals:
            if not (apr_rec.emp_type or apr_rec.registration_number):
                apr_rec.unlink()



import datetime
import logging
from datetime import date
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AppraisalSystem(models.Model):
    _name = 'appraisal.system'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Appraisal System Custom'

    name = fields.Char(default=_('New'))

    def _get_default_employee(self):
        # if not self.env.user.has_group('aesl_appraisal_system.group_user_appraisals'):
        return self.env.user.employee_id

    def _get_default_company(self):
        return self.env.user.company_id[0]

    appraisal_type = fields.Selection([
        ('employee', 'By Employee'),
        ('company', 'By Company'),
        ('department', 'By Department')],
        string='Appraisal Mode', readonly=False, required=True, default='employee')
    mode_company_id = fields.Many2one(
        'res.company', compute='_compute_from_holiday_type', store=True, string='Company Mode', readonly=False)
    department_id = fields.Many2one(
        'hr.department', string='Department')
    # company_id = fields.Many2one('res.company', store=True)
    employee_id = fields.Many2one(
        'hr.employee', required=True, string='Name', index=True,
        default=_get_default_employee)
    image_128 = fields.Image()
    image_1920 = fields.Image()
    departments = fields.Many2one('hr.department', string='Department')
    # manager_ids = fields.Many2many('hr.employee')
    company_id = fields.Many2one('res.company', store=True, default=_get_default_company)
    manager_ids = fields.Many2many(
        'hr.employee',  # Target model
        'appraisal_manager_rel',  # Relation table
        'hr_appraisal_id',  # Column for appraisal.system model ID
        'manager_id',  # Column for hr.employee model ID
        string='Managers',
        store=True
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
    # job_id = fields.Many2one('hr.job', string='Designation')
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

    remarks = fields.Text('Remarks:', size=10)
    remarks_2 = fields.Text('Remarks', size=10)
    remarks_3 = fields.Text('Remarks', size=50)
    remarks_4 = fields.Text('Remarks', size=50)
    remarks_5 = fields.Text('Remarks', size=50)
    future_project = fields.Text('Future Prospect')
    accomplishment = fields.Text('Accomplishment')

    recomm_increment = fields.Float('Increase Recommended?', tracking=True)
    recomm_increment_lines_id = fields.One2many('increment.raise.lines', 'increment_raise_id',
                                                string='Increase Recommended Lines',
                                                required=True, index=True, ondelete='cascade')
    # signature_of_reporting_officer = fields.Binary("Signature of Reporting Officer", store=True)
    name_of_reporting_officer = fields.Many2one('res.users', string='Reporting Officer')
    ro_submit_date = fields.Date("RO Submit Date")
    # countersignedBy = fields.Binary("Countersigned By", store=True)
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
        ('done', 'Done'),
        ('revert', 'Revert'),
        ('publish', 'Publish')], default='draft'
    )
    recommend_raise_amount = fields.Float(string="Recom. Increment")
    recommend_designation_id = fields.Many2one('hr.job', string='Recom. Designation')
    recommend_grades = fields.Integer(string='Recom. Grade')
    increase_percentage = fields.Float(string='Increment (%)', group_operator=False)
    dept_abbreviation = fields.Boolean('Dept. Abbreviation', default=False)
    x_css = fields.Html(sanitize=False, compute='_compute_css', store=False)

    def _compute_css(self):
        for rec in self:
            # To Remove Edit Option
            if rec.state == 'done':
                rec.x_css = '<style>.o_form_button_edit {display: none !important;}</style>'
            else:
                rec.x_css = False

    @api.onchange('dept_abbreviation')
    def onchange_dept_abbreviation(self):
        if self.dept_abbreviation:  # Check if the field has a value
            message = _(
                "'Department Abbreviation'\n"
                "CE -> ENGINE CATERPILLAR\n"
                "CM -> MACHINE CATERPILLAR\n"
                "CO -> SERVICES S. O. S. LAB\n"
                "CP -> PARTS CATERPILLAR\n"
                "CS -> SERVICE ENGINE CATERPILLAR\n"
                "CU -> SOLAR DEPARTMENT\n"
                "DD -> GRUNDFOS PUMP\n"
                "GA -> GENERAL ADMINISTRATION\n"
                "GE -> ENGINE G.O.\n"
                "GF -> GENERAL FINANCE\n"
                "GH -> GENERAL TECHNICAL CELL\n"
                "GI -> INFORMATION TECHNOLOGY\n"
                "GM -> MACHINES G.O.\n"
                "GN -> GENERAL SALES ADMIN.\n"
                "GP -> PARTS G.O.\n"
                "GS -> SERVICE G.O.\n"
                "GU -> GENERAL SOLAR DEPARTMENT\n"
                "ID -> COMPRESSOR SALES\n"
                "IS -> COMPRESSOR SERVICE\n"
                "NP -> COMPRESSOR PARTS\n"
                "OE -> ENGINE OLYMPIAN"
            )
            raise ValidationError(message)

    def _compute_is_recommended_by_user(self):
        for record in self:
            record.is_recommended_by_user = any(
                line.increment_raise_by.id == self.env.user.id for line in record.recomm_increment_lines_id)

    def _group_expand_states(self, states, domain, order=None):
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

    @api.onchange('remarks', 'remarks_2', 'remarks_3', 'remarks_4', 'remarks_5', )
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
                # appr_dept.education = appr_dept.employee_id.academic_ids.degree_id.name
                appr_dept.department_id = appr_dept.departments
                appr_dept.mode_company_id = appr_dept.departments.company_id.id
                # appr_dept.job_id = appr_dept.employee_id.job_id.id
                appr_dept.departments = appr_dept.departments
                appr_dept.registration_number = appr_dept.employee_id.registration_number
                appr_dept.grade = appr_dept.employee_id.contract_id.x_studio_grade
                appr_dept.appointment_date = appr_dept.employee_id.appointment_date
                appr_dept.birthday = appr_dept.employee_id.birthday
                appr_dept.gross_salary = appr_dept.employee_id.contract_id.wage
                appr_dept.personal_file_number = appr_dept.employee_id.x_studio_personal_file_number
                # appr_dept.location = appr_dept.employee_id.location_id.name
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
                'employee_id': self.employee_id.id,
                'department_id': self.employee_id.department_id.id,
                'mode_company_id': self.employee_id.company_id.id,
                'company_id': self.employee_id.company_id.id,
                # 'education': self.employee_id.academic_ids[0].degree_id.name if self.employee_id.academic_ids else False,
                'manager_ids': [(6, 0, manager_hierarchy)],
                'registration_number': self.employee_id.registration_number,
                # 'job_id': self.employee_id.job_id.id,
                'grade': self.employee_id.contract_id.x_studio_grade,
                'appointment_date': self.employee_id.appointment_date,
                # 'location': self.employee_id.location_id.name,
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
                    'employee_id': employee.id,
                    'department_id': employee.department_id.id,
                    'mode_company_id': employee.company_id.id,
                    'manager_ids': [(6, 0, manager_hierarchy)],
                    'registration_number': employee.registration_number,
                    # 'job_id': employee.employee_id.job_id.id,
                    # 'education': employee.academic_ids[0].degree_id.name if employee.academic_ids else False,
                    'grade': employee.contract_id.x_studio_grade,
                    'appointment_date': employee.appointment_date,
                    'birthday': employee.birthday,
                    'gross_salary': employee.contract_id.wage,
                    'personal_file_number': employee.x_studio_personal_file_number,
                    # 'location': employee.location_id.name,
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
                    'employee_id': employee.id,
                    'department_id': employee.department_id.id,
                    'mode_company_id': employee.company_id.id,
                    'manager_ids': [(6, 0, manager_hierarchy)],
                    'registration_number': employee.registration_number,
                    # 'job_id': employee.employee_id.job_id.id,
                    # 'education': employee.academic_ids[0].degree_id.name if employee.academic_ids else False,
                    'grade': employee.contract_id.x_studio_grade,
                    'appointment_date': employee.appointment_date,
                    'birthday': employee.birthday,
                    'gross_salary': employee.contract_id.wage,
                    'personal_file_number': employee.x_studio_personal_file_number,
                    # 'location': employee.location_id.name,
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
            self.dept_abbreviation = False

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

    def action_hr_confirm(self):
        for record in self:
            login_user = record.env['res.users'].browse(record.env.context.get('uid'))
            if login_user.has_group('aesl_appraisal_system.group_hr_manager_appraisal_3') and record.state == 'draft':
                # record.send_appraisal()
                record.update({
                    'appraisal_approver_id': record.employee_id.parent_id.user_id,
                    'last_state': record.state,
                    'appraisal_last_approver_id': record.env.user.id,
                    'is_hr_confirm': True,
                    'state': 'new' if record.employee_id.parent_id.user_id.id != 408 else 'pending3'})

    def action_confirm(self):
        """Handles the Line Manager confirmation process."""
        self.doc_state = 'draft'
        current_state = self.state
        login_user = self.env.user
        manager_user = self.env['res.users'].browse(414)
        self.sudo().appraisal_last_approver_id = login_user
        manager = self.sudo().find_managers(self.sudo().employee_id)

        # Update flags based on the number of managers
        manager_count = len(self.manager_ids)
        self.update({
            'is_md_state': manager_count <= 2,
            'is_exec_state': manager_count <= 3,
        })

        # Ensure the login user is the reporting officer
        if self.employee_id.parent_id.user_id != login_user:
            raise ValidationError(_('Please let Mr. %s fill the form.') % self.employee_id.parent_id.user_id.name)

        # Set reporting officer details
        self.update({
            'name_of_reporting_officer': login_user,
            'ro_submit_date': fields.Datetime.now(),
            'last_state': current_state,
        })

        # Define state transitions and approvers based on manager count
        state_mapping = {
            2: ('pending3', self.employee_id.parent_id.parent_id.user_id, {'is_md_state': True}),
            3: ('pending4', self.employee_id.parent_id.parent_id.parent_id.user_id, {'is_exec_state': True}),
            4: ('pending2', self.employee_id.parent_id.parent_id.user_id, {'is_manager2': True, 'is_manager3': True}),
        }

        # Handle special cases for specific users
        if login_user.id in (663, 626):
            self.sudo().write({
                'state': 'pending4',
                'is_manager': True,
                'is_exec_state': True,
                'appraisal_approver_id': manager_user.id,
            })
        elif manager_count in state_mapping:
            new_state, approver, extra_fields = state_mapping[manager_count]
            self.sudo().write({
                'state': new_state,
                'appraisal_approver_id': approver.id,
                **extra_fields,
            })
        else:
            self.sudo().write({
                'state': 'pending',
                'is_manager': True,
                'is_manager2': True,
                'appraisal_approver_id': self.employee_id.parent_id.parent_id.user_id.id,
            })

        # Add a recommended increment line if it doesn't already exist
        self._add_recommended_increment_line(login_user, current_state)

        # Return the action window
        return self._get_appraisal_action_window()

    def _add_recommended_increment_line(self, login_user, current_state):
        """Adds a recommended increment line if it doesn't already exist."""
        if not self.sudo().recomm_increment_lines_id.filtered(lambda line: line.increment_raise_by.id == login_user.id):
            last_line = self.recomm_increment_lines_id[-1]
            self.recomm_increment_lines_id = [(0, 0, {
                'increment_raise_amount': last_line.increment_raise_amount,
                'recomm_desigantion_id': last_line.recomm_desigantion_id.id,
                'recomm_grades': last_line.recomm_grades,
                'increment_raise_by': login_user.id,
                'incremented_date': fields.Datetime.now().strftime('%a, %d-%b-%Y'),
                'state': current_state,
            })]

    def _get_appraisal_action_window(self):
        """Returns the action window for the appraisal system."""
        return {
            'type': 'ir.actions.act_window',
            'name': 'view.appraisal.system.tree',
            'res_model': 'appraisal.system',
            'view_mode': 'tree,form',
            'context': {'group_by': ['state', 'appraisal_approver_id']},
            'target': 'current',
        }

    def action_confirm2(self):  # Dept. Manager Button
        """Handles the Department Manager confirmation process."""
        self.doc_state = 'draft'
        current_state = self.state
        login_user = self.env.user
        manager = self.sudo().find_managers(self.sudo().employee_id)
        manager_user = self.env['res.users'].browse(414)

        # Update flags based on the number of managers
        manager_count = len(self.sudo().manager_ids)
        self.sudo().update({
            'is_md_state': manager_count <= 3,
            'is_exec_state': manager_count <= 4,
        })

        # Handle special case for specific users (663 or 626)
        if login_user.id in (663, 626):
            self._update_state_and_approver('pending4', manager_user.id, is_manager2=True, is_exec_state=True)
            self._add_recommended_increment_line(login_user, current_state)
            return self._get_appraisal_action_window()

        # Check if the login user is the grandparent's manager
        if self.sudo().employee_id.parent_id.parent_id.user_id != login_user:
            raise ValidationError(
                _('Please let Mr. %s proceed the form.') % self.sudo().employee_id.parent_id.parent_id.user_id.name
            )

        # Handle state transitions based on manager hierarchy
        if not manager.get('manager4'):
            self._update_state_and_approver('pending3',
                                            self.sudo().employee_id.parent_id.parent_id.parent_id.user_id.id,
                                            is_md_state=True)
        else:
            self._update_state_and_approver('pending2',
                                            self.sudo().employee_id.parent_id.parent_id.parent_id.user_id.id,
                                            is_manager3=True)

        # Add a recommended increment line if it doesn't already exist
        self._add_recommended_increment_line(login_user, current_state)

        # Return the action window
        return self._get_appraisal_action_window()

    def _update_state_and_approver(self, state, approver_id, **kwargs):
        """Updates the state, approver, and additional fields."""
        self.sudo().write({
            'last_state': self.state,
            'state': state,
            'appraisal_approver_id': approver_id,
            **kwargs,
        })

    def action_confirm4(self):  # Executive Button
        """Handles the Executive confirmation process."""
        for rec in self:
            rec.doc_state = 'draft'
            current_state = rec.state
            login_user = rec.env.user
            manager_user = rec.env['res.users'].browse(408)
            rec.appraisal_last_approver_id = login_user

            # Check if the login user is the authorized executive (ID 414)
            if login_user.id != 414:
                raise ValidationError(_('Please let Mr. Ahad proceed the form.'))

            # Update state and flags
            rec.sudo().write({
                'last_state': rec.state,
                'state': 'pending3',
                'is_exec_state': True,
                'appraisal_approver_id': manager_user.id,
            })

            # Add a recommended increment line if it doesn't already exist
            rec._add_recommended_increment_line(login_user, current_state)

            # Return the action window if processing a single record
            if len(self) == 1:
                return rec._get_appraisal_action_window()

    def action_confirm3(self):  # Director Button
        """Handles the Director confirmation process."""
        self.doc_state = 'draft'
        current_state = self.state
        login_user = self.env.user
        manager_user = self.env['res.users'].browse(414)

        # Check if the login user is the authorized approver
        if self.sudo().appraisal_approver_id != login_user:
            raise ValidationError(_('Please let Mr. %s proceed the form.') % self.sudo().appraisal_approver_id.name)

        # Update state and flags
        self.sudo().write({
            'last_state': self.state,
            'state': 'pending4',
            'is_manager3': True,
            'appraisal_last_approver_id': login_user.id,
        })

        # Add a recommended increment line if it doesn't already exist
        self._add_recommended_increment_line(login_user, current_state)

        # Set the approver based on the login user
        if login_user.id == 663:
            self.sudo().appraisal_approver_id = manager_user.id
        else:
            self.sudo().appraisal_approver_id = self.sudo().appraisal_approver_id.employee_id.parent_id.user_id.id

        # Return the action window
        return self._get_appraisal_action_window()

    def action_done(self):
        """Marks the appraisal as done and performs final updates."""
        self.doc_state = 'done'
        current_state = self.state
        login_user = self.env.user
        current_date = datetime.date.today()

        # Check if the login user is authorized (ID 408)
        if login_user.id != 408:
            raise ValidationError(_('Mr. Syed Feisal Ali will complete/done the Appraisal.'))

        # Update appraisal details
        self.sudo().write({
            'appraisal_last_approver_id': login_user.id,
            # 'countersignedby_name': login_user.id,
            # 'countersignature_date': fields.Datetime.now(),
            'last_state': self.state,
            'state': 'done',
        })

        # Add a recommended increment line if it doesn't already exist
        self._add_recommended_increment_line(login_user, current_state)

        # Update the recommended increment amount
        self.recomm_increment = self.recomm_increment_lines_id[-1].increment_raise_amount

        # Return a success message with a rainbow man effect
        return {
            'effect': {
                'fadeout': 'slow',
                'message': 'Everything is correctly Done...',
                'type': 'rainbow_man',
            }
        }

    def action_reset_back(self):
        """Resets the appraisal state and updates the approver based on conditions."""
        for rec in self:
            rec.doc_state = 'revert'
            login_user = rec.env.user
            last_state = rec.last_state
            last_approver = rec.sudo().appraisal_last_approver_id.id
            remarks = rec.env.context.get('appraisal_remarks')

            # Check if the login user is the current approver
            if login_user != rec.appraisal_approver_id:
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Appraisal Remarks',
                    'res_model': 'appraisal.wizard',
                    'view_mode': 'form',
                    'target': 'new',
                    'context': {'active_id': rec.id},
                }

            # Determine the state and approver based on the recommended increment lines
            filtered_lines = rec.recomm_increment_lines_id.filtered(
                lambda line: line.increment_raise_by.id == login_user.id
            )
            if not filtered_lines:
                rec._reset_to_last_recommended_state(remarks)
            else:
                rec._reset_to_manager_recommended_state(login_user, remarks)

            # Return the appraisal tree view
            return rec._get_appraisal_action_window()

    def _reset_to_last_recommended_state(self, remarks):
        """Resets the state and approver to the last recommended increment line."""
        last_line = self.recomm_increment_lines_id[-1]
        self.sudo().write({
            'state': last_line.state,
            'appraisal_approver_id': last_line.increment_raise_by.id,
        })
        self._post_reset_message(last_line.state, remarks)

    def _reset_to_manager_recommended_state(self, login_user, remarks):
        """Resets the state and approver based on the manager's recommended increment line."""
        filtered_lines_manager = self.sudo().recomm_increment_lines_id.filtered(
            lambda line: line.increment_raise_by.employee_id.parent_id.user_id.id == login_user.id
        )
        if filtered_lines_manager:
            self.sudo().write({
                'state': filtered_lines_manager.state,
                'appraisal_approver_id': filtered_lines_manager.increment_raise_by.id,
            })
            self._post_reset_message(filtered_lines_manager.state, remarks)

    def _post_reset_message(self, state, remarks):
        """Posts a message with the reset action and remarks."""
        if remarks:
            action_type = f"Reverted to {state}"
            self.message_post(
                body=f"Action: {action_type}<br/>Remarks: {remarks}",
                subtype_xmlid='mail.mt_note'  # Ensures the message is posted as a note
            )

    """ This function is not used """

    def action_cancel(self):
        login_user = self.env['res.users'].browse(self.env.context.get('uid'))
        manager = self.find_managers(self.employee_id)
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
        self.mapped('meeting_id').unlink()
        self.activity_unlink(['mail.mail_activity_data_meeting', 'mail.mail_activity_data_todo'])
        self.send_appraisal()

    # def send_appraisal(self):
    #     login_user = self.env['res.users'].browse(self.env.context.get('uid'))
    #     hr_user = self.env['res.users'].search([('id', '=', 7)])
    #     employee = hr_user
    #     # managerss = self.find_managers(self.employee_id)
    #     appraisal_status = self.state
    #     for appraisal in self:
    #         # employee_mail_template = appraisal.company_id.appraisal_confirm_employee_mail_template
    #         # hr_mail_template = appraisal.company_id.appraisal_confirm_hr_mail_template
    #         if appraisal_status == 'draft':
    #             managers_mail_template = self.env.ref('aesl_appraisal_system.mail_template_request_appraisals_manager')
    #         elif appraisal_status in ['new', 'pending', 'pending2', 'pending3']:
    #             # managers_mail_template = appraisal.company_id.appraisal_confirm_manager_mail_template
    #             managers_mail_template = self.env.ref('aesl_appraisal_system.mail_template_confirm_appraisals_manager')
    #         elif appraisal_status == 'cancel':
    #             managers_mail_template = self.env.ref('aesl_appraisal_system.mail_template_appraisals_cancel_manager')
    #         elif appraisal_status == 'done':
    #             managers_mail_template = self.env.ref('aesl_appraisal_system.mail_template_appraisals_done_manager')
    #         else:
    #             return
    #         for manager in self.manager_ids:
    #             if self.state == 'draft' or login_user.has_group(
    #                     'aesl_appraisal_system.group_hr_manager_appraisal') or (login_user.id == 7):
    #                 # employee = managerss.get('manager1')
    #                 employee = self.employee_id.parent_id
    #             elif (login_user == manager.user_id):
    #                 if (login_user.login not in ['0000063', '0000071']):
    #                     employee = manager.parent_id
    #                 else:
    #                     employee = appraisal.create_uid
    #             else:
    #                 employee = appraisal.create_uid
    #
    #         mail_template = managers_mail_template
    #
    #         if not (employee.work_email or self.env.user.email):
    #             continue
    #         ctx = {
    #             'employee_to_name': appraisal.create_uid.name if appraisal_status in ['cancel',
    #                                                                                   'done'] else employee.name,
    #             'recipient_users': appraisal.create_uid if appraisal_status in ['cancel', 'done'] else employee.user_id,
    #             'url': '/mail/view?model=%s&res_id=%s' % ('appraisal.system', appraisal.id),
    #         }
    #         RenderMixin = self.env['mail.render.mixin'].with_context(**ctx)
    #         subject = \
    #             RenderMixin._render_template(mail_template.subject, 'appraisal.system', appraisal.ids,
    #                                          post_process=True)[
    #                 appraisal.id]
    #         body = \
    #             RenderMixin._render_template(mail_template.body_html, 'appraisal.system', appraisal.ids,
    #                                          post_process=True)[
    #                 appraisal.id]
    #         # post the message
    #         mail_values = {
    #             'email_from': self.env.user.email_formatted,
    #             'author_id': self.env.user.partner_id.id,
    #             'model': None,
    #             'res_id': None,
    #             'subject': subject,
    #             'body_html': body,
    #             'auto_delete': True,
    #             'email_to': appraisal.create_uid.email if appraisal_status in ['cancel',
    #                                                                            'done'] else employee.work_email
    #         }
    #         try:
    #             template = self.env.ref('mail.mail_notification_light', raise_if_not_found=True)
    #         except ValueError:
    #             _logger.warning(
    #                 'QWeb template mail.mail_notification_light not found when sending appraisal confirmed mails. Sending without layouting.')
    #         else:
    #             template_ctx = {
    #                 'message': self.env['mail.message'].sudo().new(
    #                     dict(body=mail_values['body_html'], record_name=employee.name)),
    #                 'model_description': self.env['ir.model']._get('appraisal.system').display_name,
    #                 'company': self.env.company,
    #             }
    #             body = template._render(template_ctx, engine='ir.qweb', minimal_qcontext=True)
    #             mail_values['body_html'] = self.env['mail.render.mixin']._replace_local_links(body)
    #         self.env['mail.mail'].sudo().create(mail_values)

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

    def write(self, vals):
        login_user = self.env['res.users'].browse(self.env.context.get('uid'))
        my_list = ['remarks', 'remarks_2', 'remarks_3', 'remarks_4', 'remarks_5']
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
                    raise ValidationError(_('You cannot add more lines'))

            if vals['recomm_increment_lines_id'][0][-1]:
                self.recommend_raise_amount = vals['recomm_increment_lines_id'][0][-1].get('increment_raise_amount') if \
                    vals['recomm_increment_lines_id'][0][-1].get(
                        'increment_raise_amount') else self.recommend_raise_amount
                self.recommend_designation_id = vals['recomm_increment_lines_id'][0][-1].get('recomm_desigantion_id') if \
                    vals['recomm_increment_lines_id'][0][-1].get(
                        'recomm_desigantion_id') else self.recommend_designation_id
                self.increase_percentage = ((vals['recomm_increment_lines_id'][0][-1].get(
                    'increment_raise_amount') / self.gross_salary * 100) if vals['recomm_increment_lines_id'][0][
                    -1].get('increment_raise_amount') else 0)
                self.recommend_grades = vals['recomm_increment_lines_id'][0][-1].get('recomm_grades') if \
                    vals['recomm_increment_lines_id'][0][-1].get('recomm_grades') else self.recommend_grades
                if 'state' in vals['recomm_increment_lines_id'][0][-1] and vals['recomm_increment_lines_id'][0][-1][
                    'state']:
                    vals['recomm_increment_lines_id'][0][-1].update(
                        {'increment_raise_by': login_user.id, 'incremented_date': fields.Datetime.now(),
                         'state': vals['recomm_increment_lines_id'][0][-1]['state']})
                else:
                    vals['recomm_increment_lines_id'][0][-1].update(
                        {'increment_raise_by': login_user.id, 'incremented_date': fields.Datetime.now(),
                         'state': self.state})

        if 'remarks' in vals and vals['remarks']:
            vals['remarks'] += f"\nBy: {login_user.name} {fields.Datetime.now().strftime('%a, %d-%b-%Y')}"
        if 'remarks_2' in vals and vals['remarks_2']:
            vals['remarks_2'] += f"\nBy: {login_user.name} {fields.Datetime.now().strftime('%a, %d-%b-%Y')}"
        if 'remarks_3' in vals and vals['remarks_3']:
            vals['remarks_3'] += f"\nBy: {login_user.name} {fields.Datetime.now().strftime('%a, %d-%b-%Y')}"

        if 'remarks_4' in vals and vals['remarks_4']:
            vals['remarks_4'] += f"\nBy: {login_user.name} {fields.Datetime.now().strftime('%a, %d-%b-%Y')}"

        if 'remarks_5' in vals and vals['remarks_5']:
            vals['remarks_5'] += f"\nBy: {login_user.name} {fields.Datetime.now().strftime('%a, %d-%b-%Y')}"

        if 'future_project' in vals and vals['future_project']:
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

    @api.model
    def _read_group(self, domain, groupby=(), aggregates=(), having=(), offset=0, limit=None, order=None):
        result = super()._read_group(domain, groupby, aggregates, having, offset, limit, order)

        if 'increase_percentage' in aggregates and 'gross_salary' in aggregates and 'recommend_raise_amount' in aggregates:
            for group in result:
                group_domain = group.get('__domain', [])
                records = self.search(group_domain)

                total_gross_salary = sum(records.mapped('gross_salary'))
                total_raise_amount = sum(records.mapped('recommend_raise_amount'))

                group['increase_percentage'] = (
                                                           total_raise_amount / total_gross_salary) * 100 if total_gross_salary > 0 else 0.0

        return result

    def action_approve_appraisal_to_employee(self):
        for record in self:
            increment_grade = ""
            increment_designation = ""
            if record.doc_state != 'done':
                raise ValidationError(_("Please publish only 'HR' state records"))

            if record.employee_id and record.doc_state != 'publish':
                record.doc_state = 'publish'
                if record.recomm_increment_lines_id[-1].recomm_desigantion_id and record.recomm_increment_lines_id[
                    -1].recomm_desigantion_id != record.sudo().employee_id.job_id:
                    increment_designation = record.recomm_increment_lines_id[-1].recomm_desigantion_id.name

                if record.recomm_increment_lines_id[-1].recomm_grades and record.recomm_increment_lines_id[
                    -1].recomm_grades != int(record.sudo().employee_id.contract_id.x_studio_grade):
                    increment_grade = record.recomm_increment_lines_id[-1].recomm_grades

                self.env['employee.appraisal.history'].create({
                    'appraisal_history_id': record.employee_id.id,
                    'employee_id': record.employee_id.id,
                    'increment_amount': record.recomm_increment,
                    'recommended_grade': increment_grade,
                    'recommended_designation': increment_designation,
                    'year': record.write_date.date().year,
                    'appraisal_date': record.write_date.date(),
                    'company_id': record.sudo().employee_id.company_id.id,
                    'personal_file_no': record.sudo().employee_id.x_studio_personal_file_number,
                    'gross_salary': record.sudo().employee_id.contract_id.wage,
                    'department': record.sudo().employee_id.department_id.name,
                    'designation': record.sudo().employee_id.job_id.name,
                    'location': record.sudo().employee_id.location_id.name,
                })

        return {
            'effect': {
                'fadeout': 'slow',
                'message': 'Appraisal has sent to employee',
                'type': 'rainbow_man',
            }
        }

    def action_appraisal_to_employee_contract(self):
        for record in self:
            if record.employee_id and record.doc_state == 'publish':
                contract = self.env['hr.contract'].search([
                    ('employee_id', '=', record.employee_id.id),
                    ('state', '=', 'open'),
                ])
                employee = self.env['hr.employee'].search([
                    ('id', '=', record.employee_id.id),
                    ('active', '=', 'True'),
                ])
                contract.write({
                    # 'wage': contract.wage + record.recomm_increment if record.recomm_increment else contract.wage,
                    'job_id': record.recommend_designation_id.id if record.recommend_designation_id else contract.job_id
                })
                employee.write({
                    'job_id': record.recommend_designation_id.id if record.recommend_designation_id else employee.job_id,
                    'x_studio_grade': record.recommend_grades if record.recommend_grades > int(
                        employee.contract_id.x_studio_grade) else employee.contract_id.x_studio_grade
                })
            else:
                pass
                # raise ValidationError(_("Contract wage will be updated only for 'Published' records"))

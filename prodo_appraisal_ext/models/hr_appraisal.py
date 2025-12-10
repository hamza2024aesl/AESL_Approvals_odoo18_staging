# ---------------------------------------------------------
# DYNAMIC APPRAISAL WORKFLOW – FINAL VERSION
# ---------------------------------------------------------

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError,UserError
from datetime import date, datetime, time


class HrAppraisal(models.Model):
    _inherit = "hr.appraisal"

    state = fields.Selection([
        ('draft', 'Draft'),
        ('new', 'Line Manager'),
        ('pending', 'Manager Review'),
        ('executive', 'Executive Review'),
        ('md', 'MD Review'),
        ('done', 'HR Final'),
        ('published', 'Published'),
    ], default='draft', tracking=True)

    current_approver_id = fields.Many2one('res.users', string="Current Approver")
    recomm_increment = fields.Float("Final Increment")
    gross_salary = fields.Float("Gross Salary", compute='_compute_gross_salary')

    recomm_increment_lines_id = fields.One2many('increment.raise.lines', 'increment_raise_id',
                                                string='Increase Recommended Lines',
                                                required=True, index=True, ondelete='cascade')

    appraisal_type = fields.Selection([
        ('employee', 'By Employee'),
        ('company', 'By Company'),
        ('department', 'By Department')],
        string='Appraisal Mode', readonly=False, required=True, default='employee')

    appraisal_batch_id = fields.Many2one('appraisal.batches', string='Appraisal Batch')

    appointment_date = fields.Date(related='employee_id.appointment_date', string='Appointment Date')
    registration_number = fields.Char(related='employee_id.registration_number', string='Registration Number')
    cl_count = fields.Float('Casual leave availed', compute='_leaves_count')
    sl_count = fields.Float('Sick leave availed', compute='_leaves_count')
    pl_count = fields.Float('Paid leave availed', compute='_leaves_count')
    earned_leaves_balance = fields.Float('Earned leave Balance')
    increase_percentage = fields.Float(string='Increment (%)', group_operator=False)

    future_project = fields.Char(string='Future Project')
    is_first_manager = fields.Boolean(compute="_compute_is_first_manager")
    # remarks = fields.Text()
    appraisal_employee_id = fields.Many2one('res.users', string="Appraisal Employee")
    last_approver_id = fields.Many2one('res.users', string='Last Approver')
    revert_remarks = fields.Char()
    remarks_text = fields.Char()
    remarks = fields.One2many('hr.appraisal.remarks', 'appraisal_id', string='Remarks')
    doc_state = fields.Selection([
        ('draft', 'Draft'),
        ('save', 'Save'),
        ('done', 'Done'), ('revert', 'Revert'), ('publish', 'Publish')], default='draft'
    )

    def _compute_is_first_manager(self):
        for rec in self:
            current_user = rec.env.user
            managers = rec._manager_users_ordered()

            # No manager? nothing editable
            if not managers:
                rec.is_first_manager = False
                continue

            # First manager in hierarchy
            first_manager = managers[0]

            rec.is_first_manager = (current_user == first_manager)

    # Already in your model:
    # manager_ids = Many2many()
    # recomm_increment_lines_id = One2many()

    # --------------------------------------------------------------------
    # HELPERS
    # --------------------------------------------------------------------

    def _manager_users_ordered(self):
        """Return ALL managers in hierarchy: employee → parent → ... → top."""
        for rec in self:
            managers = []
            emp = rec.employee_id

            # Walk upward in the hierarchy
            while emp.parent_id:
                manager = emp.parent_id
                if manager.user_id:
                    managers.append(manager.user_id)
                emp = manager  # go one level up

            return managers

    def _next_manager(self, current_user):
        """Return next manager user after current approver."""
        managers = self._manager_users_ordered()
        if current_user in managers:
            index = managers.index(current_user)
            if index + 1 < len(managers):
                return managers[index + 1]
        return False  # no next manager → MD stage

    # changing state
    @api.onchange('state')
    def onchange_state(self):
        if self.state:
            self.doc_state = 'draft'

    # --------------------------------------------------------------------
    # Compute Dynamic States
    # --------------------------------------------------------------------

    def _compute_dynamic_state(self, is_hr=False, is_md=False):
        '''set dynamic state based on hirarechy in every hirearchy 1st manager is line manager
         and 2nd manager from till 2nd last manager the state is in manager but on 2nd last manager the state is executive and for last manager the state is md'''
        for rec in self:
            managers = rec._manager_users_ordered()
            if not managers:
                rec.state = 'draft'
                return rec.state
            if is_hr == True:
                rec.state = 'new'
                return rec.state
            if not rec.current_approver_id or rec.current_approver_id not in managers:
                rec.state = 'draft'
                continue

            total = len(managers)
            idx = managers.index(rec.current_approver_id)

            # 1st manager → Line Manager
            if idx == 0:
                rec.state = 'new'

            # middle managers → Manager Review
            elif 1 <= idx <= (total - 3):
                rec.state = 'pending'

            # 2nd-last manager → Executive Review
            elif idx == (total - 2):
                rec.state = 'executive'

            # last manager → MD Review
            elif idx == (total - 1) and is_md == True:
                rec.state = 'md'

            else:
                rec.state = 'draft'

    # --------------------------------------------------------------------
    # BUTTON: HR STARTS WORKFLOW
    # --------------------------------------------------------------------
    def action_hr_confirm(self):
        for rec in self:
            rec.doc_state = 'draft'
            if not rec.manager_ids:
                raise ValidationError("Please assign managers first.")
            if rec._manager_users_ordered():
                first_manager = rec._manager_users_ordered()[0]
                # state = rec._compute_dynamic_state(is_hr=True)
                rec.write({
                    'state': 'new',
                    'current_approver_id': first_manager.id,
                })
            else:
                raise ValidationError("Please assign managers With Users first.")
    # --------------------------------------------------------------------
    # CHECKING: MD USER
    # --------------------------------------------------------------------

    def _is_md(self, user):
        """MD = employee whose parent_id is False."""
        emp = self.env['hr.employee'].sudo().search([('user_id', '=', user.id)], limit=1)
        return emp and not emp.parent_id

    def _is_executive(self, user):
        """Return True if employee is Executive.
        Executive = employee has a parent but parent has no parent.
        """

        employee = self.env['hr.employee'].sudo().search([
            ('user_id', '=', user.id)
        ], limit=1)

        if not employee:
            return False

        if not employee.parent_id:
            return False

        if employee.parent_id.parent_id:
            return False

        return True

    # --------------------------------------------------------------------
    # BUTTON: MANAGER SUBMIT
    # --------------------------------------------------------------------
    def action_manager_submit(self):

        for rec in self:
            rec.doc_state = 'draft'

            login_user = rec.env.user

            if login_user != rec.current_approver_id:
                raise ValidationError("You are not assigned to approve this stage.")

            # Save increment for this manager
            rec._save_increment_for_manager(login_user)

            # Get next manager user
            next_manager = rec._next_manager(login_user)
            # state = rec._compute_dynamic_state()

            if next_manager:
                # --- NEW FIX: Check if next manager is MD ---
                if rec._is_md(next_manager):
                    rec.write({
                        'state': 'md',
                        'last_approver_id': rec.current_approver_id.id,  # MD stage
                        'current_approver_id': next_manager.id,
                    })
                elif rec._is_executive(next_manager):
                    rec.write({
                        'state': 'executive',  # MD stage
                        'last_approver_id': rec.current_approver_id.id,  # MD stage
                        'current_approver_id': next_manager.id,
                    })

                else:
                    rec.last_approver_id = rec.current_approver_id

                    # rec._compute_dynamic_state()
                    rec.write({
                        'state': 'pending',
                        'current_approver_id': next_manager.id,
                    })

            else:
                # No next manager → MD stage
                md_user = rec._get_md_user(next_manager)
                # md_state = rec._compute_dynamic_state(is_md=True)
                rec.write({
                    'state': 'md',
                    'last_approver_id': rec.current_approver_id.id,  # MD stage
                    'current_approver_id': next_manager.id,
                })

    # --------------------------------------------------------------------
    # BUTTON: MD FINAL SUBMIT
    # --------------------------------------------------------------------
    def action_md_submit(self):
        for rec in self:
            rec.doc_state = 'draft'

            login_user = rec.env.user
            if login_user != rec.current_approver_id:
                raise ValidationError("Only MD can submit this stage.")

            rec._save_increment_for_manager(login_user)

            rec.write({
                'state': 'done',
                'current_approver_id': False,
            })

            # Final increment
            final_inc = rec.recomm_increment_lines_id[-1].increment_raise_amount
            rec.recomm_increment = final_inc

            # Gross salary update

            # # Update employee wage
            # if rec.employee_id.contract_id:
            #     new_wage = rec.employee_id.contract_id.wage + final_inc
            #     rec.gross_salary = new_wage
            #     rec.employee_id.contract_id.write({'wage': new_wage})
            for remark in self.remarks:
                rec._append_manager_remark(remark.remark_text)

        return {
            'effect': {
                'fadeout': 'slow',
                'message': 'Appraisal Completed Successfully!',
                'type': 'rainbow_man',
            }
        }

    # --------------------------------------------------------------------
    # BUTTON: HR PUBLISHED
    # --------------------------------------------------------------------
    def action_hr_published(self):
        for rec in self:
            if rec.state == 'done':
                if rec.employee_id.contract_id:
                    if rec.employee_id.user_id:
                        new_wage = rec.employee_id.contract_id.wage + rec.recomm_increment
                        rec.gross_salary = new_wage
                        rec.employee_id.contract_id.write({'wage': new_wage})
                        rec.appraisal_employee_id = rec.employee_id.user_id.id
                        rec.state = 'published'
                        rec.doc_state = 'publish'
                    else:
                        raise ValidationError("You are not assigned user to employee.")

    # --------------------------------------------------------------------
    # Save Increment Helper
    # --------------------------------------------------------------------
    def _save_increment_for_manager(self, user):
        """Every manager must have one increment line.
        If manager did not enter one, auto copy previous."""
        for rec in self:

            existing = rec.recomm_increment_lines_id.filtered(
                lambda l: l.increment_raise_by == user
            )

            if existing:
                return  # manager already submitted

            # No line → auto copy previous
            prev = rec.recomm_increment_lines_id[-1] if rec.recomm_increment_lines_id else False

            rec.recomm_increment_lines_id = [(0, 0, {
                'increment_raise_amount': prev.increment_raise_amount if prev else 0,
                'recomm_desigantion_id': prev.recomm_desigantion_id.id if prev else False,
                'recomm_grades': prev.recomm_grades if prev else "",
                'increment_raise_by': user.id,
                'incremented_date': fields.Datetime.now(),
                'state': rec.state,
            })]
            rec.doc_state = 'save'
    # --------------------------------------------------------------------
    # Identify MD User
    # --------------------------------------------------------------------

    def _get_md_user(self, user):
        """MD = employee whose parent_id is False."""
        emp = self.env['hr.employee'].sudo().search([('user_id', '=', user.id)], limit=1)
        if not emp.parent_id:
            return emp
        else:
            False

    # --------------------------------------------------------------------
    # PORTAL MANAGER SUBMIT (CALLED FROM CONTROLLER)
    # --------------------------------------------------------------------
    def _portal_submit_manager(self, vals_increment_line=False):
        """
        Called from portal controller when a manager submits appraisal.
        It saves increment (if provided) and triggers action_manager_submit().
        """

        user = self.env.user
        existing = self.recomm_increment_lines_id.filtered(
            lambda l: l.increment_raise_by.id == user.id
        )
        # --- Save increment submitted from portal ---
        if vals_increment_line:
            if self.doc_state == 'revert':
                existing.write({
                    "increment_raise_amount": float(vals_increment_line.get("increment_raise_amount") or 0),
                    "recomm_desigantion_id": int(vals_increment_line.get("recomm_desigantion_id") or 0),
                    "recomm_grades": vals_increment_line.get("recomm_grades") or "",
                })

            # Check if manager already has a line
            existing = self.recomm_increment_lines_id.filtered(
                lambda l: l.increment_raise_by.id == user.id
            )
            if not existing:
                self.recomm_increment_lines_id = [(0, 0, {
                    "increment_raise_amount": float(vals_increment_line.get("increment_raise_amount") or 0),
                    "recomm_desigantion_id": int(vals_increment_line.get("recomm_desigantion_id") or 0),
                    "recomm_grades": vals_increment_line.get("recomm_grades") or "",
                    "increment_raise_by": user.id,
                    "incremented_date": fields.Datetime.now(),
                    "state": self.state,
                })]
        else:
            # Manager didn't add increment → auto copy previous
            self._save_increment_for_manager(user)

        self.doc_state = 'done'
        # trigger backend internal workflow
        return self.action_manager_submit()

    # --------------------------------------------------------------------
    # PORTAL REVERT BACK (CALLED FROM CONTROLLER)
    # --------------------------------------------------------------------
    def action_revert_back(self, revert_remarks):
        managers = self._manager_users_ordered()  # Get the full hierarchy of managers

        if self.state == 'md':
            self.write({
                'state': 'executive',
                'current_approver_id': self.last_approver_id.id

            })
        elif self.state == 'executive':
            self.write({
                'state': 'pending',
                'current_approver_id': self.last_approver_id.id

            })
        elif self.state == 'pending':
            manager_index = managers.index(self.last_approver_id)

            if manager_index == 0:
                self.write({
                    'state': 'new',
                    'current_approver_id': self.last_approver_id.id
                })
            else:
                self.write({
                    'state': 'pending',
                    'current_approver_id': self.last_approver_id.id

                })
            # self._append_revert_remark(revert_remarks)
            manager_uid = self.recomm_increment_lines_id.filtered(
                lambda x: x.create_uid.id == self.current_approver_id.id)
            if manager_uid:
                manager_uid.check_access_team_id = True
        self.doc_state = 'revert'

    # --------------------------------------------------------------------
    # PORTAL MD SUBMIT (CALLED FROM CONTROLLER)
    # --------------------------------------------------------------------
    def _portal_submit_md(self, vals_increment_line=False):
        """
        MD final submission from portal.
        Saves increment if provided then triggers action_md_submit().
        """
        self.doc_state = 'done'

        user = self.env.user

        # --- Save increment submitted from MD ---
        if vals_increment_line:
            existing = self.recomm_increment_lines_id.filtered(
                lambda l: l.increment_raise_by.id == user.id
            )
            if not existing:
                self.recomm_increment_lines_id = [(0, 0, {
                    "increment_raise_amount": float(vals_increment_line.get("increment_raise_amount") or 0),
                    "recomm_desigantion_id": int(vals_increment_line.get("recomm_desigantion_id") or 0),
                    "recomm_grades": vals_increment_line.get("recomm_grades") or "",
                    "increment_raise_by": user.id,
                    "incremented_date": fields.Datetime.now(),
                    "state": self.state,
                })]
        else:
            # MD did not write increment → auto copy previous
            self._save_increment_for_manager(user)

        self.doc_state = 'done'
        # call final backend MD submit action
        return self.action_md_submit()

    # --------------------------------------------------------------------
    # EMPLOYEE LEAVE COUNT
    # pl = paid leaves , cl = casual leaves , sl = sick leave
    # --------------------------------------------------------------------
    # @api.depends('employee_id')
    # def _leaves_count(self):
    #     current_year = datetime.now().year
    #
    #     for emp in self.employee_id:
    #         if emp:
    #             casual_work_entry_type = self.env['hr.work.entry.type'].search([('name', '=', 'Casual Time Off')])
    #             sick_work_entry_type = self.env['hr.work.entry.type'].search([('name', '=', 'Sick Time Off')])
    #             pl_work_entry_type = self.env['hr.work.entry.type'].search([('name', '=', 'PL Leaves')])
    #
    #             casual_leave_type = self.env['hr.leave.type'].search(
    #                 [('work_entry_type_id', '=', casual_work_entry_type.id)])
    #             sick_leave_type = self.env['hr.leave.type'].search(
    #                 [('work_entry_type_id', '=', sick_work_entry_type.id)])
    #             pl_work_type = self.env['hr.leave.type'].search([('work_entry_type_id', '=', pl_work_entry_type.id)])
    #
    #             cl_leave_allocate = self.env['hr.leave.allocation'].search(
    #                 [('holiday_status_id', 'in', casual_leave_type.ids), ('state', '=', 'validate'),
    #                  ('employee_id', '=', emp.id)])
    #             sick_leave_allocate = self.env['hr.leave.allocation'].search(
    #                 [('holiday_status_id', 'in', sick_leave_type.ids), ('state', '=', 'validate'),
    #                  ('employee_id', '=', emp.id)])
    #             pl_leave_allocate = self.env['hr.leave.allocation'].search(
    #                 [('holiday_status_id', 'in', pl_work_type.ids), ('state', '=', 'validate'),
    #                  ('employee_id', '=', emp.id)])
    #
    #             cl_leave_allocate = cl_leave_allocate.filtered(
    #                 lambda a: a.date_from and a.date_to and
    #                           a.date_from.year <= current_year <= a.date_to.year
    #             )
    #
    #             sick_leave_allocate = sick_leave_allocate.filtered(
    #                 lambda a: a.date_from and a.date_to and
    #                           a.date_from.year <= current_year <= a.date_to.year
    #             )
    #
    #             pl_leave_allocate = pl_leave_allocate.filtered(
    #                 lambda a: a.date_from and a.date_to and
    #                           a.date_from.year <= current_year <= a.date_to.year
    #             )
    #             cl_leave_availed = sum(self.env['hr.leave'].search(
    #                 [('holiday_status_id', '=', casual_leave_type.id), ('employee_id', '=', emp.id),
    #                  ('state', '=', 'validate')]).filtered(
    #                 lambda a: a.date_from and a.date_to and
    #                           (a.date_from.year <= current_year <= a.date_to.year)
    #             ).mapped('number_of_days'))
    #             sl_leave_availed = sum(self.env['hr.leave'].search(
    #                 [('holiday_status_id', '=', sick_leave_type.id), ('employee_id', '=', emp.id),
    #                  ('state', '=', 'validate')]).filtered(
    #                 lambda a: a.date_from and a.date_to and
    #                           (a.date_from.year <= current_year <= a.date_to.year)
    #             ).mapped('number_of_days'))
    #
    #             self.cl_count = cl_leave_availed
    #             self.sl_count = sl_leave_availed
    #             self.pl_count = pl_leave_allocate.number_of_days
    #         else:
    #             self.cl_count = 0
    #             self.sl_count = 0
    #             self.pl_count = 0
    from datetime import datetime

    @api.depends('employee_id')
    def _leaves_count(self):
        current_year = datetime.now().year
        if self.employee_id:
           for emp in self.employee_id:
            if emp:
                casual_work_entry_type = self.env['hr.work.entry.type'].search([('name', '=', 'Casual Time Off')],
                                                                               limit=1)
                sick_work_entry_type = self.env['hr.work.entry.type'].search([('name', '=', 'Sick Time Off')], limit=1)
                pl_work_entry_type = self.env['hr.work.entry.type'].search([('name', '=', 'PL Leaves')], limit=1)

                casual_leave_type = self.env['hr.leave.type'].search(
                    [('work_entry_type_id', '=', casual_work_entry_type.id)])
                sick_leave_type = self.env['hr.leave.type'].search(
                    [('work_entry_type_id', '=', sick_work_entry_type.id)])
                pl_leave_type = self.env['hr.leave.type'].search([('work_entry_type_id', '=', pl_work_entry_type.id)])

                # cl_leave_allocate = self.env['hr.leave.allocation'].search([
                #     ('holiday_status_id', '=', casual_leave_type.id),
                #     ('state', '=', 'validate'),
                #     ('employee_id', '=', emp.id)
                # ])
                # sick_leave_allocate = self.env['hr.leave.allocation'].search([
                #     ('holiday_status_id', '=', sick_leave_type.id),
                #     ('state', '=', 'validate'),
                #     ('employee_id', '=', emp.id)
                # ])
                for pl_leave_type in pl_leave_type:
                    pl_leave_allocate = self.env['hr.leave.allocation'].search([
                        ('holiday_status_id', '=', pl_leave_type.id),
                        ('state', '=', 'validate'),
                        ('employee_id', '=', emp.id),

                               ])
                    pl_leave_allocate = pl_leave_allocate.filtered(
                        lambda a: a.date_from and a.date_to and
                                  a.date_from.year <= current_year <= a.date_to.year
                    )

                    pl_count = sum(a.number_of_days for a in pl_leave_allocate)



                cl_availed_days = self._calculate_availed_leave(emp, casual_leave_type)
                sl_availed_days = self._calculate_availed_leave(emp, sick_leave_type)
                pl_availed_days = self._calculate_availed_leave(emp, pl_leave_type)

                self.cl_count = cl_availed_days
                self.sl_count = sl_availed_days

                self.sudo().write({
                    'cl_count':cl_availed_days,
                    'sl_count' :sl_availed_days,
                    'pl_count':pl_count,
                    'earned_leaves_balance': pl_count - pl_availed_days
                })

            else:
                self.cl_count = 0
                self.sl_count = 0
                self.pl_count = 0
                self.earned_leaves_balance = 0
        else:
            self.cl_count = 0
            self.sl_count = 0
            self.pl_count = 0
            self.earned_leaves_balance = 0

    def _calculate_availed_leave(self, emp, casual_leave_type):
        availed_days = 0
        for casual_leave_type in casual_leave_type:
            work_entries = self.env['hr.leave'].search([
                ('employee_id', '=', emp.id),
                ('holiday_status_id', '=', casual_leave_type.id)
            ])

            availed_days += sum(entry.number_of_days for entry in work_entries)

        return availed_days

    # --------------------------------------------------------------------
    # DYNAMIC REMARKS
    # --------------------------------------------------------------------
    #
    def _append_manager_remark(self, remark_text):
        if self.doc_state == 'revert':
            self.sudo().remarks.write({
                'appraisal_id': self.id,
                'remark_text': remark_text,
            })
        else:
            self.sudo().remarks.create({
            'appraisal_id': self.id,
            'remark_text': remark_text,
        })
        self.doc_state = 'save'


    def _append_line_manager_prospect(self, future_prospect):
        user = self.env.user
        now = fields.Datetime.now()
        timestamp = now.strftime("%d %B %Y, %I:%M %p")
        new_entry = f"{future_prospect}\nBy{user.name} [{timestamp}]:\n\n"
        self.doc_state = 'save'

        self.future_project = (self.future_project or "") + new_entry

    def _append_revert_remark(self, revert_remark_text):
        user = self.env.user
        now = fields.Datetime.now()
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
        new_entry = f"[{timestamp}] {user.name}:\n{revert_remark_text}\n\n"

        self.revert_remarks = (self.revert_remarks or "") + new_entry

    @api.depends('employee_id')
    def _compute_gross_salary(self):
        for rec in self:
            if rec.employee_id:
                if rec.employee_id.contract_id:
                    rec.gross_salary = rec.employee_id.contract_id.wage
                else:
                    rec.gross_salary = 0
            else:
                rec.gross_salary = 0

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env["hr.appraisal"].browse(docids)

        # Build the values your template expects
        appraisal_history = self._prepare_appraisal_history(docs)
        form = self._prepare_form_values(docs)
        company = docs.company_id.name

        return {
            'doc_ids': docids,
            'doc_model': 'hr.appraisal',
            'docs': docs,
            'company': company,
            'appraisal_history': appraisal_history,
            'form': form,
        }

    def _get_report_base_filename(self):
        self.ensure_one()
        return "Appraisal_Letter_%s" % (self.employee_id.name.replace(" ", "_"))


    def action_hr_assigned_batch(self):
        today = date.today()
        bacth_id = self.env['appraisal.batches'].search([( 'date_start', '<=' ,today),( 'date_end', '>=' ,today)])
        if not bacth_id:
            raise UserError("No appraisal batch is valid for today's date.")
        if len(bacth_id) > 1:
            batch_names = ", ".join(bacth_id.mapped('name'))
            raise UserError(
                "Multiple appraisal batches match today's date:\n\n%s\n\n"
                "Only one batch is allowed for a date range." % batch_names
            )
        for rec in self:
            # find all batches where today lies between start & end date

            # Exactly one batch found → Assign
            rec.appraisal_batch_id = bacth_id.id


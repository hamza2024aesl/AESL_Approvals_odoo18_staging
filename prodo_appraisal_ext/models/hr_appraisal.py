# ---------------------------------------------------------
# DYNAMIC APPRAISAL WORKFLOW – FINAL VERSION
# ---------------------------------------------------------

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
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
    ], default='draft', tracking=True)

    current_approver_id = fields.Many2one('res.users', string="Current Approver")
    recomm_increment = fields.Float("Final Increment")
    gross_salary = fields.Float("Gross Salary")

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
    cl_count = fields.Float('Casual leave availed',compute='_leaves_count')
    sl_count = fields.Float('Sick leave availed', compute='_leaves_count')
    pl_count = fields.Float('Paid leave availed', compute='_leaves_count')
    earned_leaves_balance = fields.Float('Earned leave Balance')
    increase_percentage = fields.Float(string='Increment (%)', group_operator=False)

    future_project = fields.Char(string='Future Project')
    is_first_manager = fields.Boolean(compute="_compute_is_first_manager")
    remarks = fields.Text()

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

    # --------------------------------------------------------------------
    # Compute Dynamic States
    # --------------------------------------------------------------------

    def _compute_dynamic_state(self,is_hr=False,is_md=False):
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
            if not rec.manager_ids:
                raise ValidationError("Please assign managers first.")

            first_manager = rec._manager_users_ordered()[0]
            # state = rec._compute_dynamic_state(is_hr=True)
            rec.write({
                'state': 'new',
                'current_approver_id': first_manager.id,
            })
        return True

    # --------------------------------------------------------------------
    # CHECKING: MD USER
    # --------------------------------------------------------------------

    def _is_md(self, user):
        """MD = employee whose parent_id is False."""
        emp = self.env['hr.employee'].sudo().search([('user_id', '=', user.id)], limit=1)
        return emp and not emp.parent_id

    # --------------------------------------------------------------------
    # BUTTON: MANAGER SUBMIT
    # --------------------------------------------------------------------
    def action_manager_submit(self):
        for rec in self:

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
                        'state': 'md',  # MD stage
                        'current_approver_id': next_manager.id,
                    })
                else:
                    # rec._compute_dynamic_state()
                    rec.write({
                        'state':'pending',
                        'current_approver_id': next_manager.id,
                    })

            else:
                # No next manager → MD stage
                md_user = rec._get_md_user(next_manager)
                # md_state = rec._compute_dynamic_state(is_md=True)
                rec.write({
                    'state': 'md',
                    'current_approver_id': md_user.id,
                })

    # --------------------------------------------------------------------
    # BUTTON: MD FINAL SUBMIT
    # --------------------------------------------------------------------
    def action_md_submit(self):
        for rec in self:

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
            rec.gross_salary = rec.gross_salary + final_inc

            # Update employee wage
            if rec.employee_id.contract_id:
                new_wage = rec.employee_id.contract_id.wage + final_inc
                rec.employee_id.contract_id.write({'wage': new_wage})

            # rec._compute_dynamic_state()


        return {
            'effect': {
                'fadeout': 'slow',
                'message': 'Appraisal Completed Successfully!',
                'type': 'rainbow_man',
            }
        }

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

        # --- Save increment submitted from portal ---
        if vals_increment_line:
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

        # trigger backend internal workflow
        return self.action_manager_submit()

    # --------------------------------------------------------------------
    # PORTAL MD SUBMIT (CALLED FROM CONTROLLER)
    # --------------------------------------------------------------------
    def _portal_submit_md(self, vals_increment_line=False):
        """
        MD final submission from portal.
        Saves increment if provided then triggers action_md_submit().
        """

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

        # call final backend MD submit action
        return self.action_md_submit()

    # --------------------------------------------------------------------
    # EMPLOYEE LEAVE COUNT
    # pl = paid leaves , cl = casual leaves , sl = sick leave
    # --------------------------------------------------------------------
    @api.depends('employee_id')
    def _leaves_count(self):
        current_year = datetime.now().year

        for emp in self.employee_id:
            casual_work_entry_type = self.env['hr.work.entry.type'].search([('name', '=', 'Casual Time Off')])
            sick_work_entry_type = self.env['hr.work.entry.type'].search([('name', '=', 'Sick Time Off')])
            pl_work_entry_type = self.env['hr.work.entry.type'].search([('name', '=', 'PL Leaves')])

            casual_leave_type = self.env['hr.leave.type'].search(
                [('work_entry_type_id', '=', casual_work_entry_type.id)])
            sick_leave_type = self.env['hr.leave.type'].search([('work_entry_type_id', '=', sick_work_entry_type.id)])
            pl_work_type = self.env['hr.leave.type'].search([('work_entry_type_id', '=', pl_work_entry_type.id)])

            cl_leave_allocate = self.env['hr.leave.allocation'].search(
                [('holiday_status_id', 'in', casual_leave_type.ids), ('state', '=', 'validate'),
                 ('employee_id', '=', emp.id)])
            sick_leave_allocate = self.env['hr.leave.allocation'].search(
                [('holiday_status_id', 'in', sick_leave_type.ids), ('state', '=', 'validate'),
                 ('employee_id', '=', emp.id)])
            pl_leave_allocate = self.env['hr.leave.allocation'].search(
                [('holiday_status_id', 'in', pl_work_type.ids), ('state', '=', 'validate'),
                 ('employee_id', '=', emp.id)])

            cl_leave_allocate = cl_leave_allocate.filtered(
                lambda a: a.date_from and a.date_to and
                          a.date_from.year <= current_year <= a.date_to.year
            )

            sick_leave_allocate = sick_leave_allocate.filtered(
                lambda a: a.date_from and a.date_to and
                          a.date_from.year <= current_year <= a.date_to.year
            )

            pl_leave_allocate = pl_leave_allocate.filtered(
                lambda a: a.date_from and a.date_to and
                          a.date_from.year <= current_year <= a.date_to.year
            )

            self.cl_count = cl_leave_allocate.number_of_days
            self.sl_count = sick_leave_allocate.number_of_days
            self.pl_count = pl_leave_allocate.number_of_days

    # --------------------------------------------------------------------
    # DYNAMIC REMARKS
    # --------------------------------------------------------------------

    def _append_manager_remark(self, remark_text):
        user = self.env.user
        now = fields.Datetime.now()
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
        new_entry = f"[{timestamp}] {user.name}:\n{remark_text}\n\n"

        self.remarks = (self.remarks or "") + new_entry

    def _append_line_manager_prospect(self, future_prospect):
        user = self.env.user
        now = fields.Datetime.now()
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
        new_entry = f"[{timestamp}] {user.name}:\n{future_prospect}\n\n"

        self.future_project = (self.future_project or "") + new_entry

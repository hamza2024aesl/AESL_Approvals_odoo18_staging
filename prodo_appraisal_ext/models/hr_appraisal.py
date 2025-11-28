# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import date, datetime, time
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError

class HrAppraisal(models.Model):
    _inherit = 'hr.appraisal'
    _description = 'Appraisal System Batch'

    appraisal_batch_id = fields.Many2one('appraisal.batch', string='Appraisal Batch')
    recomm_increment_lines_id = fields.One2many('increment.raise.lines', 'increment_raise_id',
                                                string='Increase Recommended Lines',
                                                required=True, index=True, ondelete='cascade')

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

    doc_state = fields.Selection([
        ('draft', 'Draft'),
        ('save', 'Save'),
        ('done', 'Done'), ('revert', 'Revert'), ('publish', 'Publish')], default='draft')
    appraisal_last_approver_id = fields.Many2one('res.users', string='Last Approver Name')
    appraisal_approver_id = fields.Many2one('res.users', string='Approver Name')
    manager_ids = fields.Many2many(
        'hr.employee',
        'hr_appraisal_manager_rel',
        'hr_appraisal_id',
        'manager_id',
        string='Managers',
        store = True
    )
    name_of_reporting_officer = fields.Many2one('res.users', string='Reporting Officer')
    ro_submit_date = fields.Date("RO Submit Date")
    last_state = fields.Char()
    is_md_state = fields.Boolean(default=False)
    is_manager = fields.Boolean(default=False)
    is_manager2 = fields.Boolean(default=False)
    is_manager3 = fields.Boolean(default=False)
    is_hr_confirm = fields.Boolean(default=False)
    is_exec_state = fields.Boolean(default=False)
    countersignedby_name = fields.Many2one('res.users', string='Countersigned By')
    countersignature_date = fields.Date("Countersignature Date")
    recomm_increment = fields.Float('Increase Recommended?', tracking=True)
    emp_type = fields.Char()

    # remarks
    remarks = fields.Text('Remarks:', size=10)
    remarks_2 = fields.Text('Remarks', size=10)
    remarks_3 = fields.Text('Remarks', size=50)
    remarks_4 = fields.Text('Remarks', size=50)
    remarks_5 = fields.Text('Remarks', size=50)

    appraisal_type = fields.Selection([
        ('employee', 'By Employee'),
        ('company', 'By Company'),
        ('department', 'By Department')],
        string='Appraisal Mode', readonly=False, required=True, default='employee')

    recommend_raise_amount = fields.Float(string="Recom. Increment")
    recommend_designation_id = fields.Many2one('hr.job', string='Designation')
    recommend_grades = fields.Integer(string='Recom. Grade', group_operator=False)


    # form view fields
    appointment_date = fields.Date(related='employee_id.appointment_date',string='Appointment Date')
    gross_salary = fields.Float(string='Gross Salary',compute='_compute_employee_details')
    registration_number = fields.Char(related='employee_id.registration_number',string='Registration Number')
    cl_count = fields.Float('Casual leave availed')
    sl_count = fields.Float('Sick leave availed')
    pl_count = fields.Float('Paid leave availed')
    earned_leaves_balance = fields.Float('Earned leave Balance')

    future_project = fields.Text('Future Prospect')
    accomplishment = fields.Text('Accomplishment')
    to_confirmation = fields.Selection([
        ('yes', 'YES'),
        ('no', 'NO')],
        string="To be Confirmed?", default="yes")
    increase_percentage = fields.Float(string='Increment (%)', group_operator=False)



    @api.depends('employee_id')
    def _compute_employee_details(self):
        for rec in self:
            self.gross_salary = rec.employee_id.contract_id.wage
            self._leaves_count()


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


    def _group_expand_states(self,stages, domain):
        return [key for key, val in self._fields['state'].selection]


    def check_anomynous_records_appraisal(self):
        appraisals = self.env['hr.appraisal'].search([('emp_type', 'not in', ['probation', 'permanent'])])
        for apr_rec in appraisals:
            if not (apr_rec.emp_type or apr_rec.registration_number):
                apr_rec.unlink()


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
                            'name': 'view.hr.appraisal.list',
                            'res_model': 'hr.appraisal',
                            'view_mode': 'list,form',
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
                                'name': 'view.hr.appraisal.list',
                                'res_model': 'hr.appraisal',
                                'view_mode': 'list,form',
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

        if login_user.has_group('prodo_appraisal_ext.group_hr_manager_appraisal_3'):
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
                managers_mail_template = self.env.ref('prodo_appraisal_ext.mail_template_request_appraisals_manager')
            elif appraisal_status in ['new', 'pending', 'pending2', 'pending3']:
                # managers_mail_template = appraisal.company_id.appraisal_confirm_manager_mail_template
                managers_mail_template = self.env.ref('prodo_appraisal_ext.mail_template_confirm_appraisals_manager')
            elif appraisal_status == 'cancel':
                managers_mail_template = self.env.ref('prodo_appraisal_ext.mail_template_appraisals_cancel_manager')
            elif appraisal_status == 'done':
                managers_mail_template = self.env.ref('prodo_appraisal_ext.mail_template_appraisals_done_manager')
            else:
                return
            for manager in self.manager_ids:
                if self.state == 'draft' or login_user.has_group(
                        'prodo_appraisal_ext.group_hr_manager_appraisal') or (login_user.id == 7):
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
                'url': '/mail/view?model=%s&res_id=%s' % ('hr.appraisal', appraisal.id),
            }
            RenderMixin = self.env['mail.render.mixin'].with_context(**ctx)
            subject = \
                RenderMixin._render_template(mail_template.subject, 'hr.appraisal', appraisal.ids,
                )[
                    appraisal.id]
            body = \
                RenderMixin._render_template(mail_template.body_html, 'hr.appraisal', appraisal.ids,
                )[
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
                    'QWeb template mail.mail_notification_light not found when sending appraisal confirmed mails. Sending without layouting.'
                )
                body = mail_values['body_html']  # fallback to plain message
            else:
                # Correct template context
                template_ctx = {
                    'message': self.env['mail.message'].sudo().new({
                        'body': mail_values['body_html'],
                        'record_name': employee.name
                    }),
                    'model_description': self.env['ir.model']._get('hr.appraisal').display_name,
                    'company': self.env.company,
                }

                # ✅ Proper QWeb rendering using ir.qweb environment
                body = self.env['ir.qweb']._render(template.id, template_ctx)

            # Replace local links and send mail
            mail_values['body_html'] = self.env['mail.render.mixin']._replace_local_links(body)
            self.env['mail.mail'].sudo().create(mail_values)

            # try:
            #     template = self.env.ref('mail.mail_notification_light', raise_if_not_found=True)
            # except ValueError:
            #     _logger.warning(
            #         'QWeb template mail.mail_notification_light not found when sending appraisal confirmed mails. Sending without layouting.')
            # else:
            #     template_ctx = {
            #         'message': self.env['mail.message'].sudo().new(
            #             dict(body=mail_values['body_html'], record_name=employee.name)),
            #         'model_description': self.env['ir.model']._get('hr.appraisal').display_name,
            #         'company': self.env.company,
            #     }
            #     body = template._render(template_ctx, engine='ir.qweb', minimal_qcontext=True)
            #     assignation_msg = self.env['ir.qweb']._render(template_ctx, values,
            #                                                   minimal_qcontext=True)
            #
            #     mail_values['body_html'] = self.env['mail.render.mixin']._replace_local_links(body)
            # self.env['mail.mail'].sudo().create(mail_values)

            # if employee.user_id:
            #     appraisal.activity_schedule(
            #         'mail.mail_activity_data_todo', appraisal.date_close,
            #         summary=_('Appraisal Form to Fill'),
            #         note=_('Fill appraisal for <a href="#" data-oe-model="%s" data-oe-id="%s">%s</a>') % (
            #             appraisal.employee_id._name, appraisal.employee_id.id, appraisal.employee_id.display_name),
            #         user_id=employee.user_id.id)

    def action_hr_confirm(self):
        for record in self:
            login_user = record.env['res.users'].browse(record.env.context.get('uid'))
            if login_user.has_group('prodo_appraisal_ext.group_hr_manager_appraisal_3') and record.state == 'draft':
                # record.send_appraisal()
                record.update({
                    'appraisal_approver_id': record.employee_id.parent_id.user_id,
                    'last_state': record.state,
                    'appraisal_last_approver_id': record.env.user.id,
                    'is_hr_confirm': True,
                    # 'state': 'new' if record.employee_id.parent_id.user_id.id != 408 else 'pending3'})
                    'state': 'new'
                })
        self.check_anomynous_records_appraisal

    def action_confirm(self):  # Line Manager Button Button
        self.doc_state = 'draft'
        current_state = self.state
        login_user = self.env['res.users'].browse(self.env.context.get('uid'))
        manager_user = self.env['res.users'].search([('id', '=', 414)])
        self.sudo().appraisal_last_approver_id = login_user
        manager = self.sudo().find_managers(self.sudo().employee_id)
        if len(self.manager_ids) <= 2:
            self.update({'is_md_state': True})
        elif len(self.manager_ids) <= 3:
            self.update({'is_exec_state': True})
        # if manager.get('manager1').user_id == login_user:
        if self.employee_id.parent_id.user_id == login_user:
            self.name_of_reporting_officer = login_user
            self.ro_submit_date = fields.Datetime.now()
            # if login_user.id == 663 or login_user.id == 626:
            if login_user.sudo().employee_id.parent_id.user_id.id == 414:
                self.last_state = self.state
                self.sudo().state = 'pending4'
                self.is_manager = True
                self.is_exec_state = True
                self.sudo().appraisal_approver_id = manager_user.id
                filtered_lines = self.sudo().recomm_increment_lines_id.filtered(
                    lambda line: line.increment_raise_by.id == login_user.id)
                if not filtered_lines:
                    self.recomm_increment_lines_id = [(0, 0, {
                        'increment_raise_amount': self.recomm_increment_lines_id[-1].increment_raise_amount,
                        'recomm_desigantion_id': self.recomm_increment_lines_id[-1].recomm_desigantion_id.id,
                        'recomm_grades': self.recomm_increment_lines_id[-1].recomm_grades,
                        'increment_raise_by': self.env.user.id,
                        # 'incremented_date': fields.Datetime.now().strftime('%a, %d-%b-%Y'),
                        'incremented_date': fields.Date.today(),
                        'state': current_state
                    })]
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'view.hr.appraisal.list',
                    'res_model': 'hr.appraisal',
                    'view_mode': 'list,form',
                    'domain': [],  # Optional: add any filters if needed
                    'context': {
                        'group_by': ['state', 'appraisal_approver_id'],  # Grouping fields
                    },
                    'target': 'current',  # Replaces the current view
                }
            elif len(self.manager_ids) == 2 or (
            (not (manager.get('manager3')) and (not manager.get('manager4')) and (not manager.get('manager5')))):
                self.last_state = self.state
                self.sudo().state = 'pending3'
                self.is_md_state = True
                self.sudo().appraisal_approver_id = self.sudo().employee_id.parent_id.parent_id.user_id
                filtered_lines = self.sudo().recomm_increment_lines_id.filtered(
                    lambda line: line.increment_raise_by.id == login_user.id)
                if not filtered_lines:
                    self.recomm_increment_lines_id = [(0, 0, {
                        'increment_raise_amount': self.recomm_increment_lines_id[-1].increment_raise_amount,
                        'recomm_desigantion_id': self.recomm_increment_lines_id[-1].recomm_desigantion_id.id,
                        'recomm_grades': self.recomm_increment_lines_id[-1].recomm_grades,
                        'increment_raise_by': self.env.user.id,
                        # 'incremented_date': fields.Datetime.now().strftime('%a, %d-%b-%Y'),
                        'incremented_date':fields.Date.today(),
                        'state': current_state
                    })]
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'view.hr.appraisal.list',
                    'res_model': 'hr.appraisal',
                    'view_mode': 'list,form',
                    'domain': [],  # Optional: add any filters if needed
                    'context': {
                        'group_by': ['state', 'appraisal_approver_id'],  # Grouping fields
                    },
                    'target': 'current',  # Replaces the current view
                }
            elif len(self.manager_ids) == 3:
                self.last_state = self.state
                self.sudo().state = 'pending4'
                self.is_exec_state = True
                self.sudo().appraisal_approver_id = self.sudo().employee_id.parent_id.parent_id.parent_id.user_id
                filtered_lines = self.sudo().recomm_increment_lines_id.filtered(
                    lambda line: line.increment_raise_by.id == login_user.id)
                if not filtered_lines:
                    self.recomm_increment_lines_id = [(0, 0, {
                        'increment_raise_amount': self.recomm_increment_lines_id[-1].increment_raise_amount,
                        'recomm_desigantion_id': self.recomm_increment_lines_id[-1].recomm_desigantion_id.id,
                        'recomm_grades': self.recomm_increment_lines_id[-1].recomm_grades,
                        'increment_raise_by': self.env.user.id,
                        # 'incremented_date': fields.Datetime.now().strftime('%a, %d-%b-%Y'),
                        'incremented_date': fields.Date.today(),
                        'state': current_state
                    })]
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'view.hr.appraisal.list',
                    'res_model': 'hr.appraisal',
                    'view_mode': 'list,form',
                    'domain': [],  # Optional: add any filters if needed
                    'context': {
                        'group_by': ['state', 'appraisal_approver_id'],  # Grouping fields
                    },
                    'target': 'current',  # Replaces the current view
                }
            elif len(self.manager_ids) == 4:
                self.last_state = self.state
                self.sudo().state = 'pending2'
                self.is_manager2 = True
                self.is_manager3 = True
                self.sudo().appraisal_approver_id = self.sudo().employee_id.parent_id.parent_id.user_id.id
                filtered_lines = self.sudo().recomm_increment_lines_id.filtered(
                    lambda line: line.increment_raise_by.id == login_user.id)
                if not filtered_lines:
                    self.recomm_increment_lines_id = [(0, 0, {
                        'increment_raise_amount': self.recomm_increment_lines_id[-1].increment_raise_amount,
                        'recomm_desigantion_id': self.recomm_increment_lines_id[-1].recomm_desigantion_id.id,
                        'recomm_grades': self.recomm_increment_lines_id[-1].recomm_grades,
                        'increment_raise_by': self.env.user.id,
                        # 'incremented_date': fields.Datetime.now().strftime('%a, %d-%b-%Y'),
                        'incremented_date': fields.Date.today(),
                        'state': current_state
                    })]
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'view.hr.appraisal.list',
                    'res_model': 'hr.appraisal',
                    'view_mode': 'list,form',
                    'domain': [],  # Optional: add any filters if needed
                    'context': {
                        'group_by': ['state', 'appraisal_approver_id'],  # Grouping fields
                    },
                    'target': 'current',  # Replaces the current view
                }
            else:
                self.sudo().write({
                    'last_state': self.state,
                    'state': 'pending',
                    'is_manager': True,
                    'is_manager2': True,
                })
                filtered_lines = self.sudo().recomm_increment_lines_id.filtered(
                    lambda line: line.increment_raise_by.id == login_user.id)
                if not filtered_lines:
                    self.recomm_increment_lines_id = [(0, 0, {
                        'increment_raise_amount': self.recomm_increment_lines_id[
                            -1].increment_raise_amount if self.recomm_increment_lines_id else 0,
                        'recomm_desigantion_id': self.recomm_increment_lines_id[
                            -1].recomm_desigantion_id.id if self.recomm_increment_lines_id else False,
                        'recomm_grades': self.recomm_increment_lines_id[
                            -1].recomm_grades if self.recomm_increment_lines_id else '',
                        'increment_raise_by': self.env.user.id,
                        # 'incremented_date': fields.Datetime.now().strftime('%a, %d-%b-%Y'),
                        'incremented_date': fields.Date.today(),
                        'state': current_state
                    })]
                # self.sudo().appraisal_approver_id = self.sudo().employee_id.parent_id.parent_id.user_id
                self.appraisal_approver_id = self.employee_id.parent_id.parent_id.user_id
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'My Appraisals',
                    'res_model': 'hr.appraisal',
                    'view_mode': 'list,form',
                    'domain': [('appraisal_approver_id', '=', self.env.user.id)],
                    'context': {
                        'group_by': ['state'],
                    },
                    'target': 'current',
                }

                # return {
                #     'type': 'ir.actions.act_window',
                #     'name': 'hr.appraisal.list',
                #     'res_model': 'hr.appraisal',
                #     'view_mode': 'list,form',
                #     'domain': [],  # Optional: add any filters if needed
                #     'context': {
                #         'group_by': ['state', 'appraisal_approver_id'],  # Grouping fields
                #     },
                #     'target': 'current',  # Replaces the current view
                # }
        else:
            raise ValidationError(_('Please let Mr. %s fill the form.') % self.employee_id.parent_id.user_id.name)

    def action_confirm2(self):  # Dept. Manager Button
        self.doc_state = 'draft'
        current_state = self.state
        login_user = self.env['res.users'].browse(self.env.context.get('uid'))
        manager = self.sudo().find_managers(self.sudo().employee_id)
        manager_user = self.env['res.users'].search([('id', '=', 414)])
        if len(self.sudo().manager_ids) <= 3:
            self.sudo().update({'is_md_state': True})
        elif len(self.sudo().manager_ids) <= 4:
            self.sudo().update({'is_exec_state': True})
        # if login_user.id == 663 or login_user.id == 626:
        if login_user.sudo().employee_id.parent_id.user_id.id == 414:
            self.sudo().last_state = self.state
            self.sudo().state = 'pending4'
            self.sudo().is_manager2 = True
            self.sudo().is_exec_state = True
            filtered_lines = self.sudo().recomm_increment_lines_id.filtered(
                lambda line: line.increment_raise_by.id == login_user.id)
            if not filtered_lines:
                self.recomm_increment_lines_id = [(0, 0, {
                    'increment_raise_amount': self.recomm_increment_lines_id[-1].increment_raise_amount,
                    'recomm_desigantion_id': self.recomm_increment_lines_id[-1].recomm_desigantion_id.id,
                    'recomm_grades': self.recomm_increment_lines_id[-1].recomm_grades,
                    'increment_raise_by': self.env.user.id,
                    # 'incremented_date': fields.Datetime.now().strftime('%a, %d-%b-%Y'),
                    'incremented_date': fields.Date.today(),
                    'state': current_state
                })]
            self.sudo().appraisal_approver_id = manager_user.id
            return {
                'type': 'ir.actions.act_window',
                'name': 'view.hr.appraisal.list',
                'res_model': 'hr.appraisal',
                'view_mode': 'list,form',
                'domain': [],  # Optional: add any filters if needed
                'context': {
                    'group_by': ['state', 'appraisal_approver_id'],  # Grouping fields
                },
                'target': 'current',  # Replaces the current view
            }

        elif self.sudo().employee_id.parent_id.parent_id.user_id == login_user:
            if not manager.get('manager4'):
                self.sudo().last_state = self.state
                self.sudo().state = 'pending3'
                self.is_md_state = True
                filtered_lines = self.sudo().recomm_increment_lines_id.filtered(
                    lambda line: line.increment_raise_by.id == login_user.id)
                if not filtered_lines:
                    self.recomm_increment_lines_id = [(0, 0, {
                        'increment_raise_amount': self.recomm_increment_lines_id[-1].increment_raise_amount,
                        'recomm_desigantion_id': self.recomm_increment_lines_id[-1].recomm_desigantion_id.id,
                        'recomm_grades': self.recomm_increment_lines_id[-1].recomm_grades,
                        'increment_raise_by': self.env.user.id,
                        # 'incremented_date': fields.Datetime.now().strftime('%a, %d-%b-%Y'),
                        'incremented_date': fields.Date.today(),
                        'state': current_state
                    })]
                self.sudo().appraisal_approver_id = self.sudo().employee_id.parent_id.parent_id.parent_id.user_id
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'view.hr.appraisal.list',
                    'res_model': 'hr.appraisal',
                    'view_mode': 'list,form',
                    'domain': [],  # Optional: add any filters if needed
                    'context': {
                        'group_by': ['state', 'appraisal_approver_id'],  # Grouping fields
                    },
                    'target': 'current',  # Replaces the current view
                }
            # self.activity_feedback(['mail.mail_activity_data_todo'])
            else:
                self.sudo().last_state = self.state
                self.sudo().state = 'pending2'
                self.sudo().is_manager3 = True
            filtered_lines = self.sudo().recomm_increment_lines_id.filtered(
                lambda line: line.increment_raise_by.id == login_user.id)
            if not filtered_lines:
                self.recomm_increment_lines_id = [(0, 0, {
                    'increment_raise_amount': self.recomm_increment_lines_id[-1].increment_raise_amount,
                    'recomm_desigantion_id': self.recomm_increment_lines_id[-1].recomm_desigantion_id.id,
                    'recomm_grades': self.recomm_increment_lines_id[-1].recomm_grades,
                    'increment_raise_by': self.env.user.id,
                    # 'incremented_date': fields.Datetime.now().strftime('%a, %d-%b-%Y'),
                    'incremented_date': fields.Date.today(),
                    'state': current_state
                })]
                self.sudo().appraisal_approver_id = self.sudo().employee_id.parent_id.parent_id.parent_id.user_id.id
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'view.hr.appraisal.list',
                    'res_model': 'hr.appraisal',
                    'view_mode': 'list,form',
                    'domain': [],  # Optional: add any filters if needed
                    'context': {
                        'group_by': ['state', 'appraisal_approver_id'],  # Grouping fields
                    },
                    'target': 'current',  # Replaces the current view
                }
            else:
                self.sudo().appraisal_approver_id = self.sudo().employee_id.parent_id.parent_id.parent_id.user_id.id
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'view.hr.appraisal.list',
                    'res_model': 'hr.appraisal',
                    'view_mode': 'list,form',
                    'domain': [],  # Optional: add any filters if needed
                    'context': {
                        'group_by': ['state', 'appraisal_approver_id'],  # Grouping fields
                    },
                    'target': 'current',  # Replaces the current view
                }
            # self.sudo().appraisal_last_approver_id = login_user.id
            # return {
            #     'type': 'ir.actions.act_window',
            #     'name': 'view.hr.appraisal.list',
            #     'res_model': 'hr.appraisal',
            #     'view_mode': 'list,form',
            #     'target': 'current',  # Replaces the current view
            # }

            # self.write({'state': 'pending2',
            #             'is_manager3': True

            # self.send_appraisal()
        else:
            raise ValidationError(
                _('Please let Mr. %s proceed the form.') % self.sudo().employee_id.parent_id.parent_id.user_id.name)

    def action_confirm4(self):  # Executive Button
        for rec in self:
            rec.doc_state = 'draft'
            current_state = rec.state
            login_user = self.env['res.users'].browse(rec.env.context.get('uid'))
            next_record = self.search([('id', '!=', self.id), ('appraisal_approver_id', '=', login_user.id)],
                                      order='id ASC') if len(self) == 1 else 0
            manager_user = self.env['res.users'].search([('id', '=', 408)])
            rec.appraisal_last_approver_id = login_user
            if login_user.id == 414:
                rec.last_state = rec.state
                rec.sudo().state = 'pending3'
                rec.is_exec_state = True
                # self.write({'state': 'pending3',
                #             'is_md_state': True})
                # self.sudo().send_appraisal()

                filtered_lines = rec.recomm_increment_lines_id.filtered(
                    lambda line: line.increment_raise_by.id == login_user.id)
                if not filtered_lines:
                    rec.recomm_increment_lines_id = [(0, 0, {
                        'increment_raise_amount': rec.recomm_increment_lines_id[-1].increment_raise_amount,
                        'recomm_desigantion_id': rec.recomm_increment_lines_id[-1].recomm_desigantion_id.id,
                        'recomm_grades': rec.recomm_increment_lines_id[-1].recomm_grades,
                        'increment_raise_by': rec.env.user.id,
                        # 'incremented_date': fields.Datetime.now().strftime('%a, %d-%b-%Y'),
                        'incremented_date': fields.Date.today(),
                        'state': current_state
                    })]

                rec.sudo().appraisal_approver_id = manager_user
                if len(self) == 1 and len(next_record) >= 1:
                    return {
                        'type': 'ir.actions.act_window',
                        'name': 'view.hr.appraisal.list',
                        'res_model': 'hr.appraisal',
                        'view_mode': 'form',
                        'domain': [],  # Optional: add any filters if needed
                        'context': {
                            'group_by': ['appraisal_approver_id'],  # Grouping fields
                        },
                        'res_id': next_record[0].id if next_record else '',
                        'target': 'current',  # Replaces the current view
                    }
                else:
                    if self[-1].id == rec.id:
                        return {
                            'type': 'ir.actions.act_window',
                            'name': 'view.hr.appraisal.list',
                            'res_model': 'hr.appraisal',
                            'view_mode': 'list,form',
                            'domain': [],  # Optional: add any filters if needed
                            'context': {
                                'group_by': ['appraisal_approver_id'],  # Grouping fields
                            },
                            'target': 'current',  # Replaces the current view
                        }
                    else:
                        pass

            else:
                raise ValidationError(_('Please let Mr. Ahad proceed the form.'))

    def action_confirm3(self):  # Director Button
        self.doc_state = 'draft'
        current_state = self.state
        login_user = self.env['res.users'].browse(self.env.context.get('uid'))
        manager_user = self.env['res.users'].search([('id', '=', 414)])
        # if (login_user.id == 663 or login_user.id == 626) and self.state == 'pending2':
        #     approver_manager = login_user
        # elif len(self.sudo().manager_ids) == 4:
        #     approver_manager = self.sudo().employee_id.parent_id.parent_id.user_id
        # else:
        #     approver_manager = self.sudo().employee_id.parent_id.parent_id.parent_id.user_id

        # if approver_manager == login_user or self.sudo().appraisal_approver_id == login_user:
        if self.sudo().appraisal_approver_id == login_user:
            # self.activity_feedback(['mail.mail_activity_data_todo'])
            # self.appraisal_approver_id =
            self.sudo().last_state = self.state
            self.sudo().state = 'pending4'
            self.sudo().is_manager3 = True
            # self.write({'state': 'pending4',
            #             'is_exec_state': True})
            # self.sudo().send_appraisal()

            filtered_lines = self.recomm_increment_lines_id.filtered(
                lambda line: line.increment_raise_by.id == login_user.id)
            if not filtered_lines:
                self.recomm_increment_lines_id = [(0, 0, {
                    'increment_raise_amount': self.recomm_increment_lines_id[-1].increment_raise_amount,
                    'recomm_desigantion_id': self.recomm_increment_lines_id[-1].recomm_desigantion_id.id,
                    'recomm_grades': self.recomm_increment_lines_id[-1].recomm_grades,
                    'increment_raise_by': self.env.user.id,
                    # 'incremented_date': fields.Datetime.now().strftime('%a, %d-%b-%Y'),
                    'incremented_date': fields.Date.today(),
                    'state': current_state
                })]
                self.appraisal_last_approver_id = login_user
                # if login_user.id == 663:
                if login_user.sudo().employee_id.parent_id.user_id.id == 414:
                    self.sudo().appraisal_approver_id = manager_user.id
                    return {
                        'type': 'ir.actions.act_window',
                        'name': 'view.hr.appraisal.list',
                        'res_model': 'hr.appraisal',
                        'view_mode': 'list,form',
                        'domain': [],  # Optional: add any filters if needed
                        'context': {
                            'group_by': ['state', 'appraisal_approver_id'],  # Grouping fields
                        },
                        'target': 'current',  # Replaces the current view
                    }
                else:
                    self.sudo().appraisal_approver_id = self.sudo().appraisal_approver_id.employee_id.parent_id.user_id.id
                    return {
                        'type': 'ir.actions.act_window',
                        'name': 'view.hr.appraisal.list',
                        'res_model': 'hr.appraisal',
                        'view_mode': 'list,form',
                        'domain': [],  # Optional: add any filters if needed
                        'context': {
                            'group_by': ['state', 'appraisal_approver_id'],  # Grouping fields
                        },
                        'target': 'current',  # Replaces the current view
                    }
            else:
                self.appraisal_last_approver_id = login_user
                # if login_user.id == 663:
                if login_user.sudo().employee_id.parent_id.user_id.id == 414:
                    self.sudo().appraisal_approver_id = manager_user.id
                    return {
                        'type': 'ir.actions.act_window',
                        'name': 'view.hr.appraisal.list',
                        'res_model': 'hr.appraisal',
                        'view_mode': 'list,form',
                        'domain': [],  # Optional: add any filters if needed
                        'context': {
                            'group_by': ['state', 'appraisal_approver_id'],  # Grouping fields
                        },
                        'target': 'current',  # Replaces the current view
                    }
                else:
                    self.sudo().appraisal_approver_id = self.sudo().appraisal_approver_id.employee_id.parent_id.user_id.id
                    return {
                        'type': 'ir.actions.act_window',
                        'name': 'view.hr.appraisal.list',
                        'res_model': 'hr.appraisal',
                        'view_mode': 'list,form',
                        'domain': [],  # Optional: add any filters if needed
                        'context': {
                            'group_by': ['state', 'appraisal_approver_id'],  # Grouping fields
                        },
                        'target': 'current',  # Replaces the current view
                    }
        else:
            raise ValidationError(_('Please let Mr. %s proceed the form.') % self.sudo().appraisal_approver_id.name)

    def action_done(self):
        for rec in self:
            rec.doc_state = 'done'
            current_state = rec.state
            login_user = self.env['res.users'].browse(rec.env.context.get('uid'))
            current_date =  date.today()
            rec.appraisal_last_approver_id = login_user
            # if login_user.id != 408:
            #     raise ValidationError(_('Mr.Syed Feisal Ali will complete/done the Appraisal.'))
            # else:
            rec.sudo().countersignedby_name = login_user
            rec.sudo().countersignature_date = fields.Datetime.now()
            rec.sudo().last_state = rec.state
            rec.sudo().state = 'done'
            filtered_lines = rec.sudo().recomm_increment_lines_id.filtered(
                lambda line: line.increment_raise_by.id == login_user.id)
            if not filtered_lines:
                rec.recomm_increment_lines_id = [(0, 0, {
                    'increment_raise_amount': rec.recomm_increment_lines_id[-1].increment_raise_amount,
                    'recomm_desigantion_id': rec.recomm_increment_lines_id[-1].recomm_desigantion_id.id,
                    'recomm_grades': rec.recomm_increment_lines_id[-1].recomm_grades,
                    'increment_raise_by': rec.env.user.id,
                    # 'incremented_date': fields.Datetime.now().strftime('%a, %d-%b-%Y'),
                    'incremented_date': fields.Date.today(),
                    'state': current_state
                })]
                rec.recomm_increment = rec.recomm_increment_lines_id[-1].increment_raise_amount
            rec.recomm_increment = rec.recomm_increment_lines_id[-1].increment_raise_amount
            rec.gross_salary += rec.recomm_increment
        return {
            'effect': {
                'fadeout': 'slow',
                'message': 'Everything is correctly Done...',
                'type': 'rainbow_man',
            }
        }

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
        Appraisal = self.env['hr.appraisal'].sudo()  # Use sudo to avoid recursive create calls
        if self.appraisal_type == 'employee' and self.employee_id:
            # Get the list of all parent managers for the selected employee
            manager_hierarchy = self._get_all_parents(self.employee_id)
            leaves_data = self._leaves_count()
            # Create a single appraisal for the selected employee
            Appraisal.create({
                # 'appraisal_run_ids': self.appraisal_run_ids.id,
                'employee_id': self.employee_id.id,
                'department_id': self.employee_id.department_id.id,
                # 'mode_company_id': self.employee_id.company_id.id,
                'company_id': self.employee_id.company_id.id,
                # 'education': self.employee_id.academic_ids[0].degree_id.name if self.employee_id.academic_ids else False,
                'manager_ids': [(6, 0, manager_hierarchy)],
                'registration_number': self.employee_id.registration_number,
                'grade': self.employee_id.x_studio_grade,
                'appointment_date': self.employee_id.appointment_date,
                # 'location': self.employee_id.location_id.emp_location,
                # 'birthday': self.employee_id.birthday,
                'gross_salary': self.employee_id.contract_id.wage,
                # 'personal_file_number': self.employee_id.x_studio_personal_file_number,
                # 'name_of_reporting_officer': self.employee_id.parent_id.name,
                'emp_type': self.employee_id.contract_id.contract_type_id.name,
                # 'cl_count': leaves_data.get("casual_leaves_count"),
                # 'sl_count': leaves_data.get("sick_leaves_count"),
                # 'earned_leaves_balance': leaves_data.get("earned_leaves_balance")
            })
        elif self.appraisal_type == 'department' and self.departments:
            # Get all employees in the selected department and create an appraisal for each
            employees = self.env['hr.employee'].search([('department_id', '=', self.departments.id)])
            for employee in employees:
                leaves_data = self._leaves_count()
                manager_hierarchy = self._get_all_parents(employee)
                Appraisal.create({
                    # 'appraisal_run_ids': self.appraisal_run_ids.id,
                    'employee_id': employee.id,
                    'department_id': employee.department_id.id,
                    'mode_company_id': employee.company_id.id,
                    'manager_ids': [(6, 0, manager_hierarchy)],
                    'registration_number': employee.registration_number,
                    # 'job_id': employee.employee_id.job_id.id,
                    # 'education': employee.academic_ids[0].degree_id.name if employee.academic_ids else False,
                    'grade': employee.x_studio_grade,
                    'appointment_date': employee.appointment_date,
                    # 'birthday': employee.birthday,
                    'gross_salary': employee.contract_id.wage,
                    # 'personal_file_number': employee.x_studio_personal_file_number,
                    # 'location': employee.location_id.emp_location,
                    # 'name_of_reporting_officer': employee.parent_id.name,
                    'emp_type': employee.contract_id.contract_type_id.name,
                    # 'cl_count': leaves_data.get("casual_leaves_count"),
                    # 'sl_count': leaves_data.get("sick_leaves_count"),
                    # 'earned_leaves_balance': leaves_data.get("earned_leaves_balance")
                })
        elif self.appraisal_type == 'company' and self.mode_company_id:
            # Get all employees in the company and create an appraisal for each
            employees = self.env['hr.employee'].search([('company_id', '=', self.mode_company_id.id)])
            for employee in employees:
                leaves_data = self._leaves_count()
                manager_hierarchy = self._get_all_parents(employee)
                Appraisal.create({
                    # 'appraisal_run_ids': self.appraisal_run_ids.id,
                    'employee_id': employee.id,
                    'department_id': employee.department_id.id,
                    'mode_company_id': employee.company_id.id,
                    'manager_ids': [(6, 0, manager_hierarchy)],
                    'registration_number': employee.registration_number,
                    # 'job_id': employee.employee_id.job_id.id,
                    # 'education': employee.academic_ids[0].degree_id.name if employee.academic_ids else False,
                    'grade': employee.x_studio_grade,
                    'appointment_date': employee.appointment_date,
                    # 'birthday': employee.birthday,
                    'gross_salary': employee.contract_id.wage,
                    # 'personal_file_number': employee.x_studio_personal_file_number,
                    # 'location': employee.location_id.emp_location,
                    # 'name_of_reporting_officer': employee.parent_id.name,
                    'emp_type':  employee.contract_id.contract_type_id.name,
                    # 'cl_count': leaves_data.get("casual_leaves_count"),
                    # 'sl_count': leaves_data.get("sick_leaves_count"),
                    # 'earned_leaves_balance': leaves_data.get("earned_leaves_balance")
                })


    def write(self, vals):
        login_user = self.env.user
        remark_fields = ['remarks', 'remarks_2', 'remarks_3', 'remarks_4', 'remarks_5']

        # --- Mark document as saved when remarks are modified ---
        if any(field in vals for field in remark_fields):
            self.doc_state = 'save'

        # --- Process increment lines safely ---
        if 'recomm_increment_lines_id' in vals:
            filtered_lines = self.recomm_increment_lines_id.filtered(
                lambda line: line.increment_raise_by.id == login_user.id
            )

            # Prevent adding more lines if already exists for this user
            if filtered_lines and vals['recomm_increment_lines_id'][0][0] == 0:
                raise ValidationError(_('You cannot add more lines.'))

            for command in vals.get('recomm_increment_lines_id', []):
                if command[0] == 0 and isinstance(command[2], dict):  # new line
                    data = command[2]
                    self.recommend_raise_amount = data.get('increment_raise_amount', self.recommend_raise_amount)
                    self.recommend_designation_id = data.get('recomm_desigantion_id', self.recommend_designation_id)
                    self.recommend_grades = data.get('recomm_grades', self.recommend_grades)

                    amount = data.get('increment_raise_amount') or 0.0
                    gross_salary = self.gross_salary or 0.0
                    amount = (data.get('increment_raise_amount') or 0.0)

                    if gross_salary > 0 and amount > 0:
                        self.increase_percentage = (amount / gross_salary) * 100
                    else:
                        self.increase_percentage = 0.0

                    data.update({
                        'increment_raise_by': login_user.id,
                        'incremented_date': fields.Datetime.now(),
                        'state': data.get('state', self.state),
                    })

        # --- Append signature and timestamp for remarks ---
        for field_name in remark_fields + ['future_project']:
            if field_name in vals and vals[field_name]:
                vals[field_name] += f"\nBy: {login_user.name} {fields.Datetime.now().strftime('%a, %d-%b-%Y')}"

        # --- Access restriction for unauthorized managers ---
        if not self.is_manager:
            if self.state == 'draft' and login_user.has_group('prodo_appraisal_ext.group_hr_manager_appraisal_3'):
                pass
            elif self.state == 'new' and self.employee_id.parent_id.user_id != login_user:
            #     subordinate_appraisals = self.env['hr.appraisal'].search([
            #         ('employee_id.parent_id.user_id', '=', login_user.id)
            #     ])
            #     if not subordinate_appraisals:
            #         raise ValidationError(_('You are not allowed to edit this appraisal.'))
            #     # If there are appraisals under this manager, allow access only for those
            #     elif self.employee_id.parent_id.user_id != login_user:
            #         raise ValidationError(_('You are only allowed to edit appraisals of your subordinates.'))

                if not self.env.context.get('appraisal_remarks'):
                    raise ValidationError(_('You are not allowed to edit this appraisal.'))

        # --- Final write ---
        result = super(HrAppraisal, self).write(vals)
        return result
    #
    @api.depends('employee_id')
    def _leaves_count(self):
        first = date(2025, 1, 1)
        last = date(2025, 12, 31)

        current_year = datetime.now().year

        for emp in self.employee_id:

            casual_work_entry_type = self.env['hr.work.entry.type'].search([('name', '=', 'Casual Time Off')])
            sick_work_entry_type = self.env['hr.work.entry.type'].search([('name', '=', 'Sick Time Off')])
            pl_work_entry_type = self.env['hr.work.entry.type'].search([('name', '=', 'PL Leaves')])


            casual_leave_type = self.env['hr.leave.type'].search([('work_entry_type_id', '=', casual_work_entry_type.id)])
            sick_leave_type = self.env['hr.leave.type'].search([('work_entry_type_id', '=', sick_work_entry_type.id)])
            pl_work_type = self.env['hr.leave.type'].search([('work_entry_type_id', '=', pl_work_entry_type.id)])

            cl_leave_allocate = self.env['hr.leave.allocation'].search(
                [('holiday_status_id', 'in', casual_leave_type.ids), ('state', '=', 'validate'),
                 ('employee_id', '=',emp.id)])
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


    def action_open_share_appraisal_wizard(self):
        template = self.env.ref('project.mail_template_project_sharing', raise_if_not_found=False)

        local_context = self.env.context | {
            'default_template_id': template.id if template else False,
            'default_email_layout_xmlid': 'mail.mail_notification_light',
            'active_id': self.id,
            'active_model': 'hr.appraisal',
        }
        action = self.env["ir.actions.actions"]._for_xml_id("prodo_appraisal_ext.appraisal_share_wizard_action")
        if self.env.context.get('default_access_mode'):
            action['name'] = _("Share Appraisal")
        action['context'] = local_context
        return action
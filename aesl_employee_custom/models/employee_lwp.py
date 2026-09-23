from odoo import fields, models, tools


class LwpReport(models.Model):
    _name = 'aesl.lwp.report'
    _description = 'LWP Report'
    _auto = False
    _rec_name = 'employee_id'
    _order = 'attendance_date desc, employee_id'

    attendance_id = fields.Many2one(
        'hr.attendance',
        string='Attendance',
        readonly=True,
    )

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        readonly=True,
    )

    attendance_date = fields.Date(
        string='Attendance Date',
        readonly=True,
    )

    status2 = fields.Char(
        string='Status',
        readonly=True,
    )

    in_status = fields.Char(
        string='In Status',
        readonly=True,
    )

    on_leave = fields.Boolean(
        string='On Leave',
        readonly=True,
    )

    deduction_status = fields.Selection(
        [
            ('leave', 'Leave'),
            ('lwp', 'LWP'),
            ('present', 'Present'),
            ('not_considered', 'Not Considered'),
        ],
        string='Deduction Status',
        readonly=True,
    )
    #
    # def init(self):
    #     tools.drop_view_if_exists(self.env.cr, self._table)
    #
    #     self.env.cr.execute("""
    #         CREATE OR REPLACE VIEW aesl_lwp_report AS (
    #
    #             SELECT
    #                 a.id AS id,
    #                 a.id AS attendance_id,
    #                 a.employee_id AS employee_id,
    #                 a.attendance_date AS attendance_date,
    #                 a.status2 AS status2,
    #                 a.in_status AS in_status,
    #                 a.on_leave AS on_leave,
    #
    #                 CASE
    #                     WHEN EXISTS (
    #                         SELECT 1
    #                         FROM hr_leave l
    #                         WHERE l.employee_id = a.employee_id
    #                           AND a.attendance_date BETWEEN
    #                                 l.request_date_from::date
    #                                 AND l.request_date_to::date
    #                           AND l.state IN (
    #                               'confirm',
    #                               'validate1',
    #                               'validate'
    #                           )
    #                     )
    #                     THEN 'leave'
    #
    #                     WHEN a.status2 IN (
    #                         'absent',
    #                         'missed_check_in'
    #                     )
    #                     THEN 'lwp'
    #
    #                     WHEN a.status2 = 'Present'
    #                          AND a.in_status IN ('3', '5')
    #                     THEN 'present'
    #
    #                     ELSE 'not_considered'
    #                 END AS deduction_status
    #
    #             FROM hr_attendance a
    #
    #             WHERE
    #                 (
    #                     a.status2 IN (
    #                         'absent',
    #                         'missed_check_in'
    #                     )
    #
    #                     OR (
    #                         a.status2 = 'Present'
    #                         AND a.in_status IN ('3', '5')
    #                     )
    #                 )
    #         )
    #     """)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)

        self.env.cr.execute("""
            CREATE OR REPLACE VIEW aesl_lwp_report AS (

                SELECT
                    a.id AS id,
                    a.id AS attendance_id,
                    a.employee_id AS employee_id,
                    a.attendance_date AS attendance_date,
                    a.status2 AS status2,
                    a.in_status AS in_status,
                    a.on_leave AS on_leave,

                    'lwp' AS deduction_status

                FROM hr_attendance a

                WHERE
                    a.status2 IN ('absent', 'missed_check_in')

                    AND NOT EXISTS (
                        SELECT 1
                        FROM hr_leave l
                        WHERE l.employee_id = a.employee_id
                          AND a.attendance_date BETWEEN
                                l.request_date_from::date
                                AND l.request_date_to::date
                          AND l.state IN (
                              'confirm',
                              'validate1',
                              'validate'
                          )
                    )
            )
        """)
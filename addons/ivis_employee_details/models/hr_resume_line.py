from odoo import api, models, fields


class HrPayslipInherit(models.Model):
    _inherit = 'hr.resume.line'

    #Education Fields
    organization = fields.Char(string="Organization")
    degree = fields.Char(string="Degree")
    degree_title = fields.Char(string="Degree Title")
    specialization = fields.Char(string="Specialization")
    percentage = fields.Float(string="Percentage")
    cgpa = fields.Float(string="CGPA")
    division = fields.Char(string="Division")
    selected_type = fields.Char(string="Is Education", compute='_compute_selected_type', store=True)

    #Certification Fields
    certificate_no = fields.Char(string='Certificate No')
    issued_by = fields.Char(string='Issued By')
    expiry_date = fields.Date(string='Expiry Date')

    #Work Experience Fields
    designation = fields.Char(string="Designation")
    pay_scale = fields.Char(string="Pay Scale")
    job_description = fields.Text(string="Job Description")

    attachment = fields.Binary(string="Attachment")
    @api.depends('line_type_id')
    def _compute_selected_type(self):
        for rec in self:
            rec.selected_type = rec.line_type_id.name

from odoo import models, fields


class CertificationRecord(models.Model):
    _name = 'certification.record'
    _description = "Certifications"

    name = fields.Char('Name', required=True, )
    certificate_id = fields.Many2one('hr.employee',
                                     string='Employee',
                                     required=True)
    start_date = fields.Date('Start date', required=True)
    end_date = fields.Date('End date')
    description = fields.Text('Description')
    location = fields.Char('Organization')
    expire = fields.Boolean('Expire', help="Expire", default=True)
    attachments = fields.Binary()

    certification = fields.Char(string='Certification No',
                                help='Certification Number')

    institute = fields.Many2one('institute.institute', string="Institute/Board", required=True)
    expiry_date = fields.Date(string='Expiry Date')

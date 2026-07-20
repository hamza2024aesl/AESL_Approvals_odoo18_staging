from odoo import models, fields


class EmployeeDescription(models.Model):
    _name = "employee.description"

    description_name = fields.Char()

    # def name_get(self):
    #     result = []
    #     for record in self:
    #         if record.description_name:
    #             name = record.description_name
    #             record.name = name
    #             result.append(name)
    #     return result

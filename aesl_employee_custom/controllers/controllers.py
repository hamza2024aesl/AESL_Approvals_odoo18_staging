# -*- coding: utf-8 -*-
# from odoo import http


# class AeslEmployeeCustom(http.Controller):
#     @http.route('/aesl_employee_custom/aesl_employee_custom', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/aesl_employee_custom/aesl_employee_custom/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('aesl_employee_custom.listing', {
#             'root': '/aesl_employee_custom/aesl_employee_custom',
#             'objects': http.request.env['aesl_employee_custom.aesl_employee_custom'].search([]),
#         })

#     @http.route('/aesl_employee_custom/aesl_employee_custom/objects/<model("aesl_employee_custom.aesl_employee_custom"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('aesl_employee_custom.object', {
#             'object': obj
#         })


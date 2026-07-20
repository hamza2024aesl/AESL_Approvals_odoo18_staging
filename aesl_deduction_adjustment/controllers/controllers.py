# -*- coding: utf-8 -*-
# from odoo import http


# class aesl_deduction_adjustment(http.Controller):
#     @http.route('/aesl_deduction_adjustment/aesl_deduction_adjustment/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/aesl_deduction_adjustment/aesl_deduction_adjustment/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('aesl_deduction_adjustment.listing', {
#             'root': '/aesl_deduction_adjustment/aesl_deduction_adjustment',
#             'objects': http.request.env['aesl_deduction_adjustment.aesl_deduction_adjustment'].search([]),
#         })

#     @http.route('/aesl_deduction_adjustment/aesl_deduction_adjustment/objects/<model("aesl_deduction_adjustment.aesl_deduction_adjustment"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('aesl_deduction_adjustment.object', {
#             'object': obj
#         })

# -*- coding: utf-8 -*-
# from odoo import http


# class AeslBonusSystem(http.Controller):
#     @http.route('/aesl_bonus_system/aesl_bonus_system/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/aesl_bonus_system/aesl_bonus_system/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('aesl_bonus_system.listing', {
#             'root': '/aesl_bonus_system/aesl_bonus_system',
#             'objects': http.request.env['aesl_bonus_system.aesl_bonus_system'].search([]),
#         })

#     @http.route('/aesl_bonus_system/aesl_bonus_system/objects/<model("aesl_bonus_system.aesl_bonus_system"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('aesl_bonus_system.object', {
#             'object': obj
#         })

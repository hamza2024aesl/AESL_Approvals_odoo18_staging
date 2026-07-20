# -*- coding: utf-8 -*-
# from odoo import http


# class AeslAppraisalSystem(http.Controller):
#     @http.route('/aesl_appraisal_system/aesl_appraisal_system/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/aesl_appraisal_system/aesl_appraisal_system/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('aesl_appraisal_system.listing', {
#             'root': '/aesl_appraisal_system/aesl_appraisal_system',
#             'objects': http.request.env['aesl_appraisal_system.aesl_appraisal_system'].search([]),
#         })

#     @http.route('/aesl_appraisal_system/aesl_appraisal_system/objects/<model("aesl_appraisal_system.aesl_appraisal_system"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('aesl_appraisal_system.object', {
#             'object': obj
#         })

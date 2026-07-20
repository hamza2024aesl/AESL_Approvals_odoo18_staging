from odoo import http


class HcsLeavesChart(http.Controller):
    @http.route('/hcs_leaves_chart/hcs_leaves_chart/', auth='public')
    def index(self, **kw):
        return "Hello, world"

    @http.route('/hcs_leaves_chart/hcs_leaves_chart/objects/', auth='public')
    def list(self, **kw):
        return http.request.render('hcs_leaves_chart.listing', {
            'root': '/hcs_leaves_chart/hcs_leaves_chart',
            'objects': http.request.env['hcs_leaves_chart.hcs_leaves_chart'].search([]),
        })

    @http.route('/hcs_leaves_chart/hcs_leaves_chart/objects/<model("hcs_leaves_chart.hcs_leaves_chart"):obj>/',
                auth='public')
    def object(self, obj, **kw):
        return http.request.render('hcs_leaves_chart.object', {
            'object': obj
        })
# -*- coding: utf-8 -*-
# from odoo import http


# class C:\users\rtrice\source\repos\odooHsv\odoodev(http.Controller):
#     @http.route('/c:\users\rtrice\source\repos\odoo_hsv\odoodev/c:\users\rtrice\source\repos\odoo_hsv\odoodev', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/c:\users\rtrice\source\repos\odoo_hsv\odoodev/c:\users\rtrice\source\repos\odoo_hsv\odoodev/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('c:\users\rtrice\source\repos\odoo_hsv\odoodev.listing', {
#             'root': '/c:\users\rtrice\source\repos\odoo_hsv\odoodev/c:\users\rtrice\source\repos\odoo_hsv\odoodev',
#             'objects': http.request.env['c:\users\rtrice\source\repos\odoo_hsv\odoodev.c:\users\rtrice\source\repos\odoo_hsv\odoodev'].search([]),
#         })

#     @http.route('/c:\users\rtrice\source\repos\odoo_hsv\odoodev/c:\users\rtrice\source\repos\odoo_hsv\odoodev/objects/<model("c:\users\rtrice\source\repos\odoo_hsv\odoodev.c:\users\rtrice\source\repos\odoo_hsv\odoodev"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('c:\users\rtrice\source\repos\odoo_hsv\odoodev.object', {
#             'object': obj
#         })

from odoo import http
import logging
_logger = logging.getLogger(__name__)
class ProjectedShortagesController(http.Controller):
    @http.route('/projected_shortages', type='http', auth='user', website=True)
    def projected_shortages(self, **kw):
        return http.request.render('edge_module.projected_shortages_template')

# controllers/mo_list.py

from odoo import http
from odoo.http import request


class ComponentMOViewController(http.Controller):
    @http.route('/component_mo_view/<int:product_id>', type='http', auth='user', website=True)
    def component_mo_view(self, product_id, **kwargs):
        action = request.env.ref('edge_module.component_mo_view_action').read()[0]
        _logger.info(action)
        _logger.info(action['id'])
        _logger.info(action['context'])
        _logger.info(action['name'])
        return request.redirect('/web?#action=%s&active_id=%s' % (action['id'], product_id))
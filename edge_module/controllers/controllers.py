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

class ProjectedShortagesController(http.Controller):
    @http.route('/projected_shortages', type='http', auth='user', website=True)
    def projected_shortages(self, **kw):
        return http.request.render('edge_module.projected_shortages_template')

# controllers/mo_list.py

from odoo import http
from odoo.http import request

class MOListController(http.Controller):
    @http.route('/mo_list/<int:product_id>', type='http', auth='user', website=True)
    def mo_list(self, product_id, **kwargs):
        MO = request.env['mrp.production']
        mos = MO.search([('product_id', '=', product_id), ('state', 'not in', ['done', 'cancel'])])
        
        mo_data = []
        total_component_qty = 0
        
        for mo in mos:
            component_qty = sum(mo.move_raw_ids.mapped(lambda m: m.product_uom_qty * m.unit_factor))
            mo_qty = mo.product_qty
            total_qty = mo_qty * component_qty
            total_component_qty += total_qty
            
            mo_data.append({
                'mo_name': mo.name,
                'mo_id': mo.id,
                'mo_qty': mo_qty,
                'component_qty': component_qty,
                'total_qty': total_qty,
            })
        
        return request.render('your_module_name.mo_list_template', {
            'mo_data': mo_data,
            'total_component_qty': total_component_qty,
        })
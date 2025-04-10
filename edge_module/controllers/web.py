from odoo import http
from odoo.addons.web.controllers.home import Home
from odoo.http import request

class ExtendedHome(Home):
    @http.route()
    def index(self, *args, **kw):
        if request.session.uid:
            user = request.env['res.users'].browse(request.session.uid)
            if user.has_group('base.group_portal'):
                # Check if user is a purchase request approver (at any level)
                partner_id = user.partner_id.id
                approver = request.env['purchase.request.approver'].sudo().search([
                    ('user_id.partner_id', '=', partner_id)
                ], limit=1)
                
                # If they're an approver, redirect them to the purchase requests
                if approver:
                    return request.redirect('/my/purchase_requests')
        
        return super(ExtendedHome, self).index(*args, **kw)
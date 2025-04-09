from odoo import http
from odoo.addons.web.controllers.home import Home
from odoo.http import request

class ExtendedHome(Home):
    @http.route()
    def index(self, *args, **kw):
        if request.session.uid:
            user = request.env['res.users'].browse(request.session.uid)
            if user.has_group('base.group_portal'):
                # Check if user is a purchase request approver
                partner_id = user.partner_id.id
                
                PurchaseRequest = request.env['purchase.request'].sudo()
                pending_approvals = PurchaseRequest.search_count([
                    '|', '|', '|', '|', 
                    ('approver_level_1.user_id.partner_id', '=', partner_id),
                    ('approver_level_2.user_id.partner_id', '=', partner_id),
                    ('approver_level_3.user_id.partner_id', '=', partner_id),
                    ('approver_level_4.user_id.partner_id', '=', partner_id),
                    ('approver_level_5.user_id.partner_id', '=', partner_id),
                    ('state', '=', 'pending_approval')
                ])
                
                if pending_approvals > 0:
                    return request.redirect('/my/purchase_requests')
        
        return super(ExtendedHome, self).index(*args, **kw)
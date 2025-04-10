from odoo import http
from odoo.addons.web.controllers.home import Home
from odoo.http import request

import logging
_logger = logging.getLogger(__name__)

class ExtendedHome(Home):
    @http.route()
    def index(self, *args, **kw):
        _logger.info("ExtendedHome index method called")
        if request.session.uid:
            _logger.info("User ID: %s", request.session.uid)
            user = request.env['res.users'].browse(request.session.uid)
            _logger.info("User: %s", user.name)
            if user.has_group('base.group_portal'):
                _logger.info("User is a portal user")
                # Check if user is a purchase request approver (at any level)
                partner_id = user.partner_id.id
                _logger.info("Partner ID: %s", partner_id)
                approver = request.env['purchase.request.approver'].sudo().search([
                    ('user_id.partner_id', '=', partner_id)
                ], limit=1)
                
                # If they're an approver, redirect them to the purchase requests
                if approver:
                    _logger.info("User is a purchase request approver")
                    return request.redirect('/my/purchase_requests')
                _logger.info("User is NOT a purchase request approver")
        
        return super(ExtendedHome, self).index(*args, **kw)
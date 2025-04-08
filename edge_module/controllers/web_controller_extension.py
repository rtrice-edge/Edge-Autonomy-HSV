# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.home import Home

class HomeExtension(Home):
    @http.route()
    def index(self, *args, **kw):
        if request.session.uid and self._is_purchase_approver(request.session.uid):
            return http.request.redirect('/web#action=edge_module.action_purchase_request')
        return super().index(*args, **kw)

    @http.route()
    def web_client(self, s_action=None, **kw):
        if request.session.uid and self._is_purchase_approver(request.session.uid):
            return super().web_client(s_action, **kw)
        return super().web_client(s_action, **kw)

    def _is_purchase_approver(self, uid):
        # Check if the user is in the portal purchase approver group
        user = request.env['res.users'].sudo().browse(uid)
        return user.has_group('edge_module.group_portal_purchase_approver')
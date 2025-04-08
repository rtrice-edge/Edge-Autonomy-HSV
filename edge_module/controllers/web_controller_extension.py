# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.http import request
from odoo.addons.web.controllers.home import Home

class HomeExtended(Home):
    @http.route()
    def index(self, *args, **kw):
        if request.session.uid and not self._is_public_user():
            user = request.env['res.users'].browse(request.session.uid)
            if self._is_purchase_approver(user):
                return http.request.redirect('/web#cids=1&menu_id=208&action=edge_module.action_purchase_request')
        return super(HomeExtended, self).index(*args, **kw)
    
    @http.route()
    def web_client(self, s_action=None, **kw):
        if request.session.uid and not self._is_public_user():
            user = request.env['res.users'].browse(request.session.uid)
            if self._is_purchase_approver(user) and not s_action:
                s_action = 'edge_module.action_purchase_request'
        return super(HomeExtended, self).web_client(s_action=s_action, **kw)
    
    def _is_public_user(self):
        return request.env.user._is_public()
    
    def _is_purchase_approver(self, user):
        """Check if user is listed as an approver in any purchase request"""
        if user.has_group('base.group_portal'):
            approver_records = request.env['purchase.request.approver'].sudo().search([
                ('user_id', '=', user.id)
            ])
            return bool(approver_records)
        return False
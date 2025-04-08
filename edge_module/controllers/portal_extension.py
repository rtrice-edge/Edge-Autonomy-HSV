# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.home import Home

import logging

_logger = logging.getLogger(__name__)

class HomeExtended(Home):
    @http.route()
    def index(self, *args, **kw):
        _logger.info("------------- index method called --------------------")
        _logger.info("PORTAL EXTENSTION CONTROLLER: User ID: %s", request.session.uid)
        if request.session.uid:
            user = request.env['res.users'].browse(request.session.uid)
            _logger.info("User ID: %s", user.id)
            _logger.info("User Name: %s", user.name)
            _logger.info("User Groups: %s", user.groups_id.mapped('name'))
            if user.has_group('base.group_portal') and self._is_purchase_approver(user):
                _logger.info("User is a purchase approver")
                return http.request.redirect('/web#cids=1&action=edge_module.action_purchase_request')
        return super().index(*args, **kw)
    
    @http.route()
    def web_client(self, s_action=None, **kw):
        _logger.info("-------------- web client method called -------------------------")
        _logger.info("PORTAL EXTENSTION CONTROLLER: User ID: %s", request.session.uid)
        if request.session.uid:
            user = request.env['res.users'].browse(request.session.uid)
            _logger.info("User ID: %s", user.id)
            _logger.info("User Name: %s", user.name)
            _logger.info("User Groups: %s", user.groups_id.mapped('name'))
            if user.has_group('base.group_portal') and self._is_purchase_approver(user):
                _logger.info("User is a purchase approver")
                if not s_action:
                    _logger.info("s_action is None, setting it to edge_module.action_purchase_request")
                    s_action = 'edge_module.action_purchase_request'
                return super().web_client(s_action=s_action, **kw)
        return super().web_client(s_action=s_action, **kw)
    
    def _is_purchase_approver(self, user):
        _logger.info("Checking if user is a purchase approver")
        """Check if user is listed as an approver in any purchase request"""
        approver_records = request.env['purchase.request.approver'].sudo().search([
            ('user_id', '=', user.id)
        ])
        _logger.info("Approver records found: %s", approver_records)
        if approver_records:
            _logger.info("User is a purchase approver")
        else:
            _logger.info("User is NOT a purchase approver")
        return bool(approver_records)
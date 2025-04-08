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
            # Use sudo() to avoid permission issues
            user = request.env['res.users'].sudo().browse(request.session.uid)
            _logger.info("User ID: %s", user.id)
            _logger.info("User Name: %s", user.name)
            
            # Skip the override for admin and internal users
            if user.has_group('base.group_system') or user.has_group('base.group_user'):
                _logger.info("User is admin or internal - using standard behavior")
                return super().index(*args, **kw)
                
            _logger.info("User Groups: %s", user.groups_id.mapped('name'))
            # Check if portal user and approver using sudo
            is_portal = user.has_group('base.group_portal')
            is_approver = self._is_purchase_approver(user)
            
            if is_portal and is_approver:
                _logger.info("User is a portal user and purchase approver - redirecting to purchase requests")
                return http.request.redirect('/web#cids=1&action=edge_module.action_purchase_request')
        return super().index(*args, **kw)
    
    @http.route()
    def web_client(self, s_action=None, **kw):
        _logger.info("-------------- web client method called -------------------------")
        _logger.info("PORTAL EXTENSTION CONTROLLER: User ID: %s", request.session.uid)
        if request.session.uid:
            # Use sudo() to avoid permission issues
            user = request.env['res.users'].sudo().browse(request.session.uid)
            _logger.info("User ID: %s", user.id)
            _logger.info("User Name: %s", user.name)
            
            # Skip the override for admin and internal users
            if user.has_group('base.group_system') or user.has_group('base.group_user'):
                _logger.info("User is admin or internal - using standard behavior")
                return super().web_client(s_action=s_action, **kw)
                
            _logger.info("User Groups: %s", user.groups_id.mapped('name'))
            # Check if portal user and approver using sudo
            is_portal = user.has_group('base.group_portal')
            is_approver = self._is_purchase_approver(user)
            
            if is_portal and is_approver:
                _logger.info("User is a portal user and purchase approver")
                if not s_action:
                    _logger.info("s_action is None, setting it to edge_module.action_purchase_request")
                    s_action = 'edge_module.action_purchase_request'
                return super().web_client(s_action=s_action, **kw)
        return super().web_client(s_action=s_action, **kw)
    
    def _is_purchase_approver(self, user):
        _logger.info("Checking if user is a purchase approver")
        """Check if user is listed as an approver in any purchase request"""
        # Use sudo() to avoid permission issues
        approver_records = request.env['purchase.request.approver'].sudo().search([
            ('user_id', '=', user.id)
        ])
        _logger.info("Approver records found: %s", approver_records)
        if approver_records:
            _logger.info("User is a purchase approver")
        else:
            _logger.info("User is NOT a purchase approver")
        return bool(approver_records)
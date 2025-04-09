# -*- coding: utf-8 -*-
from collections import OrderedDict
from odoo import http, _, fields
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.exceptions import AccessError, MissingError

class PurchaseRequestPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        
        if 'purchase_request_count' in counters:
            partner = request.env.user.partner_id
            PurchaseRequest = request.env['purchase.request']
            
            domain = [
                '|', '|', '|', '|', '|',
                ('approver_level_1.user_id.partner_id', '=', partner.id),
                ('approver_level_2.user_id.partner_id', '=', partner.id),
                ('approver_level_3.user_id.partner_id', '=', partner.id),
                ('approver_level_4.user_id.partner_id', '=', partner.id),
                ('approver_level_5.user_id.partner_id', '=', partner.id),
                ('state', '=', 'pending_approval')
            ]
            
            values['purchase_request_count'] = PurchaseRequest.search_count(domain)
        
        return values

    @http.route(['/my/purchase_requests', '/my/purchase_requests/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_purchase_requests(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        PurchaseRequest = request.env['purchase.request']
        
        domain = [
            '|', '|', '|', '|', '|',
            ('approver_level_1.user_id.partner_id', '=', partner.id),
            ('approver_level_2.user_id.partner_id', '=', partner.id),
            ('approver_level_3.user_id.partner_id', '=', partner.id),
            ('approver_level_4.user_id.partner_id', '=', partner.id),
            ('approver_level_5.user_id.partner_id', '=', partner.id),
            ('state', '=', 'pending_approval')
        ]
        
        # Sorting options
        searchbar_sortings = {
            'date': {'label': _('Date'), 'order': 'date_requested desc'},
            'name': {'label': _('Reference'), 'order': 'name'},
            'amount': {'label': _('Amount'), 'order': 'amount_total desc'},
        }
        
        # Default sort by date
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']
        
        # Count for pager
        purchase_request_count = PurchaseRequest.search_count(domain)
        
        # Pager
        pager = portal_pager(
            url="/my/purchase_requests",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=purchase_request_count,
            page=page,
            step=self._items_per_page
        )
        
        # Content according to pager and order
        purchase_requests = PurchaseRequest.search(
            domain, 
            order=order, 
            limit=self._items_per_page, 
            offset=pager['offset']
        )
        
        values.update({
            'purchase_requests': purchase_requests,
            'page_name': 'purchase_requests',
            'pager': pager,
            'default_url': '/my/purchase_requests',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
        })
        
        return request.render("edge_module.portal_my_purchase_requests", values)

    @http.route(['/my/purchase_requests/<int:purchase_request_id>'], type='http', auth="user", website=True)
    def portal_my_purchase_request_detail(self, purchase_request_id, **kw):
        try:
            purchase_request_sudo = self._document_check_access('purchase.request', purchase_request_id)
        except (AccessError, MissingError):
            return request.redirect('/my')
            
        # Check if the user is an approver for this purchase request
        partner = request.env.user.partner_id
        is_approver = False
        
        for i in range(1, 6):
            approver_field = f'approver_level_{i}'
            if hasattr(purchase_request_sudo, approver_field):
                approver = getattr(purchase_request_sudo, approver_field)
                if approver and approver.user_id.partner_id.id == partner.id:
                    is_approver = True
                    break
        
        if not is_approver and purchase_request_sudo.state != 'pending_approval':
            return request.redirect('/my')
            
        values = {
            'purchase_request': purchase_request_sudo,
            'page_name': 'purchase_request_detail',
            'is_approver': is_approver,
        }
        
        return request.render("edge_module.portal_my_purchase_request_detail", values)
        
    @http.route(['/my/purchase_requests/<int:purchase_request_id>/approve'], type='http', auth="user", website=True, methods=['POST'])
    def portal_approve_purchase_request(self, purchase_request_id, **kw):
        try:
            purchase_request_sudo = self._document_check_access('purchase.request', purchase_request_id)
        except (AccessError, MissingError):
            return request.redirect('/my')
            
        # Check if the user is an approver for this purchase request
        partner = request.env.user.partner_id
        can_approve = False
        
        # Find which approver level the current user is
        for i in range(1, 6):
            approver_field = f'approver_level_{i}'
            is_approved_field = f'is_level_{i}_approved'
            
            if hasattr(purchase_request_sudo, approver_field) and hasattr(purchase_request_sudo, is_approved_field):
                approver = getattr(purchase_request_sudo, approver_field)
                is_approved = getattr(purchase_request_sudo, is_approved_field)
                
                if approver and approver.user_id.partner_id.id == partner.id and not is_approved:
                    can_approve = True
                    break
        
        if can_approve and purchase_request_sudo.state == 'pending_approval':
            # Call the approve function
            purchase_request_sudo.sudo().action_approve()
            
            # Post message in chatter
            purchase_request_sudo.sudo().message_post(
                body=_("Request approved by %s through the portal.") % partner.name,
                message_type='notification',
                subtype_xmlid='mail.mt_comment'
            )
            
        return request.redirect('/my/purchase_requests/%s' % purchase_request_id)
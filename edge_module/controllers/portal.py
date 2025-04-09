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
            
            # Similar logic as the list view
            request_ids = []
            pending_requests = PurchaseRequest.sudo().search([
                ('state', '=', 'pending_approval')
            ])
            
            for pr in pending_requests:
                for i in range(1, 13):
                    needs_approver_field = f'needs_approver_level_{i}'
                    is_approved_field = f'is_level_{i}_approved'
                    approver_field = f'approver_level_{i}'
                    
                    if hasattr(pr, needs_approver_field) and getattr(pr, needs_approver_field):
                        if hasattr(pr, is_approved_field) and not getattr(pr, is_approved_field):
                            if hasattr(pr, approver_field):
                                approver = getattr(pr, approver_field)
                                if approver and approver.user_id.partner_id.id == partner.id:
                                    request_ids.append(pr.id)
                                    break
                            break
            
            values['purchase_request_count'] = len(request_ids)
        
        return values

    @http.route(['/my/purchase_requests', '/my/purchase_requests/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_purchase_requests(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        PurchaseRequest = request.env['purchase.request']
        
        # We'll build a list of IDs of purchase requests requiring this user's approval
        request_ids = []
        
        # First get all purchase requests that are in pending_approval state
        pending_requests = PurchaseRequest.sudo().search([
            ('state', '=', 'pending_approval')
        ])
        
        # Now filter for only those where this user is the next required approver
        for pr in pending_requests:
            for i in range(1, 13):  # Loop through all possible approver levels
                needs_approver_field = f'needs_approver_level_{i}'
                is_approved_field = f'is_level_{i}_approved'
                approver_field = f'approver_level_{i}'
                
                # Check if we need this level of approval
                if hasattr(pr, needs_approver_field) and getattr(pr, needs_approver_field):
                    # Check if this level is not yet approved
                    if hasattr(pr, is_approved_field) and not getattr(pr, is_approved_field):
                        # Check if the current user is the approver at this level
                        if hasattr(pr, approver_field):
                            approver = getattr(pr, approver_field)
                            if approver and approver.user_id.partner_id.id == partner.id:
                                # This PR needs this user's approval next
                                request_ids.append(pr.id)
                                break  # Break after finding the first level that needs approval
                        
                        # If we've found a level that needs approval but the current 
                        # user is not the approver, break the loop - no need to check further
                        break
        
        # Now build the domain using the filtered IDs
        domain = [('id', 'in', request_ids)]
        
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
        purchase_request_count = len(request_ids)
        
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
            
        # Check if the user is the next required approver for this purchase request
        partner = request.env.user.partner_id
        is_next_approver = False
        
        # Only allow viewing if the request is in pending_approval state
        if purchase_request_sudo.state != 'pending_approval':
            return request.redirect('/my')
        
        # Check if user is the next required approver
        for i in range(1, 13):
            needs_approver_field = f'needs_approver_level_{i}'
            is_approved_field = f'is_level_{i}_approved'
            approver_field = f'approver_level_{i}'
            
            if hasattr(purchase_request_sudo, needs_approver_field) and getattr(purchase_request_sudo, needs_approver_field):
                if hasattr(purchase_request_sudo, is_approved_field) and not getattr(purchase_request_sudo, is_approved_field):
                    if hasattr(purchase_request_sudo, approver_field):
                        approver = getattr(purchase_request_sudo, approver_field)
                        if approver and approver.user_id.partner_id.id == partner.id:
                            is_next_approver = True
                            break
                    break
        
        if not is_next_approver:
            return request.redirect('/my')
            
        values = {
            'purchase_request': purchase_request_sudo,
            'page_name': 'purchase_request_detail',
            'is_approver': is_next_approver,
        }
        
        return request.render("edge_module.portal_my_purchase_request_detail", values)
        
    @http.route(['/my/purchase_requests/<int:purchase_request_id>/approve'], type='http', auth="user", website=True, methods=['POST'])
    def portal_approve_purchase_request(self, purchase_request_id, **kw):
        try:
            purchase_request_sudo = self._document_check_access('purchase.request', purchase_request_id)
        except (AccessError, MissingError):
            return request.redirect('/my')
            
        # Check if the user is the next required approver for this purchase request
        partner = request.env.user.partner_id
        can_approve = False
        approver_level = None
        
        # Only allow approval if the request is in pending_approval state
        if purchase_request_sudo.state != 'pending_approval':
            return request.redirect('/my')
        
        # Check if user is the next required approver
        for i in range(1, 13):
            needs_approver_field = f'needs_approver_level_{i}'
            is_approved_field = f'is_level_{i}_approved'
            approver_field = f'approver_level_{i}'
            
            if hasattr(purchase_request_sudo, needs_approver_field) and getattr(purchase_request_sudo, needs_approver_field):
                if hasattr(purchase_request_sudo, is_approved_field) and not getattr(purchase_request_sudo, is_approved_field):
                    if hasattr(purchase_request_sudo, approver_field):
                        approver = getattr(purchase_request_sudo, approver_field)
                        if approver and approver.user_id.partner_id.id == partner.id:
                            can_approve = True
                            approver_level = i
                            break
                    break
        
        if can_approve:
            # Mark this level as approved
            setattr(purchase_request_sudo.sudo(), f'is_level_{approver_level}_approved', True)
            
            # Check if fully approved
            if purchase_request_sudo.sudo().is_fully_approved():
                purchase_request_sudo.sudo().write({'state': 'approved'})
                
            # Post message in chatter
            purchase_request_sudo.sudo().message_post(
                body=_("Level %s approval completed by %s through the portal.") % (approver_level, partner.name),
                message_type='notification',
                subtype_xmlid='mail.mt_comment'
            )
            
            # Notify the next approver if there is one
            purchase_request_sudo.sudo()._notify_next_approver()
            
        return request.redirect('/my/purchase_requests')
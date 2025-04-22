# -*- coding: utf-8 -*-
from collections import OrderedDict
from odoo import http, _, fields
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.exceptions import AccessError, MissingError
from ..models.TeamsLib import TeamsLib
import logging
_logger = logging.getLogger(__name__)

class PurchaseRequestPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        
        if 'purchase_request_count' in counters:
            partner = request.env.user.partner_id
            PurchaseRequest = request.env['purchase.request']
            
            # Get all potentially relevant purchase requests
            potential_requests = PurchaseRequest.sudo().search([
                ('state', 'in', ['pending_approval', 'approved', 'po_created', 'cancelled'])
            ])
            
            request_count = 0
            for pr in potential_requests:
                user_is_approver = False
                user_already_approved = False
                user_is_next_approver = False
                
                # Check each approver level
                for i in range(1, 15):
                    needs_approver_field = f'needs_approver_level_{i}'
                    is_approved_field = f'is_level_{i}_approved'
                    approver_field = f'approver_level_{i}'
                    
                    if hasattr(pr, needs_approver_field) and getattr(pr, needs_approver_field):
                        if hasattr(pr, approver_field):
                            approver = getattr(pr, approver_field)
                            if approver and approver.user_id.partner_id.id == partner.id:
                                user_is_approver = True
                                
                                # Check if this level is already approved
                                if hasattr(pr, is_approved_field) and getattr(pr, is_approved_field):
                                    user_already_approved = True
                                # If not approved yet and PR is in pending_approval state
                                elif pr.state == 'pending_approval':
                                    # Check if all previous levels are approved
                                    is_next = True
                                    for j in range(1, i):
                                        prev_needs_field = f'needs_approver_level_{j}'
                                        prev_approved_field = f'is_level_{j}_approved'
                                        
                                        if (hasattr(pr, prev_needs_field) and getattr(pr, prev_needs_field) and
                                            hasattr(pr, prev_approved_field) and not getattr(pr, prev_approved_field)):
                                            is_next = False
                                            break
                                    
                                    if is_next:
                                        user_is_next_approver = True
                
                # Count the request if it's relevant to this user
                if user_is_next_approver or (user_is_approver and user_already_approved):
                    request_count += 1
            
            values['purchase_request_count'] = request_count
        
        return values

    @http.route(['/my/purchase_requests', '/my/purchase_requests/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_purchase_requests(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        PurchaseRequest = request.env['purchase.request']
        
        # We'll build a list of IDs of purchase requests requiring this user's approval
        # and those connected to this user as an approver (regardless of state)
        pending_approval_ids = []
        connected_request_ids = []
        
        # Get all purchase requests that might be relevant (including cancelled)
        potential_requests = PurchaseRequest.sudo().search([
            ('state', 'in', ['pending_approval', 'approved', 'po_created', 'cancelled'])
        ])
        
        # Pre-calculate approval status
        purchase_requests_with_status = []
        
        for pr in potential_requests:
            user_is_approver = False
            user_already_approved = False
            user_is_next_approver = False
            
            # Check each approver level
            for i in range(1, 15):
                needs_approver_field = f'needs_approver_level_{i}'
                is_approved_field = f'is_level_{i}_approved'
                approver_field = f'approver_level_{i}'
                
                # Check if this level is configured in this PR
                if hasattr(pr, needs_approver_field) and getattr(pr, needs_approver_field, False):
                    # Check if the current user is the approver at this level
                    if hasattr(pr, approver_field):
                        approver = getattr(pr, approver_field, False)
                        if approver and approver.user_id and approver.user_id.partner_id.id == partner.id:
                            user_is_approver = True
                            connected_request_ids.append(pr.id)
                            
                            # Check if this level is already approved
                            if hasattr(pr, is_approved_field) and getattr(pr, is_approved_field, False):
                                user_already_approved = True
                            # If not approved yet and PR is in pending_approval state
                            elif pr.state == 'pending_approval':
                                # Check if all previous levels are approved
                                is_next = True
                                for j in range(1, i):
                                    prev_needs_field = f'needs_approver_level_{j}'
                                    prev_approved_field = f'is_level_{j}_approved'
                                    
                                    if (hasattr(pr, prev_needs_field) and 
                                        getattr(pr, prev_needs_field, False) and
                                        hasattr(pr, prev_approved_field) and 
                                        not getattr(pr, prev_approved_field, False)):
                                        is_next = False
                                        break
                                
                                if is_next:
                                    user_is_next_approver = True
                                    pending_approval_ids.append(pr.id)
            
            # Only add PRs where the user is an approver
            if user_is_approver:
                # Calculate approval status
                approval_status = 'no_action'
                if user_is_next_approver:
                    approval_status = 'pending'
                elif user_already_approved:
                    approval_status = 'approved'
                elif pr.state == 'cancelled':
                    approval_status = 'cancelled'
                
                # Add PR with its calculated status
                purchase_requests_with_status.append({
                    'request': pr,
                    'approval_status': approval_status
                })
        
        # Filter requests based on filterby parameter (removed 'approved' filter)
        searchbar_filters = {
            'pending': {'label': _('Pending My Approval'), 'domain': [('id', 'in', pending_approval_ids)]},
            'all': {'label': _('All'), 'domain': [('id', 'in', connected_request_ids)]},
        }
        
        # Default filter is pending
        if not filterby or filterby not in searchbar_filters:
            filterby = 'pending'
        domain = searchbar_filters[filterby]['domain']
        
        # Sorting options
        searchbar_sortings = {
            'date': {'label': _('Date'), 'order': 'date_requested desc'},
            'name': {'label': _('Reference'), 'order': 'name desc'},
            'amount': {'label': _('Amount'), 'order': 'amount_total desc'},
            'state': {'label': _('Status'), 'order': 'state'},
        }
        
        # Default sort by date
        if not sortby:
            sortby = 'name'
        order = searchbar_sortings[sortby]['order']
        
        # Count for pager
        if filterby == 'pending':
            purchase_request_count = len(pending_approval_ids)
        else:  # 'all'
            purchase_request_count = len(connected_request_ids)
        
        # Pager
        pager = portal_pager(
            url="/my/purchase_requests",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby, 'filterby': filterby},
            total=purchase_request_count,
            page=page,
            step=self._items_per_page
        )
        
        # Content according to pager and order
        filtered_requests = PurchaseRequest.search(
            domain, 
            order=order, 
            limit=self._items_per_page, 
            offset=pager['offset']
        )
        
        # Get the status for each filtered request
        records_to_display = []
        for pr in filtered_requests:
            for pr_with_status in purchase_requests_with_status:
                if pr_with_status['request'].id == pr.id:
                    records_to_display.append(pr_with_status)
                    break
        
        values.update({
            'purchase_requests': records_to_display,
            'page_name': 'purchase_requests',
            'pager': pager,
            'default_url': '/my/purchase_requests',
            'searchbar_sortings': searchbar_sortings,
            'searchbar_filters': searchbar_filters,
            'sortby': sortby,
            'filterby': filterby,
        })
        
        return request.render("edge_module.portal_my_purchase_requests", values)

    @http.route(['/my/purchase_requests/<int:purchase_request_id>'], type='http', auth="user", website=True)
    def portal_my_purchase_request_detail(self, purchase_request_id, **kw):
        try:
            purchase_request_sudo = self._document_check_access('purchase.request', purchase_request_id)
        except (AccessError, MissingError):
            return request.redirect('/my')
            
        partner = request.env.user.partner_id
        is_next_approver = False
        has_approved = False
        is_approver = False
        
        # Simplified approach - check approval status
        for i in range(1, 15):
            needs_approver_field = f'needs_approver_level_{i}'
            is_approved_field = f'is_level_{i}_approved'
            approver_field = f'approver_level_{i}'
            
            if (hasattr(purchase_request_sudo, needs_approver_field) and 
                getattr(purchase_request_sudo, needs_approver_field, False) and
                hasattr(purchase_request_sudo, approver_field)):
                
                approver = getattr(purchase_request_sudo, approver_field, False)
                if approver and approver.user_id and approver.user_id.partner_id.id == partner.id:
                    is_approver = True
                    
                    # Check if this level is already approved
                    if hasattr(purchase_request_sudo, is_approved_field) and getattr(purchase_request_sudo, is_approved_field, False):
                        has_approved = True
                    elif purchase_request_sudo.state == 'pending_approval':
                        # Check if all previous levels are approved
                        is_next = True
                        for j in range(1, i):
                            prev_needs_field = f'needs_approver_level_{j}'
                            prev_approved_field = f'is_level_{j}_approved'
                            
                            if (hasattr(purchase_request_sudo, prev_needs_field) and 
                                getattr(purchase_request_sudo, prev_needs_field, False) and
                                hasattr(purchase_request_sudo, prev_approved_field) and 
                                not getattr(purchase_request_sudo, prev_approved_field, False)):
                                is_next = False
                                break
                        
                        if is_next:
                            is_next_approver = True
        
        # Only allow viewing if user is an approver for this request
        if not is_approver:
            return request.redirect('/my')
            
        values = {
            'purchase_request': purchase_request_sudo,
            'page_name': 'purchase_request_detail',
            'is_approver': is_next_approver,
            'has_approved': has_approved,
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
        for i in range(1, 15):
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

            # Post message in chatter
            purchase_request_sudo.sudo().message_post(
                body=_("Approved by %s through the portal.") % (partner.name),
                message_type='notification',
                subtype_xmlid='mail.mt_comment'
            )
            
            # Check if fully approved
            if purchase_request_sudo.sudo().is_fully_approved():
                purchase_request_sudo.sudo().write({'state': 'approved'})
                
                # Send Teams notification for fully approved request
                purchaser = purchase_request_sudo.sudo().purchaser_id
                
                if purchaser and purchaser.email:
                    # Get the base URL for links
                    base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
                    url = f"{base_url}/web#id={purchase_request_sudo.id}&view_type=form&model={purchase_request_sudo._name}"
                    url_text = "View Purchase Request"
                    
                    title = "Purchase Request Has Been Fully Approved"
                    
                    # Construct message
                    message = f"""
                            Purchase Request {purchase_request_sudo.name} was fully approved<br>
                            Request details:<br>
                            - Requester: {purchase_request_sudo.requester_id.name}<br>
                            - Need by Date: {purchase_request_sudo.need_by_date}<br>
                            - Production Impact: {purchase_request_sudo.production_stoppage_display}<br>
                            - Total Amount: {purchase_request_sudo.currency_id.symbol} {purchase_request_sudo.amount_total:,.2f}
                            """
                    
                    TeamsLib().send_message("jmacfarlane@edgeautonomy.io", message, title, url, url_text)
                else:
                    _logger.error(f"Could not find valid purchaser email for purchase request: {purchase_request_sudo.name}")
            else:
                purchase_request_sudo.sudo()._notify_next_approver()
            
        return request.redirect('/my/purchase_requests')
    
    @http.route(['/my/purchase_requests/<int:purchase_request_id>/cancel'], type='http', auth="user", website=True, methods=['POST'])
    def portal_cancel_purchase_request(self, purchase_request_id, **kw):
        try:
            purchase_request_sudo = self._document_check_access('purchase.request', purchase_request_id)
        except (AccessError, MissingError):
            return request.redirect('/my')
            
        # Check if the user is an approver for this purchase request
        partner = request.env.user.partner_id
        is_approver = False
        
        # Check each approver level to see if user is an approver
        for i in range(1, 15):
            approver_field = f'approver_level_{i}'
            if hasattr(purchase_request_sudo, approver_field):
                approver = getattr(purchase_request_sudo, approver_field, False)
                if approver and approver.user_id and approver.user_id.partner_id.id == partner.id:
                    is_approver = True
                    break
        
        # Only allow cancellation if request is in pending_approval state and user is an approver
        if is_approver and purchase_request_sudo.state == 'pending_approval':
            # Get cancellation reason if provided
            cancel_reason = kw.get('cancel_reason', '')
            
            # Cancel the request
            purchase_request_sudo.sudo().write({'state': 'cancelled'})
            
            # Post message in chatter
            message = _("Request denied by %s through the portal.") % partner.name
            if cancel_reason:
                message += _(" Reason: %s") % cancel_reason
                
            purchase_request_sudo.sudo().message_post(
                body=message,
                message_type='notification',
                subtype_xmlid='mail.mt_comment'
            )
        
        return request.redirect('/my/purchase_requests')
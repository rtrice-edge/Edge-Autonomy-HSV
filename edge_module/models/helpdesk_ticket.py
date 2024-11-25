from odoo import models, fields, api

class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order')
    purchase_order_line_id = fields.Many2one('purchase.order.line', string='Purchase Order Line', domain="[('order_id', '=', purchase_order_id)]")
    subtype = fields.Selection([
        ('no_cofc', 'No CofC'),
        ('overshipped', 'Overshipped'),
        ('no_packing_slip', 'PO Arrived with no Packing Slip'),
        ('short_shipped', 'Short Shipped'),
        ('other', 'Other')
    ], string='Subtype')

    stock_picking_id = fields.Many2one('stock.picking', string='Receipt')

    def send_helpdesk_teams_notification(webhook_url, ticket):
        """Send formatted Teams notification for new helpdesk ticket"""
        import requests
        import json
        
        # Get related record names safely
        po_name = ticket.purchase_order_id.name if ticket.purchase_order_id else 'N/A'
        po_line = ticket.purchase_order_line_id.name if ticket.purchase_order_line_id else 'N/A'
        receipt = ticket.stock_picking_id.name if ticket.stock_picking_id else 'N/A'
        
        # Build ticket URL - adjust base URL as needed
        base_url = ticket.env['ir.config_parameter'].sudo().get_param('web.base.url')
        ticket_url = f"{base_url}/web#id={ticket.id}&model=helpdesk.ticket&view_type=form"
        
        payload = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": "0076D7",
            "summary": f"New Helpdesk Ticket: {ticket.name}",
            "sections": [{
                "activityTitle": "🎫 New Helpdesk Ticket Created",
                "activitySubtitle": ticket.name,
                "facts": [
                    {"name": "Subtype", "value": dict(ticket._fields['subtype'].selection).get(ticket.subtype, 'N/A')},
                    {"name": "Purchase Order", "value": po_name},
                    {"name": "PO Line", "value": po_line},
                    {"name": "Receipt", "value": receipt}
                ],
                "markdown": True
            }],
            "potentialAction": [{
                "@type": "OpenUri",
                "name": "View Ticket",
                "targets": [{"os": "default", "uri": ticket_url}]
            }]
        }
        
        try:
            response = requests.post(
                webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json'}
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Error sending Teams notification: {e}")
            return False

    @api.onchange('purchase_order_id')
    def _onchange_purchase_order_id(self):
        self.purchase_order_line_id = False
        
    @api.model
    def create(self, vals):
        # Create the ticket
        ticket = super(HelpdeskTicket, self).create(vals)
        
        # Add email to followers
        partner = self.env['res.partner'].search([('email', '=', 'hsvreceiving@edgeautomony.io')], limit=1)
        if partner:
            ticket.message_subscribe(partner_ids=[partner.id])
        else:
            # Create partner if doesn't exist
            partner = self.env['res.partner'].create({
                'name': 'HSV Receiving',
                'email': 'hsvreceiving@edgeautomony.io'
            })
            ticket.message_subscribe(partner_ids=[partner.id])
        
        # Replace 'your_webhook_url' with the URL you copied when you created the webhook
        webhook_url = "https://jenaero.webhook.office.com/webhookb2/b420a0ff-bfb1-4d82-8346-e290d675b0d7@1876f61a-3bdb-4843-ae70-75ed0ccb7404/IncomingWebhook/8c62e8c5b8dc40698beeae3e8b4adeed/1f4d666c-833c-435c-aab4-6b002d4a2b44/V2vXokV2krzuxCySmW6FBn3P573ZyzQE6P9JnRpV9P8oU1"

        #Sending a message
        self.send_helpdesk_teams_notification(self, webhook_url, ticket)
        
            
        return ticket
    
    

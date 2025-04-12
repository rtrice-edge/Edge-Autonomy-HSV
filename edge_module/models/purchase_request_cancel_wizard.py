from odoo import api, fields, models, _

class PurchaseRequestCancelWizard(models.TransientModel):
    _name = 'purchase.request.cancel.wizard'
    _description = 'Purchase Request Cancellation Wizard'

    reason = fields.Text(string='Reason for cancellation')
    
    def action_confirm_cancel(self):
        """Confirm the cancellation of the purchase request"""
        request_id = self.env.context.get('active_id')
        if request_id:
            request = self.env['purchase.request'].browse(request_id)
            
            # Post message in the chatter
            message = _("Request denied")
            if self.reason:
                message = _("Denied. Reason: %s") % self.reason
                
            request.message_post(
                body=message,
                message_type='notification',
                subtype_xmlid='mail.mt_comment'
            )
            
            # Set state to cancelled
            request.write({'state': 'cancelled'})
            
        return {'type': 'ir.actions.act_window_close'}
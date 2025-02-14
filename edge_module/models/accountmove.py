from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = 'account.move'

    jamis_bill_ids = fields.One2many('jamis.bills', 'move_id', string='Jamis Bills')

    def action_add_bill_to_jamis(self):
        # This method will be called when the button is clicked
        # For now, we'll just pass and implement the logic later
        pass

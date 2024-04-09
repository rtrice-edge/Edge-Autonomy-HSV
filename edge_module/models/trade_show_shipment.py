from odoo import models, fields

class TradeShowShipment(models.Model):
    _name = 'trade.show.shipment'
    _description = 'Trade Show Shipment'

    name = fields.Char(string='Name', required=True)
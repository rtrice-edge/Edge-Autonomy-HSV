from odoo import models, fields

class TradeShowShipment(models.Model):
    _name = 'trade.show.shipment'
    _description = 'Trade Show Shipment'

    name = fields.Char(string='Name', required=True)
    shipper = fields.Char(string='Shipper')
    tracking_number = fields.Char(string='Tracking Number')
    ship_date = fields.Datetime(string='Ship Date')
    arrival_date = fields.Datetime(string='Arrival Date')
    return_date = fields.Datetime(string='Return Date')
    trade_show_id = fields.Many2one('trade.show', string='Trade Show')
    shipment_lines = fields.One2many('trade.show.shipment.line', 'shipment_id', string='Shipment Lines')
    palletized = fields.Boolean(string='Palletized')
    pallet_count = fields.Integer(string='Pallet Count')
    shipped_by = fields.Char(string='Shipped By')
    shipped = fields.Boolean(string='Shipped')
    returned = fields.Boolean(string='Returned')
    
    notes = fields.Text(string='Notes')
    
class TradeShowShipmentLine(models.Model):
    _name = 'trade.show.shipment.line'
    _description = 'Trade Show Shipment Line'
    
    
    shipment_id = fields.Many2one('trade.show.shipment', string='Shipment')
    equipment_id = fields.Many2one('trade.show.equipment', string='Equipment')

    home_location_id = fields.Many2one('trade.show.equipment.home.location', string='Home Location')
    
    notes = fields.Text(string='Notes')

    
class TradeShowEquipment(models.Model):
    _name = 'trade.show.equipment'
    _description = 'Trade Show Equipment'
    
    name = fields.Char(string='Name', required=True)
    description = fields.Text(string='Description')
    home_location_id = fields.Many2one('trade.show.equipment.home.location', string='Home Location')

    notes = fields.Text(string='Notes')
    
class TradeShow(models.Model):
    _name = 'trade.show'
    _description = 'Trade Show'
    
    
    name = fields.Char(string='Name', required=True)
    description = fields.Text(string='Description')
    
    street_address_1 = fields.Char(string='Street Address 1')
    street_address_2 = fields.Char(string='Street Address 2')
    city = fields.Char(string='City')
    state = fields.Char(string='State')
    zip_code = fields.Char(string='Zip Code')
    country = fields.Char(string='Country')
    
    check_in_time = fields.Datetime(string='Check In Time')
    check_out_time = fields.Datetime(string='Check Out Time')
    
    trade_show_start = fields.Datetime(string='Trade Show Start')
    trade_show_end = fields.Datetime(string='Trade Show End')
    website = fields.Char(string='Website') 
    
    booth_requirements = fields.Text(string='Booth Requirements')
    shipments = fields.One2many('trade.show.shipment', 'trade_show_id', string='Shipments')
    notes = fields.Text(string='Notes')
    
    
class TradeShowEquipmentHomeLocation(models.Model):
    _name = 'trade.show.equipment.home.location'
    _description = 'Trade Show Equipment Home Location'
    
    name = fields.Char(string='Name', required=True)
    address = fields.Char(string='Address')
    city = fields.Char(string='City')
    state = fields.Char(string='State')
    zip_code = fields.Char(string='Zip Code')
    
    
    

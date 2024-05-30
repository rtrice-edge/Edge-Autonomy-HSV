from odoo import models, fields, api

class TradeShowShipment(models.Model):
    _name = 'trade.show.shipment'
    _description = 'Trade Show Shipment'

    name = fields.Char(string='Name', required=True)
    frieght_forwarder_id = fields.Many2one('trade.show.freight.forwarder', string='Freight Forwarder')
    tracking_number = fields.Char(string='Tracking Number')
    ship_date = fields.Datetime(string='Ship Date')
    arrival_date = fields.Datetime(string='Arrival Date')
    return_date = fields.Datetime(string='Return Date')
    trade_show_id = fields.Many2one('trade.show', string='Trade Show')
    shipment_lines = fields.One2many('trade.show.shipment.line', 'shipment_id', string='Shipment Lines')
    palletized = fields.Boolean(string='Palletized')
    pallet_count = fields.Integer(string='Pallet Count')
    shipped_by = fields.Char(string='Shipped By')
    from_location = fields.Many2one('trade.show.equipment.location', string='From Location')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('shipped', 'Shipped'),
        ('returned', 'Returned')
    ], string='Status', default='draft', tracking=True)
    notes = fields.Text(string='Notes')

    def create_transfer_history(self):
        for line in self.shipment_lines:
            self.env['trade.show.equipment.transfer'].create({
                'equipment_id': line.equipment_id.id,
                'from_location_id': self.from_location.id,
                'to_location_id': self.trade_show_id.location.id,
                'transfer_date': self.ship_date,
                'notes': line.notes,
            })

    def mark_as_shipped(self):
        self.ensure_one()
        self.state = 'shipped'
        self.create_transfer_history()

    def mark_as_returned(self):
        self.ensure_one()
        self.state = 'returned'
        for line in self.shipment_lines:
            self.env['trade.show.equipment.transfer'].create({
                'equipment_id': line.equipment_id.id,
                'from_location_id': self.trade_show_id.location.id,
                'to_location_id': self.from_location.id,
                'transfer_date': self.return_date,
                'notes': line.notes,
            })

class TradeShowShipmentLine(models.Model):
    _name = 'trade.show.shipment.line'
    _description = 'Trade Show Shipment Line'

    shipment_id = fields.Many2one('trade.show.shipment', string='Shipment')
    equipment_id = fields.Many2one('trade.show.equipment', string='Equipment')
    equipment_serial = fields.Char(string='Serial Number', related='equipment_id.serial_number', store=True)

    notes = fields.Text(string='Notes')

class TradeShowEquipment(models.Model):
    _name = 'trade.show.equipment'
    _description = 'Trade Show Equipment'

    name = fields.Char(string='Name', required=True)
    description = fields.Text(string='Description')
    serial_number = fields.Char(string='Serial Number')
    model_number = fields.Char(string='Model Number')
    jursidiction = fields.Char(string='Jurisdiction')
    usml_category = fields.Char(string='USML Category')
    eccn_number = fields.Char(string='ECCN')
    ushts_number = fields.Char(string='USHTS/HS')
    coo = fields.Char(string='COO')
    license = fields.Char(string='License')
    license_line_number = fields.Char(string='License Line Number')
    manufacturer = fields.Char(string='Manufacturer')
    value = fields.Float(string='Value')
    weight = fields.Float(string='Weight')
    equipment_type = fields.Selection([('dummy', 'Dummy'), ('operational', 'Operational'), ('dgd', 'Dangerous Goods'), ('other', 'Other')], string='Equipment Type')
    transfer_history_ids = fields.One2many('trade.show.equipment.transfer', 'equipment_id', string='Transfer History')
    notes = fields.Text(string='Notes')
    current_location = fields.Many2one('trade.show.equipment.location', string='Current Location', compute='_compute_current_location', store=True)

    @api.depends('transfer_history_ids.to_location_id')
    def _compute_current_location(self):
        for equipment in self:
            last_transfer = equipment.transfer_history_ids.sorted(key=lambda r: r.transfer_date, reverse=True)
            equipment.current_location = last_transfer[0].to_location_id if last_transfer else False
    


class TradeShowFreightForwarder(models.Model):
    _name = 'trade.show.freight.forwarder'
    _description = 'Trade Show Freight Forwarder'

    name = fields.Char(string='Name', required=True)
    address = fields.Char(string='Address')
    city = fields.Char(string='City')
    state = fields.Char(string='State')
    zip_code = fields.Char(string='Zip Code')
    country = fields.Char(string='Country')
    contact = fields.Char(string='Contact')
    phone = fields.Char(string='Phone')
    email = fields.Char(string='Email')
    notes = fields.Text(string='Notes')

class TradeShow(models.Model):
    _name = 'trade.show'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Trade Show'

    name = fields.Char(string='Name', required=True)
    description = fields.Text(string='Description')
    location = fields.Many2one('trade.show.equipment.location', string='Location')
    check_in_time = fields.Datetime(string='Check In Time')
    check_out_time = fields.Datetime(string='Check Out Time')
    trade_show_start = fields.Datetime(string='Trade Show Start')
    trade_show_end = fields.Datetime(string='Trade Show End')
    website = fields.Char(string='Website')
    booth_requirements = fields.Text(string='Booth Requirements')
    shipments = fields.One2many('trade.show.shipment', 'trade_show_id', string='Shipments')
    notes = fields.Text(string='Notes')

class TradeShowEquipmentLocation(models.Model):
    _name = 'trade.show.equipment.location'
    _description = 'Trade Show Equipment Location'

    name = fields.Char(string='Name', required=True)
    street_address_1 = fields.Char(string='Street Address 1')
    street_address_2 = fields.Char(string='Street Address 2')
    city = fields.Char(string='City')
    state = fields.Char(string='State')
    zip_code = fields.Char(string='Zip Code')
    country = fields.Char(string='Country')

class TradeShowEquipmentTransfer(models.Model):
    _name = 'trade.show.equipment.transfer'
    _description = 'Trade Show Equipment Transfer'

    equipment_id = fields.Many2one('trade.show.equipment', string='Equipment', required=True)
    from_location_id = fields.Many2one('trade.show.equipment.location', string='From Location')
    to_location_id = fields.Many2one('trade.show.equipment.location', string='To Location')
    transfer_date = fields.Datetime(string='Transfer Date')
    notes = fields.Text(string='Notes')
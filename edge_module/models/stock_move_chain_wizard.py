from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)

class StockMoveChainWizard(models.TransientModel):
    _name = 'stock.move.chain.wizard'
    _description = 'Stock Move Chain Wizard'

    purchase_line_id = fields.Many2one('purchase.order.line', string='Purchase Order Line', readonly=True)
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    move_line_ids = fields.One2many('stock.move.chain.line', 'wizard_id', string='Move Chain')

class StockMoveChainLine(models.TransientModel):
    _name = 'stock.move.chain.line'
    _description = 'Stock Move Chain Line'
    _order = 'sequence, id'

    wizard_id = fields.Many2one('stock.move.chain.wizard', string='Wizard')
    sequence = fields.Integer(string='Sequence', default=10)
    move_id = fields.Many2one('stock.move', string='Stock Move')
    picking_type = fields.Char(string='Operation Type')
    state = fields.Selection([
        ('draft', 'New'),
        ('cancel', 'Cancelled'),
        ('waiting', 'Waiting Another Move'),
        ('confirmed', 'Waiting'),
        ('assigned', 'Ready'),
        ('done', 'Done')
    ], string='Status')
    reference = fields.Char(string='Reference')
    source_location = fields.Char(string='Source Location')
    destination_location = fields.Char(string='Destination Location')
    date = fields.Datetime(string='Date')
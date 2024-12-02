from odoo import models, fields, api
from datetime import datetime
import logging
_logger = logging.getLogger(__name__)

class CycleCount(models.Model):
    _name = 'inventory.cycle.count'
    _description = 'Inventory Cycle Count'

    date = fields.Date(string='Cycle Count Date', required=True, default=fields.Date.today)
    count_type = fields.Selection([
        ('full', 'Full'),
        ('monthly', 'Monthly'),
        ('custom', 'Custom')
    ], string='Count Type', required=True, default='full')
    percent_a = fields.Float(string='Percent A', default=100, help="Percentage of A category products to count")
    percent_b = fields.Float(string='Percent B', help="Percentage of B category products to count")
    percent_c = fields.Float(string='Percent C', help="Percentage of C category products to count")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('done', 'Done')
    ], string='Status', default='draft', compute='_compute_state', store=True)
    log_ids = fields.One2many('inventory.cycle.count.log', 'cycle_count_id', string='Count Logs')
    remaining_items_count = fields.Integer(string='Remaining Items to Count', compute='_compute_remaining_items', store=True)

    @api.depends('date')
    def _compute_remaining_items(self):
        for record in self:
            quants = self.env['stock.quant'].search([('inventory_date', '=', record.date)])
            record.remaining_items_count = len(quants)

    @api.depends('remaining_items_count')
    def _compute_state(self):
        for record in self:
            if record.remaining_items_count == 0 and record.state != 'draft':
                record.state = 'done'
            elif record.state == 'draft' and record.remaining_items_count > 0:
                record.state = 'in_progress'

    @api.onchange('count_type')
    def _onchange_count_type(self):
        if self.count_type == 'full':
            self.percent_a = self.percent_b = self.percent_c = 100
        elif self.count_type == 'monthly':
            self.percent_a, self.percent_b, self.percent_c = 100, 35, 12
            
            
    @api.model
    def create(self, vals):
        _logger.error("Starting create method for CycleCount")
        new_record = super(CycleCount, self).create(vals)
        
        try:
            StockQuant = self.env['stock.quant']
            batch_size = 500  # Process records in smaller chunks
            
            # Get all stock quants for storable products, ordered by last count date
            quants = StockQuant.search([
                ('product_id.type', '=', 'product'),
                ('location_id.complete_name', 'not ilike', 'NCR%'),
                ('location_id.complete_name', 'not ilike', 'Quality%'),
                ('location_id.complete_name', 'not ilike', 'QC%'),
                ('location_id.complete_name', 'not ilike', 'Partners%'),
                ('location_id.complete_name', 'not ilike', 'Virtual Locations%'),
            ], order='inventory_date asc, in_date asc')

            _logger.error(f"Total quants found: {len(quants)}")

            # Group quants by inventory category
            quants_by_category = {
                'A': quants.filtered(lambda q: q.product_id.product_inventory_category == 'A'),
                'B': quants.filtered(lambda q: q.product_id.product_inventory_category == 'B'),
                'C': quants.filtered(lambda q: q.product_id.product_inventory_category == 'C')
            }

            _logger.error(f"Quants by category - A: {len(quants_by_category['A'])}, B: {len(quants_by_category['B'])}, C: {len(quants_by_category['C'])}")

            # Calculate number of quants to count for each category
            count_a = int(len(quants_by_category['A']) * (new_record.percent_a / 100))
            count_b = int(len(quants_by_category['B']) * (new_record.percent_b / 100))
            count_c = int(len(quants_by_category['C']) * (new_record.percent_c / 100))

            _logger.error(f"Quants to count - A: {count_a}, B: {count_b}, C: {count_c}")

            # Select quants to count
            quants_to_count = StockQuant.browse()
            for category in ['A', 'B', 'C']:
                count = locals()[f'count_{category.lower()}']
                category_quants = quants_by_category[category][:count]
                quants_to_count |= category_quants

            total_quants = len(quants_to_count)
            _logger.error(f"Total quants selected for counting: {total_quants}")

            # Process in batches with error handling and commit
            processed_count = 0
            for i in range(0, total_quants, batch_size):
                batch = quants_to_count[i:i + batch_size]
                try:
                    # Update inventory_date for current batch
                    batch.write({'inventory_date': new_record.date})
                    processed_count += len(batch)
                    
                    # Commit the transaction for this batch
                    self.env.cr.commit()
                    
                    _logger.error(f"Processed batch {i//batch_size + 1}: {processed_count}/{total_quants} quants updated")
                    
                except Exception as batch_error:
                    _logger.exception(f"Error processing batch {i//batch_size + 1}:")
                    self.env.cr.rollback()
                    # Continue with next batch instead of failing completely
                    continue

            if processed_count < total_quants:
                _logger.warning(f"Not all quants were processed: {processed_count}/{total_quants}")

            new_record.write({'state': 'in_progress'})
            _logger.error(f"Updated cycle count record with ID: {new_record.id} to 'in_progress' state")

        except Exception as e:
            _logger.exception("An error occurred in create method of CycleCount:")
            self.env.cr.rollback()
            raise

        _logger.error("Finished create method for CycleCount")
        return new_record
    
class CycleCountLog(models.Model):
    _name = 'inventory.cycle.count.log'
    _description = 'Inventory Cycle Count Log'

    cycle_count_id = fields.Many2one('inventory.cycle.count', string='Cycle Count', required=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    lot_id = fields.Many2one('stock.lot', string='Lot/Serial Number')
    expected_quantity = fields.Float(string='Expected Quantity')
    actual_quantity = fields.Float(string='Actual Quantity')
    location_id = fields.Many2one('stock.location', string='Location',required=True)
    difference = fields.Float(string='Difference', compute='_compute_difference', store=True)
    planned_count_date = fields.Date(string='Planned Count Date', related='cycle_count_id.date', store=True)
    actual_count_date = fields.Datetime(string='Actual Count Date', default=fields.Datetime.now)
    user_id = fields.Many2one('res.users', string='Counted By', default=lambda self: self.env.user)

    @api.depends('expected_quantity', 'actual_quantity')
    def _compute_difference(self):
        for record in self:
            record.difference = record.actual_quantity - record.expected_quantity
    
    @api.model
    def read(self, fields=None, load='_classic_read'):
        try:
            return super().read(fields=fields, load=load)
        except AttributeError as e:
            _logger.error(f"AttributeError in CycleCountLog read method: {str(e)}")
            for record in self:
                for field in self._fields:
                    try:
                        value = record[field]
                        _logger.info(f"Field {field}: {value} (type: {type(value)})")
                    except Exception as field_error:
                        _logger.error(f"Error accessing field {field}: {str(field_error)}")
            raise

    @api.model
    def create(self, vals):
        for field, value in vals.items():
            _logger.info(f"Creating CycleCountLog - Field {field}: {value} (type: {type(value)})")
        return super().create(vals)

    def write(self, vals):
        for field, value in vals.items():
            _logger.info(f"Updating CycleCountLog - Field {field}: {value} (type: {type(value)})")
        return super().write(vals)

# wizards/cycle_count_date_wizard.py
class CycleCountDateWizard(models.TransientModel):
    _name = 'cycle.count.date.wizard'
    _description = 'Cycle Count Date Selection Wizard'

    date = fields.Date(string='Planned Date', required=True)

    # @api.model
    # def _get_unique_dates(self):
    #     # Fetch distinct planned_count_date values from logs
    #     self.env.cr.execute("""
    #         SELECT DISTINCT planned_count_date 
    #         FROM inventory_cycle_count_log 
    #         WHERE planned_count_date IS NOT NULL
    #         ORDER BY planned_count_date
    #     """)
    #     result = self.env.cr.fetchall()
    #     return [(row[0], row[0]) for row in result]  # Return tuples (value, label)

    def print_report(self):
        logs = self.env['inventory.cycle.count.log'].search([
            ('planned_count_date', '=', self.date.planned_count_date)
        ])
        if not logs:
            raise UserError("No logs found for the selected date.")
        return self.env.ref('inventory_cycle_count.action_report_cycle_count').report_action(logs)

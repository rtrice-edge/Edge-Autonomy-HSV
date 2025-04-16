# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero
import logging
import pytz # For timezone handling

_logger = logging.getLogger(__name__)

class HistoricalStockReportWizard(models.TransientModel):
    _name = 'historical.stock.report.wizard'
    _description = 'Historical Stock Report Wizard'

    date_snapshot = fields.Datetime(
        string='Snapshot Date & Time',
        required=True,
        default=fields.Datetime.now,
        help="The report will show quantities as they were at this exact point in time (in your timezone)."
    )
    location_id = fields.Many2one(
        'stock.location',
        string='Location',
        required=True,
        domain="[('usage', '=', 'internal')]",
        help="Select the parent location. Stock from this location and all its children will be included."
    )
    include_zero_quantities = fields.Boolean(
        string="Include Products with Zero Quantity",
        default=False,
        help="Show lines even if the calculated quantity at the snapshot date was zero (but the product moved through the location)."
    )
    # Optional: Add filters like product category, specific products etc. later if needed

    def action_generate_report(self):
        self.ensure_one()
        ReportLine = self.env['historical.stock.report.line']
        StockLocation = self.env['stock.location']
        ProductProduct = self.env['product.product']
        StockProductionLot = self.env['stock.lot']
        UomUom = self.env['uom.uom']
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')

        # --- Date Handling (same as before) ---
        user_tz = pytz.timezone(self.env.user.tz or 'UTC')
        local_dt_aware = user_tz.localize(fields.Datetime.to_datetime(self.date_snapshot), is_dst=None) # Error handling might be needed if already aware
        date_snapshot_utc = local_dt_aware.astimezone(pytz.utc)
        _logger.info("Snapshot Date (User): %s, Converted to UTC: %s", self.date_snapshot, date_snapshot_utc)

        # --- Location Handling (fetch name now) ---
        target_location_id = self.location_id.id
        target_location_name = self.location_id.display_name # Get name now
        child_location_ids = StockLocation.search([('id', 'child_of', target_location_id), ('usage', '=', 'internal')]).ids
        if not child_location_ids:
            raise UserError(_("Selected location '%s' has no usable child locations (including itself).") % target_location_name)
        _logger.info("Target Location: %s (ID: %d). Including child IDs: %s", target_location_name, target_location_id, child_location_ids)

        # --- Query Stock Move Lines (same as before) ---
        domain = [
            ('date', '<=', date_snapshot_utc),
            ('state', '=', 'done'),
            ('product_id.type', '=', 'product'),
            '|',
                ('location_id', 'in', child_location_ids),
                ('location_dest_id', 'in', child_location_ids),
        ]
        fields_to_read = ['product_id', 'lot_id', 'qty_done', 'location_id', 'location_dest_id', 'product_uom_id'] # Fetch UoM ID from line

        _logger.info("Searching stock.move.line with domain: %s", domain)
        move_lines_data = self.env['stock.move.line'].search_read(domain, fields_to_read, order='date asc, id asc') # Ensure order
        _logger.info("Found %d relevant stock move lines.", len(move_lines_data))

        if not move_lines_data:
             raise UserError(_("No stock movements found for location '%s' up to the specified date.") % target_location_name)

        # --- Process Data (same logic, just track IDs) ---
        stock_levels = {} # Key: (product_id, lot_id), Value: {'qty': quantity, 'uom_id': uom_id}
        all_product_ids = set()
        all_lot_ids = set()
        all_uom_ids = set()

        for line in move_lines_data:
            product_id = line['product_id'][0] if line.get('product_id') else None
            lot_id = line['lot_id'][0] if line.get('lot_id') else None
            uom_id = line['product_uom_id'][0] if line.get('product_uom_id') else None # UoM from move line
            qty = line.get('qty_done', 0.0)
            loc_from_id = line['location_id'][0] if line.get('location_id') else None
            loc_to_id = line['location_dest_id'][0] if line.get('location_dest_id') else None

            if not product_id or not uom_id:
                _logger.debug("Skipping move line %s: missing product or uom", line.get('id'))
                continue # Skip lines without product or UOM

            key = (product_id, lot_id)
            # Initialize if key not seen before
            if key not in stock_levels:
                stock_levels[key] = {'qty': 0.0, 'uom_id': uom_id} # Store last known UoM? Or product's default? Let's take last known.

            current_qty = stock_levels[key]['qty']
            # Update UoM in case it changed (unlikely for same product/lot key but possible)
            stock_levels[key]['uom_id'] = uom_id

            is_in = loc_to_id in child_location_ids and loc_from_id not in child_location_ids
            is_out = loc_from_id in child_location_ids and loc_to_id not in child_location_ids

            # Here we assume qty_done is in the UoM specified by product_uom_id
            # If calculations needed conversion to product's primary UoM, it would happen here.
            # For simplicity, we assume direct summation is desired based on move line UoM.
            if is_in:
                stock_levels[key]['qty'] = current_qty + qty
            elif is_out:
                stock_levels[key]['qty'] = current_qty - qty

            # Collect all unique IDs needed for fetching details later
            all_product_ids.add(product_id)
            if lot_id: all_lot_ids.add(lot_id)
            all_uom_ids.add(uom_id)

        _logger.info("Processed move lines. Calculated %d preliminary stock level entries.", len(stock_levels))

        # --- Pre-fetch names and codes ---
        product_info = {p['id']: p for p in ProductProduct.with_context(active_test=False).search_read(
            [('id', 'in', list(all_product_ids))],
            ['display_name', 'default_code', 'standard_price'] # No need for uom_id here now
        )}
        lot_info = {l['id']: l['name'] for l in StockProductionLot.with_context(active_test=False).search_read(
            [('id', 'in', list(all_lot_ids))], ['name']
        )}
        uom_info = {u['id']: u['name'] for u in UomUom.with_context(active_test=False).search_read(
            [('id', 'in', list(all_uom_ids))], ['name']
        )}
        _logger.info("Fetched details for %d products, %d lots, %d UoMs", len(product_info), len(lot_info), len(uom_info))

        # --- Prepare Report Lines ---
        report_lines_vals = []
        missing_product_count = 0
        missing_lot_count = 0
        missing_uom_count = 0

        for key, data in stock_levels.items():
            product_id, lot_id = key
            quantity = data['qty']
            uom_id = data['uom_id']

            if not self.include_zero_quantities and float_is_zero(quantity, precision_digits=precision):
                continue

            p_data = product_info.get(product_id)
            lot_name = lot_info.get(lot_id) if lot_id else "[No Lot]"
            uom_name = uom_info.get(uom_id)

            # --- Handle missing records gracefully ---
            if not p_data:
                 product_name = f"[Missing Product ID: {product_id}]"
                 product_code = ""
                 cost = 0.0
                 missing_product_count += 1
            else:
                 product_name = p_data.get('display_name', f"[Product ID: {product_id}]")
                 product_code = p_data.get('default_code', "")
                 cost = p_data.get('standard_price', 0.0)

            if lot_id and not lot_name:
                 lot_name = f"[Missing Lot ID: {lot_id}]"
                 missing_lot_count += 1

            if not uom_name:
                 uom_name = f"[Missing UoM ID: {uom_id}]"
                 missing_uom_count += 1
            # --- End graceful handling ---

            vals = {
                'report_date': self.date_snapshot,
                'report_location_id': self.location_id.id,
                'report_location_name': target_location_name, # Store location name
                'product_id': product_id, # Store ID for reference
                'product_default_code': product_code, # Store code
                'product_name': product_name, # Store name
                'lot_id': lot_id, # Store ID for reference (False if no lot)
                'lot_name': lot_name, # Store name (or placeholder)
                'uom_id': uom_id, # Store ID for reference
                'uom_name': uom_name, # Store name (or placeholder)
                'quantity': quantity,
                'cost': cost,
                # total_value is computed
            }
            report_lines_vals.append(vals)

        if missing_product_count or missing_lot_count or missing_uom_count:
             _logger.warning("Missing related records during report line preparation: Products=%d, Lots=%d, UoMs=%d",
                             missing_product_count, missing_lot_count, missing_uom_count)

        _logger.info("Prepared %d report line values.", len(report_lines_vals))

        # --- Create Report Lines & Return Action (same as before) ---
        if not report_lines_vals:
             raise UserError(_("No stock records with non-zero quantity found for the specified criteria (or 'Include Zero Quantities' was not checked)."))

        try:
             _logger.info("Creating historical.stock.report.line records...")
             # Using with_context active_test=False for search_read above helps find archived records if needed
             created_lines = ReportLine.create(report_lines_vals)
             _logger.info("Successfully created %d report line records.", len(created_lines))
             created_line_ids = created_lines.ids
        except Exception as e:
             _logger.error("Failed to create historical report lines: %s", e, exc_info=True)
             raise UserError(_("Failed to create report lines. Check server logs for details. Error: %s") % e)

        action = {
            'name': _('Historical Stock Report'),
            'type': 'ir.actions.act_window',
            'res_model': 'historical.stock.report.line',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', created_line_ids)],
            'target': 'current',
            'context': {'create': False, 'search_default_group_by_product': 1}
        }
        return action


# models/historical_stock_report.py
# (Wizard class remains the same)

class HistoricalStockReportLine(models.Model):
    _name = 'historical.stock.report.line'
    _description = 'Historical Stock Report Line'
    _order = 'report_date desc, product_id, lot_id'

    # --- Fields storing report parameters ---
    report_date = fields.Datetime(string="Snapshot Date", readonly=True, index=True)
    report_location_id = fields.Many2one('stock.location', string="Report Location", readonly=True)
    # Add location name for convenience
    report_location_name = fields.Char(string="Location Name", readonly=True)

    # --- Product Info (Keep IDs for reference/linking, store names/codes) ---
    product_id = fields.Many2one(
        'product.product', string='Product Ref', readonly=True, index=True
    )
    product_default_code = fields.Char(string='Internal Reference', readonly=True)
    product_name = fields.Char(string='Product Name', readonly=True) # Changed from description

    # --- Lot Info ---
    lot_id = fields.Many2one(
        'stock.lot', string='Lot/Serial Ref', readonly=True, index=True
    )
    lot_name = fields.Char(string='Lot/Serial Number', readonly=True) # Store name

    # --- UoM Info ---
    uom_id = fields.Many2one('uom.uom', string='UoM Ref', readonly=True)
    uom_name = fields.Char(string='Unit of Measure', readonly=True) # Store name

    # --- Calculated Values ---
    quantity = fields.Float(string='Quantity', readonly=True, digits='Product Unit of Measure')
    cost = fields.Float(string='Unit Cost', readonly=True, digits='Product Price', help="Current standard cost of the product at the time the report was run.")
    total_value = fields.Float(string='Total Value', readonly=True, digits='Product Price', compute='_compute_total_value', store=True)

    # --- Automatic Fields ---
    # create_date (Implicit)
    # create_uid (Implicit)

    @api.depends('quantity', 'cost')
    def _compute_total_value(self):
        # This compute method remains the same
        for line in self:
            line.total_value = line.quantity * line.cost

    # Remove description and default_code if replaced by product_name/product_default_code
    # Remove uom if replaced by uom_name
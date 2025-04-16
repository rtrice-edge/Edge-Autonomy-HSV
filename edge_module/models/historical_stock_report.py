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

    def action_generate_report(self):
        self.ensure_one()

        ReportLine = self.env['historical.stock.report.line']
        StockLocation = self.env['stock.location']
        Product = self.env['product.product']
        StockProductionLot = self.env['stock.lot']
        Uom = self.env['uom.uom']
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')

        # -------------------------------
        # 1. Convert the snapshot datetime to UTC
        # -------------------------------
        user_tz = pytz.timezone(self.env.user.tz or 'UTC')
        local_dt = fields.Datetime.to_datetime(self.date_snapshot)
        local_dt_aware = user_tz.localize(local_dt, is_dst=None)
        snapshot_utc = local_dt_aware.astimezone(pytz.utc)
        _logger.info("Snapshot Date (User): %s, Converted to UTC: %s", self.date_snapshot, snapshot_utc)

        # -------------------------------
        # 2. Retrieve the location and its child internal locations
        # -------------------------------
        target_location = self.location_id
        child_locations = StockLocation.search([
            ('id', 'child_of', target_location.id),
            ('usage', '=', 'internal')
        ])
        child_location_ids = [loc.id for loc in child_locations]
        if not child_location_ids:
            raise UserError(_("Selected location '%s' has no usable internal child locations.") % target_location.display_name)
        _logger.info("Target Location: %s (ID: %s). Child internal locations: %s", target_location.display_name, target_location.id, child_location_ids)

        # -------------------------------
        # 3. Query stock_quant_history for records before or equal to the snapshot date
        #    For each distinct key (product, location, lot, package), select the latest history record.
        # -------------------------------
        query = """
            WITH LatestHistory AS (
                SELECT DISTINCT ON (h.product_id, h.location_id, h.lot_id, h.package_id)
                       h.product_id,
                       h.location_id,
                       h.lot_id,
                       h.package_id,
                       h.quantity,
                       h.change_date
                FROM stock_quant_history h
                WHERE h.change_date <= %s
                  AND h.location_id IN %s
                ORDER BY h.product_id, h.location_id, h.lot_id, h.package_id, h.change_date DESC, h.id DESC
            )
            SELECT * FROM LatestHistory;
        """
        # Note: For the IN clause we pass a tuple of location IDs.
        self.env.cr.execute(query, (snapshot_utc, tuple(child_location_ids)))
        history_records = self.env.cr.dictfetchall()

        if not history_records:
            raise UserError(_("No historical stock records found for the specified snapshot date and location."))

        # -------------------------------
        # 4. Pre-fetch related record details
        # -------------------------------
        product_ids = {rec['product_id'] for rec in history_records}
        lot_ids = {rec['lot_id'] for rec in history_records if rec['lot_id']}
        # Product and lot details
        product_info = {p.id: p for p in Product.browse(list(product_ids))}
        lot_info = {l.id: l for l in StockProductionLot.browse(list(lot_ids))}

        # -------------------------------
        # 5. Build report line values based on the queried historical state
        # -------------------------------
        report_lines_vals = []
        for rec in history_records:
            qty = rec['quantity']
            if (not self.include_zero_quantities) and float_is_zero(qty, precision_digits=precision):
                continue

            product_id = rec['product_id']
            product_rec = product_info.get(product_id)
            if not product_rec:
                product_name = "[Missing Product ID: %s]" % product_id
                product_code = ""
                cost = 0.0
            else:
                product_name = product_rec.display_name
                product_code = product_rec.default_code
                cost = product_rec.standard_price or 0.0

            lot_id = rec['lot_id']
            lot_name = "[No Lot]" if not lot_id else (lot_info.get(lot_id).name if lot_info.get(lot_id) else f"[Missing Lot ID: {lot_id}]")

            # Assume the product’s UoM is the one on the product record.
            uom_id = product_rec.uom_id.id if product_rec else False
            uom_name = product_rec.uom_id.name if product_rec else "[Missing UoM]"

            vals = {
                'report_date': self.date_snapshot,
                'report_location_id': target_location.id,
                'report_location_name': target_location.display_name,
                'product_id': product_id,
                'product_default_code': product_code,
                'product_name': product_name,
                'lot_id': lot_id,
                'lot_name': lot_name,
                'uom_id': uom_id,
                'uom_name': uom_name,
                'quantity': qty,
                'cost': cost,
            }
            report_lines_vals.append(vals)

        if not report_lines_vals:
            raise UserError(_("No non-zero stock records found for the specified snapshot."))
        _logger.info("Prepared %d report line values.", len(report_lines_vals))

        # -------------------------------
        # 6. Create the report lines and open the report view
        # -------------------------------
        try:
            _logger.info("Creating historical.stock.report.line records...")
            created_lines = ReportLine.create(report_lines_vals)
            _logger.info("Successfully created %d report line records.", len(created_lines))
        except Exception as e:
            _logger.error("Failed to create historical report lines: %s", e, exc_info=True)
            raise UserError(_("Failed to create report lines. Check server logs for details. Error: %s") % e)

        action = {
            'name': _('Historical Stock Report'),
            'type': 'ir.actions.act_window',
            'res_model': 'historical.stock.report.line',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', created_lines.ids)],
            'target': 'current',
            'context': {'create': False},
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
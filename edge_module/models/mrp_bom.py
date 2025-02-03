import logging
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)

class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    is_rma_bom = fields.Boolean(
        string="RMA BOM",
        help="If checked, the BOM Product is automatically added as a BOM line."
    )

    @api.model
    def create(self, vals):
        bom = super(MrpBom, self).create(vals)
        _logger.info("Created BOM (id: %s) with is_rma_bom=%s", bom.id, bom.is_rma_bom)
        if bom.is_rma_bom and bom.product_id:
            _logger.info("BOM (id: %s): RMA BOM enabled; adding BOM product (%s) as auto line.",
                         bom.id, bom.product_id.display_name)
            bom._update_bom_product_line(add=True)
        return bom

    def write(self, vals):
        res = super(MrpBom, self).write(vals)
        for bom in self:
            _logger.info("BOM (id: %s) write() called with vals: %s", bom.id, vals)
            # If any of these fields are updated, adjust the auto BOM line
            if any(field in vals for field in ['is_rma_bom', 'product_id', 'product_qty', 'product_uom_id']):
                if bom.is_rma_bom and bom.product_id:
                    _logger.info("BOM (id: %s): RMA BOM enabled; ensuring BOM product auto line exists.", bom.id)
                    bom._update_bom_product_line(add=True)
                else:
                    _logger.info("BOM (id: %s): RMA BOM disabled; removing BOM product auto line.", bom.id)
                    bom._update_bom_product_line(add=False)
        return res

    def _update_bom_product_line(self, add=True):
        """
        Helper method to add or remove the auto-generated BOM line for the BOM product.
        When add=True, if an auto line for the BOM product does not exist, it is created.
        When add=False, the auto line (if any) is removed.
        """
        auto_line = self.bom_line_ids.filtered(lambda l: l.auto_rma and l.product_id == self.product_id)
        if add:
            if auto_line:
                _logger.info("BOM (id: %s): Auto BOM line exists; updating quantity and UoM.", self.id)
                auto_line.write({
                    'product_qty': self.product_qty,
                    'product_uom_id': self.product_uom_id.id,
                })
            else:
                _logger.info("BOM (id: %s): Creating auto BOM line for BOM product (id: %s).",
                             self.id, self.product_id.id)
                self.env['mrp.bom.line'].create({
                    'bom_id': self.id,
                    'product_id': self.product_id.id,
                    'product_qty': self.product_qty,
                    'product_uom_id': self.product_uom_id.id,
                    'auto_rma': True,
                    'name': _('RMA Work - BOM Product'),
                })
        else:
            if auto_line:
                _logger.info("BOM (id: %s): Removing auto BOM line.", self.id)
                auto_line.unlink()
            else:
                _logger.info("BOM (id: %s): No auto BOM line found to remove.", self.id)


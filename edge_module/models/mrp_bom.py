import logging
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)

class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    is_rma_bom = fields.Boolean(
        string="RMA BOM",
        help="If checked, the BOM Product is automatically added as a BOM line."
    )

    def _get_produced_product(self):
        """Return the produced product:
           - Use product_id if set,
           - Otherwise, if product_tmpl_id is set, return its product variant.
        """
        self.ensure_one()
        produced_product = self.product_id or (self.product_tmpl_id and self.product_tmpl_id.product_variant_id)
        return produced_product

    @api.model
    def create(self, vals):
        _logger.info("Creating BOM with vals: %s", vals)
        bom = super(MrpBom, self).create(vals)
        produced_product = bom._get_produced_product()
        _logger.info("Created BOM (id: %s) with is_rma_bom=%s, produced_product=%s", 
                     bom.id, bom.is_rma_bom, produced_product.id if produced_product else 'None')
        if bom.is_rma_bom and produced_product:
            _logger.info("BOM (id: %s): RMA BOM enabled; adding produced product (%s) as auto line.",
                         bom.id, produced_product.display_name)
            bom._update_bom_product_line(add=True)
        return bom

    def write(self, vals):
        res = super(MrpBom, self).write(vals)
        for bom in self:
            produced_product = bom._get_produced_product()
            _logger.info("After write, BOM (id: %s): is_rma_bom=%s, produced_product=%s", 
                         bom.id, bom.is_rma_bom, produced_product.id if produced_product else 'None')
            # If any of these fields are updated, adjust the auto BOM line
            if any(field in vals for field in ['is_rma_bom', 'product_id', 'product_tmpl_id', 'product_qty', 'product_uom_id']):
                if bom.is_rma_bom and produced_product:
                    _logger.info("BOM (id: %s): RMA BOM enabled; ensuring produced product auto line exists.", bom.id)
                    bom._update_bom_product_line(add=True)
                else:
                    _logger.info("BOM (id: %s): RMA BOM disabled; removing produced product auto line.", bom.id)
                    bom._update_bom_product_line(add=False)
        return res

    def _update_bom_product_line(self, add=True):
        """
        Helper method to add or remove the auto-generated BOM line for the produced product.
        When add=True, if an auto line for the produced product does not exist, it is created.
        When add=False, the auto line (if any) is removed.
        """
        produced_product = self._get_produced_product()
        auto_line = self.bom_line_ids.filtered(lambda l: l.auto_rma and l.product_id == produced_product)
        if add:
            if auto_line:
                _logger.info("BOM (id: %s): Auto BOM line exists; updating quantity (%s) and UoM (%s).",
                             self.id, self.product_qty, self.product_uom_id.id)
                auto_line.write({
                    'product_qty': self.product_qty,
                    'product_uom_id': self.product_uom_id.id,
                })
            else:
                _logger.info("BOM (id: %s): Creating auto BOM line for produced product (id: %s).",
                             self.id, produced_product.id)
                self.env['mrp.bom.line'].create({
                    'bom_id': self.id,
                    'product_id': produced_product.id,
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


import logging
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)

class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    is_rma_bom = fields.Boolean(
        string="RMA BOM",
        help="If checked, the produced product will be automatically added as a component in this BOM."
    )

    @api.onchange('is_rma_bom')
    def _onchange_is_rma_bom(self):
        _logger.info("Onchange triggered for BOM (id: %s): is_rma_bom set to %s", self.id, self.is_rma_bom)

    @api.model
    def create(self, vals):
        _logger.info("Creating BOM with vals: %s", vals)
        bom = super(MrpBom, self).create(vals)
        _logger.info("Created BOM (id: %s) with is_rma_bom=%s", bom.id, bom.is_rma_bom)
        if bom.is_rma_bom and bom.product_id:
            _logger.info("BOM (id: %s) is marked as RMA BOM and has a product (%s). Adding auto RMA BOM line.", bom.id, bom.product_id.display_name)
            bom._update_rma_bom_line(add=True)
        return bom

    def write(self, vals):
        _logger.info("Write called on BOM (id(s): %s) with vals: %s", self.ids, vals)
        res = super(MrpBom, self).write(vals)
        for bom in self:
            # If key fields change, update auto RMA BOM line accordingly.
            if ('is_rma_bom' in vals) or any(key in vals for key in ['product_id', 'product_qty', 'product_uom_id']):
                _logger.info("Updating BOM (id: %s) after write with vals: %s", bom.id, vals)
                if bom.is_rma_bom and bom.product_id:
                    # Remove any auto-lines that refer to a different product.
                    auto_wrong = bom.bom_line_ids.filtered(lambda l: l.auto_rma and l.product_id != bom.product_id)
                    if auto_wrong:
                        _logger.info("BOM (id: %s) has %s auto RMA BOM line(s) for an outdated product. Removing them.", bom.id, len(auto_wrong))
                        auto_wrong.unlink()
                    # Update or create the auto RMA BOM line.
                    auto_lines = bom.bom_line_ids.filtered(lambda l: l.auto_rma and l.product_id == bom.product_id)
                    if auto_lines:
                        _logger.info("Updating existing auto RMA BOM line(s) for BOM (id: %s).", bom.id)
                        auto_lines.write({
                            'product_qty': bom.product_qty,
                            'product_uom_id': bom.product_uom_id.id,
                        })
                    else:
                        _logger.info("No auto RMA BOM line found for BOM (id: %s). Creating one.", bom.id)
                        bom._update_rma_bom_line(add=True)
                else:
                    _logger.info("BOM (id: %s) is not marked as RMA BOM or does not have a product. Removing any auto RMA BOM lines if they exist.", bom.id)
                    bom._update_rma_bom_line(add=False)
        return res

    def _update_rma_bom_line(self, add=True):
        """Helper method to add or remove the auto-created BOM line for the produced product."""
        auto_lines = self.bom_line_ids.filtered(lambda l: l.auto_rma and l.product_id == self.product_id)
        if add:
            if not auto_lines and self.product_uom_id and self.product_id:
                _logger.info("Creating auto RMA BOM line for BOM (id: %s).", self.id)
                self.env['mrp.bom.line'].create({
                    'bom_id': self.id,
                    'product_id': self.product_id.id,
                    'product_qty': self.product_qty,
                    'product_uom_id': self.product_uom_id.id,
                    'auto_rma': True,
                    'name': _('RMA Work - Self Consumption'),
                })
            else:
                _logger.info("Auto RMA BOM line already exists for BOM (id: %s), skipping creation.", self.id)
        else:
            if auto_lines:
                _logger.info("Removing %s auto RMA BOM line(s) from BOM (id: %s).", len(auto_lines), self.id)
                auto_lines.unlink()
            else:
                _logger.info("No auto RMA BOM lines to remove for BOM (id: %s).", self.id)




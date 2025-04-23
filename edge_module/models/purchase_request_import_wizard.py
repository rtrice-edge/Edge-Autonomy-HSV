# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
import base64
import io
import logging
import xlrd

_logger = logging.getLogger(__name__)

class PurchaseRequestImportWizard(models.TransientModel):
    _name = 'purchase.request.import.wizard'
    _description = 'Import Purchase Request from Excel Template'

    excel_file = fields.Binary(string='Excel File', required=True)
    file_name = fields.Char(string='File Name')

    def action_import(self):
        """Import data from the uploaded Excel file."""
        self.ensure_one()
        if not self.excel_file:
            raise UserError(_("Please upload an Excel file."))

        # Decode the file
        try:
            excel_file_data = base64.b64decode(self.excel_file)
            book = xlrd.open_workbook(file_contents=excel_file_data)
            sheet = book.sheet_by_index(0)
        except Exception as e:
            raise UserError(_("Could not read the Excel file: %s") % str(e))

        # Initialize data dictionary
        data = {
            'partner_id': False,
            'deliver_to_address': 'edge_slo',
            'production_stoppage': False,
            'resale_designation': 'no_resale',
            'request_line_ids': [],
        }
        
        # Extract header data
        # Find and extract supplier info (row 12, column B)
        try:
            supplier_cell = None
            for row_idx in range(sheet.nrows):
                cell_value = sheet.cell_value(row_idx, 0)
                if isinstance(cell_value, str) and "suggested supplier" in cell_value.lower():
                    supplier_cell = sheet.cell_value(row_idx, 1).strip()
                    break
                    
            if supplier_cell and supplier_cell not in ['Suggested Supplier', '']:
                supplier = self.env['res.partner'].search([
                    ('name', 'ilike', supplier_cell),
                    ('supplier_rank', '>', 0)
                ], limit=1)
                if supplier:
                    data['partner_id'] = supplier.id
        except Exception as e:
            _logger.warning("Error extracting supplier: %s", str(e))

        # Production Stoppage
        try:
            stoppage_cell = None
            for row_idx in range(sheet.nrows):
                cell_value = sheet.cell_value(row_idx, 0)
                if isinstance(cell_value, str) and "production stoppage" in cell_value.lower():
                    stoppage_cell = sheet.cell_value(row_idx, 1).strip().lower()
                    break
                    
            if stoppage_cell in ['yes', 'true', '1', 'select one']:
                data['production_stoppage'] = True
        except Exception as e:
            _logger.warning("Error extracting production stoppage: %s", str(e))

        # Need by date
        try:
            date_cell = None
            for row_idx in range(sheet.nrows):
                cell_value = sheet.cell_value(row_idx, 0)
                if isinstance(cell_value, str) and "need date" in cell_value.lower():
                    date_cell = sheet.cell_value(row_idx, 1)
                    break
                    
            if date_cell:
                if isinstance(date_cell, float):
                    # Excel date as float
                    from datetime import datetime
                    date_tuple = xlrd.xldate_as_tuple(date_cell, 0)  # 0 = 1900-based
                    date_obj = datetime(*date_tuple)
                    data['need_by_date'] = date_obj.strftime('%Y-%m-%d')
                elif isinstance(date_cell, str) and date_cell.strip():
                    try:
                        # Try to convert to odoo date format if it's a string
                        from datetime import datetime
                        for fmt in ['%m/%d/%Y', '%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y']:
                            try:
                                date_obj = datetime.strptime(date_cell, fmt)
                                data['need_by_date'] = date_obj.strftime('%Y-%m-%d')
                                break
                            except ValueError:
                                continue
                    except Exception:
                        # If conversion fails, use current date + 30 days
                        from datetime import datetime, timedelta
                        data['need_by_date'] = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        except Exception as e:
            _logger.warning("Error extracting need by date: %s", str(e))

        # Delivery Location
        try:
            delivery_cell = None
            for row_idx in range(sheet.nrows):
                cell_value = sheet.cell_value(row_idx, 0)
                if isinstance(cell_value, str) and "delivery location" in cell_value.lower():
                    delivery_cell = sheet.cell_value(row_idx, 1).strip().lower()
                    break
                    
            if delivery_cell and "other" in delivery_cell:
                data['deliver_to_address'] = 'other'
        except Exception as e:
            _logger.warning("Error extracting delivery location: %s", str(e))

        # Delivery Address
        try:
            address_cell = None
            for row_idx in range(sheet.nrows):
                cell_value = sheet.cell_value(row_idx, 0)
                if isinstance(cell_value, str) and "delivery address" in cell_value.lower():
                    address_cell = sheet.cell_value(row_idx, 1).strip()
                    break
                    
            if address_cell and data['deliver_to_address'] == 'other':
                data['deliver_to_other_address'] = address_cell
        except Exception as e:
            _logger.warning("Error extracting delivery address: %s", str(e))

        # Delivery Point of Contact
        try:
            poc_cell = None
            for row_idx in range(sheet.nrows):
                cell_value = sheet.cell_value(row_idx, 0)
                if isinstance(cell_value, str) and "delivery point of contact" in cell_value.lower():
                    poc_cell = sheet.cell_value(row_idx, 1).strip()
                    break
                    
            if poc_cell and data['deliver_to_address'] == 'other':
                data['deliver_to_other'] = poc_cell
        except Exception as e:
            _logger.warning("Error extracting delivery contact: %s", str(e))

        # Delivery POC Phone Number
        try:
            phone_cell = None
            for row_idx in range(sheet.nrows):
                cell_value = sheet.cell_value(row_idx, 0)
                if isinstance(cell_value, str) and "poc phone" in cell_value.lower():
                    phone_cell = sheet.cell_value(row_idx, 1).strip()
                    break
                    
            if phone_cell and data['deliver_to_address'] == 'other':
                data['deliver_to_other_phone'] = phone_cell
        except Exception as e:
            _logger.warning("Error extracting delivery phone: %s", str(e))

        # Resale/No Resale
        try:
            resale_cell = None
            for row_idx in range(sheet.nrows):
                cell_value = sheet.cell_value(row_idx, 0)
                if isinstance(cell_value, str) and "resale" in cell_value.lower():
                    resale_cell = sheet.cell_value(row_idx, 1).strip().lower()
                    break
                    
            if resale_cell == 'resale':
                data['resale_designation'] = 'resale'
        except Exception as e:
            _logger.warning("Error extracting resale designation: %s", str(e))

        # Notes/Links
        try:
            notes_cell = None
            for row_idx in range(sheet.nrows):
                cell_value = sheet.cell_value(row_idx, 0)
                if isinstance(cell_value, str) and "notes" in cell_value.lower():
                    notes_cell = sheet.cell_value(row_idx, 1).strip()
                    break
                    
            if notes_cell and notes_cell != 'Notes/Links':
                data['requester_notes'] = notes_cell
        except Exception as e:
            _logger.warning("Error extracting notes: %s", str(e))

        # Find the row containing 'Purchase Type'
        header_row_idx = None
        for row_idx in range(sheet.nrows):
            if row_idx < sheet.nrows:
                cell_value = sheet.cell_value(row_idx, 0)
                if isinstance(cell_value, str) and "purchase type" in cell_value.lower():
                    header_row_idx = row_idx
                    _logger.info(f"Found header row at index {header_row_idx}")
                    break

        if header_row_idx is None:
            raise UserError(_("Could not find the 'Purchase Type' header in the Excel file."))

        # Find the column indices for each required field based on the header row
        columns = {}
        for col_idx in range(sheet.ncols):
            if col_idx < sheet.ncols:
                header_value = sheet.cell_value(header_row_idx, col_idx)
                if isinstance(header_value, str):
                    header_value = header_value.lower().strip()
                    if "purchase type" in header_value:
                        columns['purchase_type'] = col_idx
                    elif "part number" in header_value:
                        columns['part_number'] = col_idx
                    elif "description" in header_value:
                        columns['description'] = col_idx
                    elif "uom" in header_value:
                        columns['uom'] = col_idx
                    elif "qty" in header_value:
                        columns['qty'] = col_idx
                    elif "price" in header_value:
                        columns['price'] = col_idx
                    elif "job" in header_value and not "number" in header_value:
                        columns['job'] = col_idx
                    elif "expense type" in header_value:
                        columns['expense_type'] = col_idx
                    elif "pop start" in header_value:
                        columns['pop_start'] = col_idx
                    elif "pop end" in header_value:
                        columns['pop_end'] = col_idx
                    elif "mfr" in header_value and not "pn" in header_value:
                        columns['mfr'] = col_idx
                    elif "mfr pn" in header_value:
                        columns['mfr_pn'] = col_idx
                    elif "cage" in header_value:
                        columns['cage'] = col_idx

        _logger.info(f"Columns mapping: {columns}")

        # Extract line items - start from row after header
        for row_idx in range(header_row_idx + 1, sheet.nrows):
            try:
                # Check if we have data in this row by looking at the purchase type and description
                purchase_type_col = columns.get('purchase_type', 0)
                description_col = columns.get('description', 2)
                
                purchase_type_value = sheet.cell_value(row_idx, purchase_type_col) if purchase_type_col < sheet.ncols else ""
                description_value = sheet.cell_value(row_idx, description_col) if description_col < sheet.ncols else ""
                
                # Skip if both purchase type and description are empty
                if (not purchase_type_value or purchase_type_value.strip() == '') and \
                   (not description_value or description_value.strip() == ''):
                    continue

                _logger.info(f"Processing row {row_idx}: {purchase_type_value} - {description_value}")
                
                # Create line data from the mapped columns
                line_data = {
                    'purchase_type': self._determine_purchase_type(
                        sheet.cell_value(row_idx, columns.get('purchase_type', 0)).strip() if columns.get('purchase_type', 0) < sheet.ncols else "direct_materials"
                    ),
                    'name': sheet.cell_value(row_idx, columns.get('description', 2)).strip() if columns.get('description', 2) < sheet.ncols else "",
                }
                
                # Add remaining fields if columns were found
                if 'uom' in columns and columns['uom'] < sheet.ncols:
                    line_data['product_uom_id'] = self._get_uom_id(sheet.cell_value(row_idx, columns['uom']).strip())
                
                if 'qty' in columns and columns['qty'] < sheet.ncols:
                    qty_value = sheet.cell_value(row_idx, columns['qty'])
                    line_data['quantity'] = float(qty_value) if qty_value else 1.0
                else:
                    line_data['quantity'] = 1.0
                
                if 'price' in columns and columns['price'] < sheet.ncols:
                    price_value = sheet.cell_value(row_idx, columns['price'])
                    line_data['price_unit'] = float(price_value) if price_value else 0.0
                else:
                    line_data['price_unit'] = 0.0
                
                if 'job' in columns and columns['job'] < sheet.ncols:
                    line_data['job'] = self._get_job_id(sheet.cell_value(row_idx, columns['job']).strip())
                
                if 'expense_type' in columns and columns['expense_type'] < sheet.ncols:
                    line_data['expense_type'] = self._get_expense_type(sheet.cell_value(row_idx, columns['expense_type']).strip())
                else:
                    line_data['expense_type'] = 'raw_materials'  # Default
                
                if 'pop_start' in columns and columns['pop_start'] < sheet.ncols:
                    line_data['pop_start'] = self._convert_date(sheet.cell_value(row_idx, columns['pop_start']))
                
                if 'pop_end' in columns and columns['pop_end'] < sheet.ncols:
                    line_data['pop_end'] = self._convert_date(sheet.cell_value(row_idx, columns['pop_end']))
                
                if 'mfr' in columns and columns['mfr'] < sheet.ncols:
                    line_data['manufacturer'] = sheet.cell_value(row_idx, columns['mfr']).strip()
                
                if 'mfr_pn' in columns and columns['mfr_pn'] < sheet.ncols:
                    line_data['manufacturer_number'] = sheet.cell_value(row_idx, columns['mfr_pn']).strip()
                
                if 'cage' in columns and columns['cage'] < sheet.ncols:
                    line_data['cage_code'] = sheet.cell_value(row_idx, columns['cage']).strip()
                
                # Find product by internal reference or create a placeholder
                product_internal_ref = ""
                if 'part_number' in columns and columns['part_number'] < sheet.ncols:
                    product_internal_ref = sheet.cell_value(row_idx, columns['part_number']).strip()
                
                _logger.info(f"Looking for product with internal reference: {product_internal_ref}")
                
                product = False
                if product_internal_ref:
                    product = self.env['product.product'].search([
                        ('default_code', '=', product_internal_ref)
                    ], limit=1)
                
                if not product:
                    # First try to find by manufacturer number if available
                    if line_data.get('manufacturer_number'):
                        product = self.env['product.product'].search([
                            ('manufacturernumber', '=', line_data['manufacturer_number']),
                            ('purchase_ok', '=', True)
                        ], limit=1)
                    
                    # Next try to find by name/description
                    if not product and line_data['name']:
                        product = self.env['product.product'].search([
                            ('name', 'ilike', line_data['name']),
                            ('purchase_ok', '=', True)
                        ], limit=1)
                    
                    # If still not found, use appropriate product based on purchase type
                    if not product:
                        if line_data['purchase_type'] == 'direct_materials':
                            # Try to find a consumable product
                            product = self.env['product.product'].search([
                                ('type', '=', 'consu'),
                                ('purchase_ok', '=', True)
                            ], limit=1)
                            if not product:
                                # If not found, use the generic product
                                product = self.env.ref('product.product_product_consumable', raise_if_not_found=False)
                        elif line_data['purchase_type'] == 'indirect_materials':
                            product = self.env['product.product'].search([
                                ('default_code', '=', 'IndirectMisc')
                            ], limit=1)
                            if not product:
                                # If the specific product isn't found, use a generic one
                                product = self.env['product.product'].search([
                                    ('type', '=', 'consu'),
                                    ('purchase_ok', '=', True)
                                ], limit=1)
                        elif line_data['purchase_type'] == 'direct_services':
                            product = self.env['product.product'].search([
                                ('default_code', '=', 'DirectService')
                            ], limit=1)
                            if not product:
                                # If not found, use a generic service product
                                product = self.env['product.product'].search([
                                    ('type', '=', 'service'),
                                    ('purchase_ok', '=', True)
                                ], limit=1)
                        elif line_data['purchase_type'] == 'indirect_services':
                            product = self.env['product.product'].search([
                                ('default_code', '=', 'IndirectService')
                            ], limit=1)
                            if not product:
                                # If not found, use a generic service product
                                product = self.env['product.product'].search([
                                    ('type', '=', 'service'),
                                    ('purchase_ok', '=', True)
                                ], limit=1)
                
                if product:
                    line_data['product_id'] = product.id
                    # If we didn't get a UOM from the file, use the product's UOM
                    if not line_data.get('product_uom_id'):
                        line_data['product_uom_id'] = product.uom_po_id.id or product.uom_id.id
                else:
                    # If we can't find a product, we'll create a temporary one
                    vals = {
                        'name': line_data['name'] or 'Imported Product',
                        'type': 'consu' if line_data['purchase_type'] in ['direct_materials', 'indirect_materials'] else 'service',
                        'default_code': product_internal_ref if product_internal_ref else 'IMP-' + str(row_idx),
                        'purchase_ok': True,
                    }
                    if line_data.get('manufacturer'):
                        vals['manufacturer'] = line_data['manufacturer']
                    if line_data.get('manufacturer_number'):
                        vals['manufacturernumber'] = line_data['manufacturer_number']
                    
                    try:
                        product = self.env['product.product'].create(vals)
                        line_data['product_id'] = product.id
                        # Use the product's UOM
                        if not line_data.get('product_uom_id'):
                            line_data['product_uom_id'] = product.uom_po_id.id or product.uom_id.id
                    except Exception as e:
                        _logger.error(f"Error creating product: {e}")
                        # If product creation fails, skip this line
                        continue
                
                # Add line to the list if it has a name (bare minimum)
                if line_data.get('name'):
                    _logger.info(f"Adding line: {line_data}")
                    data['request_line_ids'].append((0, 0, line_data))
                
            except Exception as e:
                _logger.warning(f"Error processing line {row_idx}: {str(e)}", exc_info=True)

        # Create the purchase request
        if data['request_line_ids']:
            # Set the originator to current user if not found
            data['originator'] = self.env['hr.employee'].search([
                ('user_id', '=', self.env.user.id)
            ], limit=1).id or False

            # If no need_by_date was found, set to today + 30 days
            if 'need_by_date' not in data or not data['need_by_date']:
                from datetime import datetime, timedelta
                data['need_by_date'] = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')

            _logger.info(f"Creating purchase request with data: {data}")
            
            # Create the purchase request
            purchase_request = self.env['purchase.request'].create(data)
            
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'purchase.request',
                'view_mode': 'form',
                'res_id': purchase_request.id,
                'target': 'current',
            }
        else:
            raise UserError(_("No valid line items found in the Excel file. Please check your file format."))

    def _determine_purchase_type(self, value):
        """Determine the purchase type based on the Excel value."""
        if not isinstance(value, str):
            return "direct_materials"  # Default
            
        value = value.lower()
        
        if 'direct' in value and ('material' in value or 'mat' in value):
            return 'direct_materials'
        elif 'direct' in value and ('service' in value or 'serv' in value):
            return 'direct_services'
        elif 'indirect' in value and ('material' in value or 'mat' in value):
            return 'indirect_materials'
        elif 'indirect' in value and ('service' in value or 'serv' in value):
            return 'indirect_services'
        
        # Default
        return 'direct_materials'

    def _get_uom_id(self, uom_name):
        """Find the UOM ID based on the name from Excel."""
        if not uom_name:
            return False
            
        # Try to find the UOM
        uom = self.env['uom.uom'].search([
            '|', '|', '|',
            ('name', '=ilike', uom_name),
            ('name', '=ilike', uom_name.replace(' ', '')),
            ('name', '=ilike', uom_name + 's'),  # Try plural
            ('name', '=ilike', uom_name[:-1] if uom_name.endswith('s') else uom_name),  # Try singular
        ], limit=1)
        
        if uom:
            return uom.id
        
        # Return the default UOM (EA) if not found
        default_uom = self.env.ref('uom.product_uom_unit', raise_if_not_found=False)
        if not default_uom:
            # Find a unit UOM if the reference fails
            default_uom = self.env['uom.uom'].search([('name', 'in', ['Units', 'Unit', 'unit', 'ea', 'EA', 'Each'])], limit=1)
        
        return default_uom.id if default_uom else False
    
    def _get_job_id(self, job_name):
        """Find the job ID based on the name or number from Excel."""
        if not job_name or job_name in ['', 'N/A', 'n/a', 'NA', 'na']:
            # Try to find a default job
            default_job = self.env['job'].search([('active', '=', True)], limit=1)
            return default_job.id if default_job else False
            
        # Try to find the job by name or number
        job = self.env['job'].search([
            '|', ('name', '=ilike', job_name),
            ('number', '=ilike', job_name),
        ], limit=1)
        
        if job:
            return job.id
        
        # If not found, try a broader search
        job = self.env['job'].search([
            '|', ('name', 'ilike', job_name),
            ('number', 'ilike', job_name),
        ], limit=1)
        
        if job:
            return job.id
            
        # If still not found, get the first active job
        default_job = self.env['job'].search([('active', '=', True)], limit=1)
        return default_job.id if default_job else False
    
    def _get_expense_type(self, expense_type_name):
        """Map the expense type name to Odoo's expense type options."""
        if not expense_type_name or expense_type_name in ['', 'N/A', 'n/a', 'NA', 'na']:
            return 'raw_materials'  # Default
            
        # Mapping of common expense type names to Odoo's codes
        mappings = {
            'inventory': 'raw_materials',
            'raw material': 'raw_materials',
            'consumable': 'consumables',
            'tooling': 'small_tooling',
            'manufacturing': 'manufacturing_supplies',
            'engineering': 'engineering_supplies',
            'office': 'office_supplies',
            'building': 'building_supplies',
            'janitorial': 'janitorial',
            'communication': 'communications',
            'utility': 'utilities',
            'flight': 'flight_ops',
            'it hardware': 'it_hardware',
            'hardware': 'it_hardware',
            'it software': 'it_software',
            'software': 'it_software',
            'it service': 'it_services',
            'repair': 'repairs',
            'business': 'business_dev',
            'training': 'training',
            'license': 'licenses',
            'vehicle': 'vehicle',
            'rental': 'equipment_rental',
            'employee': 'employee_morale',
            'morale': 'employee_morale',
            'safety': 'safety',
            'marketing': 'marketing',
            'recruiting': 'recruiting',
            'shipping': 'shipping',
            'packaging': 'shipping',
            'direct award': 'direct_award',
            'capital': 'capex',
            'capex': 'capex',
            'subcontractor': 'subcontractors',
            'consultant': 'subcontractors',
            'professional': 'subcontractors',
        }
        
        # Try to match the expense type
        expense_type_lower = expense_type_name.lower()
        for key, value in mappings.items():
            if key in expense_type_lower:
                return value
        
        return 'raw_materials'  # Default if no match found
    
    def _convert_date(self, date_value):
        """Convert Excel date value to Odoo date format."""
        if not date_value:
            return False
            
        try:
            if isinstance(date_value, float):
                # Excel date as float
                from datetime import datetime, timedelta
                date_tuple = xlrd.xldate_as_tuple(date_value, 0)  # 0 = 1900-based
                date_obj = datetime(*date_tuple)
                return date_obj.strftime('%Y-%m-%d')
            elif isinstance(date_value, str):
                # Try common formats
                from datetime import datetime
                for fmt in ['%m/%d/%Y', '%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y']:
                    try:
                        date_obj = datetime.strptime(date_value, fmt)
                        return date_obj.strftime('%Y-%m-%d')
                    except ValueError:
                        continue
        except Exception as e:
            _logger.warning("Error converting date %s: %s", date_value, str(e))
        
        return False
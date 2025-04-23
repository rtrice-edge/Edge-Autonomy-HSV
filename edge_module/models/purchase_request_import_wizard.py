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
    # Use a Character field for sheet_name instead of Selection
    sheet_name = fields.Char(string='Sheet Name', help="Enter the name of the sheet to import (e.g., 'PR Request')")
    debug_mode = fields.Boolean(string='Debug Mode', default=False, 
                               help="Enable debug mode to see detailed logging")
    available_sheets = fields.Char(string='Available Sheets', readonly=True)
    
    @api.onchange('excel_file')
    def _onchange_excel_file(self):
        """Update available sheet names when file is uploaded."""
        if self.excel_file:
            try:
                excel_file_data = base64.b64decode(self.excel_file)
                book = xlrd.open_workbook(file_contents=excel_file_data)
                sheet_names_list = book.sheet_names()
                
                # Show available sheets to the user
                self.available_sheets = ', '.join(sheet_names_list)
                
                # Default to 'PR Request' if available
                pr_sheet = None
                for name in sheet_names_list:
                    if 'pr request' in name.lower():
                        pr_sheet = name
                        break
                
                if pr_sheet:
                    self.sheet_name = pr_sheet
                elif sheet_names_list:
                    self.sheet_name = sheet_names_list[0]
                
                # Debug logging
                if self.debug_mode:
                    _logger.info(f"Found sheets: {sheet_names_list}")
                    _logger.info(f"Selected sheet: {self.sheet_name}")
                
            except Exception as e:
                self.available_sheets = f"Error reading sheets: {str(e)}"
                _logger.error(f"Error in _onchange_excel_file: {str(e)}")

    def action_import(self):
        """Import data from the uploaded Excel file."""
        self.ensure_one()
        if not self.excel_file:
            raise UserError(_("Please upload an Excel file."))
            
        if not self.sheet_name:
            raise UserError(_("Please enter a sheet name to import."))

        # Decode the file
        try:
            excel_file_data = base64.b64decode(self.excel_file)
            book = xlrd.open_workbook(file_contents=excel_file_data)
            
            # Try to get the sheet by name
            try:
                sheet = book.sheet_by_name(self.sheet_name)
            except xlrd.biffh.XLRDError:
                # If exact match fails, try case-insensitive match
                sheet = None
                for idx, name in enumerate(book.sheet_names()):
                    if name.lower() == self.sheet_name.lower():
                        sheet = book.sheet_by_index(idx)
                        break
                
                if not sheet:
                    # If still no match, show available sheets and raise error
                    available_sheets = ', '.join(book.sheet_names())
                    raise UserError(_(
                        "Sheet '%(sheet_name)s' not found in the Excel file. Available sheets are: %(available_sheets)s",
                        sheet_name=self.sheet_name,
                        available_sheets=available_sheets
                    ))
            
            if self.debug_mode:
                _logger.info(f"Processing sheet: {sheet.name}")
                # Print sample rows
                for row_idx in range(min(10, sheet.nrows)):
                    row_data = []
                    for col_idx in range(min(10, sheet.ncols)):
                        row_data.append(sheet.cell_value(row_idx, col_idx))
                    _logger.info(f"Row {row_idx}: {row_data}")
                    
        except Exception as e:
            raise UserError(_("Could not read the Excel file: %s") % str(e))

        # Initialize data dictionary
        data = {
            'partner_id': False,
            'deliver_to_address': 'edge_slo',
            'production_stoppage': False,
            'resale_designation': 'no_resale',
            'request_line_ids': [],
            'originator': self.env['hr.employee'].search([
                ('user_id', '=', self.env.user.id)
            ], limit=1).id or False,
        }
        
        # Set default need_by_date if not found
        from datetime import datetime, timedelta
        data['need_by_date'] = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        
        # Extract header data by looking for key strings
        self._extract_header_data(sheet, data)

        # Find all potential header rows - look for any row that contains "purchase type", "description", etc.
        header_row_candidates = []
        for row_idx in range(sheet.nrows):
            row_text = ' '.join([str(sheet.cell_value(row_idx, col_idx)).lower() 
                                for col_idx in range(min(10, sheet.ncols))])
            if 'purchase type' in row_text or 'description' in row_text or 'part number' in row_text:
                header_row_candidates.append(row_idx)
                if self.debug_mode:
                    _logger.info(f"Found potential header row at index {row_idx}: {row_text}")

        # Try each header row candidate
        for header_row_idx in header_row_candidates:
            # Map columns based on this header row
            columns = self._map_columns(sheet, header_row_idx)
            
            if self.debug_mode:
                _logger.info(f"Column mapping for row {header_row_idx}: {columns}")
            
            # If this header row has essential columns, process data rows
            if 'description' in columns or 'purchase_type' in columns:
                line_items = self._extract_line_items(sheet, header_row_idx, columns)
                if line_items:
                    data['request_line_ids'].extend(line_items)
                    if self.debug_mode:
                        _logger.info(f"Found {len(line_items)} line items from header row {header_row_idx}")
        
        # If no line items were found, try a more aggressive approach
        if not data['request_line_ids']:
            if self.debug_mode:
                _logger.info("No line items found with header-based approach, trying direct row scanning")
            
            # Directly scan rows looking for potential product data
            for row_idx in range(sheet.nrows):
                if row_idx < 10:  # Skip likely header area
                    continue
                    
                # Look for rows that might contain product data
                has_part_number = False
                has_description = False
                
                for col_idx in range(min(5, sheet.ncols)):
                    cell_value = str(sheet.cell_value(row_idx, col_idx))
                    # Check if cell looks like a part number (alphanumeric with hyphens)
                    if any(char.isdigit() for char in cell_value) and len(cell_value) > 3:
                        has_part_number = True
                    # Check if cell looks like a description (longer text)
                    if len(cell_value) > 10:
                        has_description = True
                
                if has_part_number or has_description:
                    line_data = self._extract_line_from_row(sheet, row_idx)
                    if line_data:
                        data['request_line_ids'].append((0, 0, line_data))
                        if self.debug_mode:
                            _logger.info(f"Extracted line from row {row_idx}: {line_data}")

        # Create the purchase request
        if data['request_line_ids']:
            if self.debug_mode:
                _logger.info(f"Creating purchase request with {len(data['request_line_ids'])} lines")
                
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
            raise UserError(_(
                "No valid line items found in the Excel file. Please check your file format.\n"
                "The import wizard looks for a row with headings like 'Purchase Type', 'Description', 'Part Number', etc."
            ))

    def _extract_header_data(self, sheet, data):
        """Extract header data like supplier, dates, etc."""
        # Try to find key header fields by searching for text patterns
        for row_idx in range(min(30, sheet.nrows)):
            for col_idx in range(min(5, sheet.ncols)):
                cell_value = str(sheet.cell_value(row_idx, col_idx)).lower()
                
                # Look for supplier information
                if 'supplier' in cell_value or 'vendor' in cell_value:
                    try:
                        supplier_value = sheet.cell_value(row_idx, col_idx + 1)
                        if supplier_value and supplier_value not in ['', 'Suggested Supplier']:
                            supplier = self.env['res.partner'].search([
                                ('name', 'ilike', supplier_value),
                                ('supplier_rank', '>', 0)
                            ], limit=1)
                            if supplier:
                                data['partner_id'] = supplier.id
                                if self.debug_mode:
                                    _logger.info(f"Found supplier: {supplier.name}")
                    except Exception as e:
                        if self.debug_mode:
                            _logger.warning(f"Error extracting supplier: {str(e)}")
                
                # Look for production stoppage
                if 'production stoppage' in cell_value:
                    try:
                        stoppage_value = str(sheet.cell_value(row_idx, col_idx + 1)).lower()
                        if stoppage_value in ['yes', 'true', '1', 'y']:
                            data['production_stoppage'] = True
                            if self.debug_mode:
                                _logger.info("Production stoppage set to True")
                    except Exception as e:
                        if self.debug_mode:
                            _logger.warning(f"Error extracting production stoppage: {str(e)}")
                
                # Look for need-by date
                if 'need' in cell_value and 'date' in cell_value:
                    try:
                        date_value = sheet.cell_value(row_idx, col_idx + 1)
                        date_str = self._convert_date(date_value)
                        if date_str:
                            data['need_by_date'] = date_str
                            if self.debug_mode:
                                _logger.info(f"Found need by date: {date_str}")
                    except Exception as e:
                        if self.debug_mode:
                            _logger.warning(f"Error extracting need by date: {str(e)}")
                
                # Look for delivery location
                if 'delivery location' in cell_value:
                    try:
                        delivery_value = str(sheet.cell_value(row_idx, col_idx + 1)).lower()
                        if 'other' in delivery_value:
                            data['deliver_to_address'] = 'other'
                            if self.debug_mode:
                                _logger.info("Delivery location set to 'other'")
                    except Exception as e:
                        if self.debug_mode:
                            _logger.warning(f"Error extracting delivery location: {str(e)}")
                
                # Look for notes
                if 'notes' in cell_value:
                    try:
                        notes_value = sheet.cell_value(row_idx, col_idx + 1)
                        if notes_value and notes_value != 'Notes/Links':
                            data['requester_notes'] = notes_value
                            if self.debug_mode:
                                _logger.info(f"Found notes: {notes_value[:50]}...")
                    except Exception as e:
                        if self.debug_mode:
                            _logger.warning(f"Error extracting notes: {str(e)}")
                            
                # Other delivery fields
                if data['deliver_to_address'] == 'other':
                    if 'delivery address' in cell_value:
                        data['deliver_to_other_address'] = sheet.cell_value(row_idx, col_idx + 1)
                    if 'point of contact' in cell_value:
                        data['deliver_to_other'] = sheet.cell_value(row_idx, col_idx + 1)
                    if 'phone' in cell_value:
                        data['deliver_to_other_phone'] = sheet.cell_value(row_idx, col_idx + 1)
                
                # Look for resale designation
                if 'resale' in cell_value:
                    try:
                        resale_value = str(sheet.cell_value(row_idx, col_idx + 1)).lower()
                        if 'resale' in resale_value and 'no' not in resale_value:
                            data['resale_designation'] = 'resale'
                            if self.debug_mode:
                                _logger.info("Resale designation set to 'resale'")
                    except Exception as e:
                        if self.debug_mode:
                            _logger.warning(f"Error extracting resale designation: {str(e)}")

    def _map_columns(self, sheet, header_row_idx):
        """Map column indices based on header names."""
        columns = {}
        header_count = 0
        
        for col_idx in range(sheet.ncols):
            header_value = str(sheet.cell_value(header_row_idx, col_idx)).lower().strip()
            
            # Map common header terms to field names
            if 'purchase type' in header_value:
                columns['purchase_type'] = col_idx
                header_count += 1
            elif any(term in header_value for term in ['part number', 'part #', 'item number']):
                columns['part_number'] = col_idx
                header_count += 1
            elif 'description' in header_value:
                columns['description'] = col_idx
                header_count += 1
            elif header_value in ['uom', 'unit', 'units']:
                columns['uom'] = col_idx
                header_count += 1
            elif header_value in ['qty', 'quantity']:
                columns['qty'] = col_idx
                header_count += 1
            elif any(term in header_value for term in ['price', 'cost', 'unit price']):
                columns['price'] = col_idx
                header_count += 1
            elif header_value == 'job':
                columns['job'] = col_idx
                header_count += 1
            elif 'expense type' in header_value:
                columns['expense_type'] = col_idx
                header_count += 1
            elif 'pop start' in header_value:
                columns['pop_start'] = col_idx
                header_count += 1
            elif 'pop end' in header_value:
                columns['pop_end'] = col_idx
                header_count += 1
            elif header_value in ['mfr', 'manufacturer']:
                columns['mfr'] = col_idx
                header_count += 1
            elif any(term in header_value for term in ['mfr pn', 'mfr part', 'manufacturer pn']):
                columns['mfr_pn'] = col_idx
                header_count += 1
            elif 'cage' in header_value:
                columns['cage'] = col_idx
                header_count += 1
                
        # For this to be a valid header row, we need at least 3 recognized headers
        if header_count < 2:
            if self.debug_mode:
                _logger.info(f"Row {header_row_idx} doesn't appear to be a valid header row (only {header_count} headers found)")
            return {}
            
        return columns

    def _extract_line_items(self, sheet, header_row_idx, columns):
        """Extract line items from the sheet based on the mapped columns."""
        line_items = []
        
        # Process rows after the header
        for row_idx in range(header_row_idx + 1, sheet.nrows):
            try:
                # Check if this row has data by looking for description or part number
                has_data = False
                
                if 'description' in columns:
                    desc_value = sheet.cell_value(row_idx, columns['description'])
                    if desc_value and str(desc_value).strip():
                        has_data = True
                        
                if not has_data and 'part_number' in columns:
                    part_value = sheet.cell_value(row_idx, columns['part_number'])
                    if part_value and str(part_value).strip():
                        has_data = True
                        
                if not has_data:
                    continue
                
                # Create line data dictionary
                line_data = {
                    'purchase_type': 'direct_materials',  # Default
                    'name': '',
                    'product_uom_id': False,
                    'quantity': 1.0,
                    'price_unit': 0.0,
                    'expense_type': 'raw_materials',  # Default
                }
                
                # Fill in fields from mapped columns
                if 'purchase_type' in columns:
                    purchase_type = str(sheet.cell_value(row_idx, columns['purchase_type'])).strip()
                    line_data['purchase_type'] = self._determine_purchase_type(purchase_type)
                    
                if 'description' in columns:
                    line_data['name'] = str(sheet.cell_value(row_idx, columns['description'])).strip()
                    
                if 'uom' in columns:
                    uom_name = str(sheet.cell_value(row_idx, columns['uom'])).strip()
                    line_data['product_uom_id'] = self._get_uom_id(uom_name)
                    
                if 'qty' in columns:
                    qty_value = sheet.cell_value(row_idx, columns['qty'])
                    if qty_value and str(qty_value).strip():
                        try:
                            line_data['quantity'] = float(qty_value)
                        except (ValueError, TypeError):
                            pass  # Keep default if conversion fails
                            
                if 'price' in columns:
                    price_value = sheet.cell_value(row_idx, columns['price'])
                    if price_value and str(price_value).strip():
                        try:
                            line_data['price_unit'] = float(price_value)
                        except (ValueError, TypeError):
                            pass  # Keep default if conversion fails
                            
                if 'job' in columns:
                    job_name = str(sheet.cell_value(row_idx, columns['job'])).strip()
                    line_data['job'] = self._get_job_id(job_name)
                    
                if 'expense_type' in columns:
                    expense_type = str(sheet.cell_value(row_idx, columns['expense_type'])).strip()
                    line_data['expense_type'] = self._get_expense_type(expense_type)
                    
                if 'pop_start' in columns:
                    line_data['pop_start'] = self._convert_date(sheet.cell_value(row_idx, columns['pop_start']))
                    
                if 'pop_end' in columns:
                    line_data['pop_end'] = self._convert_date(sheet.cell_value(row_idx, columns['pop_end']))
                    
                if 'mfr' in columns:
                    line_data['manufacturer'] = str(sheet.cell_value(row_idx, columns['mfr'])).strip()
                    
                if 'mfr_pn' in columns:
                    line_data['manufacturer_number'] = str(sheet.cell_value(row_idx, columns['mfr_pn'])).strip()
                    
                if 'cage' in columns:
                    line_data['cage_code'] = str(sheet.cell_value(row_idx, columns['cage'])).strip()
                
                # Find or create product
                product = self._find_or_create_product(
                    sheet, row_idx, columns, line_data,
                    part_number_col=columns.get('part_number')
                )
                
                if product:
                    line_data['product_id'] = product.id
                    # If we didn't get a UOM from the file, use the product's UOM
                    if not line_data['product_uom_id']:
                        line_data['product_uom_id'] = product.uom_po_id.id or product.uom_id.id
                    
                    # Add line if it has minimum required fields
                    if line_data['name'] and line_data['product_id'] and line_data['product_uom_id']:
                        line_items.append((0, 0, line_data))
                        if self.debug_mode:
                            _logger.info(f"Added line item: {line_data['name']}")
                    
            except Exception as e:
                if self.debug_mode:
                    _logger.warning(f"Error processing row {row_idx}: {str(e)}", exc_info=True)
                
        return line_items
    
    def _extract_line_from_row(self, sheet, row_idx):
        """Extract a line item directly from a row without relying on headers."""
        try:
            # Try to identify which columns have which type of data based on content
            description_col = None
            part_number_col = None
            quantity_col = None
            price_col = None
            
            for col_idx in range(min(15, sheet.ncols)):
                cell_value = sheet.cell_value(row_idx, col_idx)
                cell_str = str(cell_value).strip()
                
                # Part numbers often have digits and are relatively short
                if not part_number_col and len(cell_str) > 3 and len(cell_str) < 30 and any(c.isdigit() for c in cell_str):
                    part_number_col = col_idx
                
                # Descriptions are usually longer text
                elif not description_col and len(cell_str) > 10:
                    description_col = col_idx
                
                # Quantities are typically small numbers
                elif not quantity_col and isinstance(cell_value, (int, float)) and 0 < cell_value < 1000:
                    quantity_col = col_idx
                
                # Prices are typically larger numbers than quantities
                elif not price_col and isinstance(cell_value, (int, float)) and cell_value > 0:
                    if not quantity_col:
                        quantity_col = col_idx
                    else:
                        price_col = col_idx
            
            # If we couldn't determine key columns, skip this row
            if not description_col and not part_number_col:
                return None
            
            # Create line data
            line_data = {
                'purchase_type': 'direct_materials',  # Default
                'name': sheet.cell_value(row_idx, description_col) if description_col is not None else '',
                'quantity': float(sheet.cell_value(row_idx, quantity_col)) if quantity_col is not None else 1.0,
                'price_unit': float(sheet.cell_value(row_idx, price_col)) if price_col is not None else 0.0,
                'expense_type': 'raw_materials',  # Default
            }
            
            # Find or create product
            part_number = sheet.cell_value(row_idx, part_number_col) if part_number_col is not None else ''
            
            # Try to find the product by part number
            product = False
            if part_number:
                product = self.env['product.product'].search([
                    ('default_code', '=', part_number)
                ], limit=1)
            
            # If not found by part number, try by name
            if not product and line_data['name']:
                product = self.env['product.product'].search([
                    ('name', 'ilike', line_data['name']),
                    ('purchase_ok', '=', True)
                ], limit=1)
            
            # If still not found, create a generic product
            if not product:
                if line_data['name']:
                    # Create a product based on the name
                    product = self.env['product.product'].create({
                        'name': line_data['name'],
                        'default_code': part_number if part_number else f'IMP-{row_idx}',
                        'type': 'consu',
                        'purchase_ok': True,
                    })
            
            if product:
                line_data['product_id'] = product.id
                line_data['product_uom_id'] = product.uom_po_id.id or product.uom_id.id
                return line_data
            
            return None
            
        except Exception as e:
            if self.debug_mode:
                _logger.warning(f"Error extracting line from row {row_idx}: {str(e)}", exc_info=True)
            return None

    def _find_or_create_product(self, sheet, row_idx, columns, line_data, part_number_col=None):
        """Find existing product or create a new one if needed."""
        product = False
        product_internal_ref = ""
        
        # Try to get part number from the dedicated column
        if part_number_col is not None:
            product_internal_ref = str(sheet.cell_value(row_idx, part_number_col)).strip()
            
        if self.debug_mode and product_internal_ref:
            _logger.info(f"Looking for product with internal reference: {product_internal_ref}")
        
        # Try to find by internal reference
        if product_internal_ref:
            product = self.env['product.product'].search([
                ('default_code', '=', product_internal_ref)
            ], limit=1)
        
        # Try to find by manufacturer number
        if not product and line_data.get('manufacturer_number'):
            product = self.env['product.product'].search([
                ('manufacturernumber', '=', line_data['manufacturer_number']),
                ('purchase_ok', '=', True)
            ], limit=1)
        
        # Try to find by name/description
        if not product and line_data.get('name'):
            product = self.env['product.product'].search([
                ('name', 'ilike', line_data['name']),
                ('purchase_ok', '=', True)
            ], limit=1)
        
        # If still not found, create a new product
        if not product:
            try:
                product_type = 'consu'
                if line_data['purchase_type'] in ['direct_services', 'indirect_services']:
                    product_type = 'service'
                
                # Create a new product
                vals = {
                    'name': line_data.get('name') or 'Imported Product',
                    'default_code': product_internal_ref or f'IMP-{row_idx}',
                    'type': product_type,
                    'purchase_ok': True,
                }
                
                if line_data.get('manufacturer'):
                    vals['manufacturer'] = line_data['manufacturer']
                    
                if line_data.get('manufacturer_number'):
                    vals['manufacturernumber'] = line_data['manufacturer_number']
                
                product = self.env['product.product'].create(vals)
                if self.debug_mode:
                    _logger.info(f"Created new product: {product.name}")
                    
            except Exception as e:
                if self.debug_mode:
                    _logger.error(f"Error creating product: {str(e)}")
        
        return product

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
            if self.debug_mode:
                _logger.warning(f"Error converting date {date_value}: {str(e)}")
        
        return False
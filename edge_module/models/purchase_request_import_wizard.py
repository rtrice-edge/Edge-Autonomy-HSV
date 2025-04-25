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
            
            # Check if purchase type column exists - required
            if 'purchase_type' not in columns:
                continue  # Skip this header row and try the next one

            # Process data rows
            line_items = self._extract_line_items(sheet, header_row_idx, columns)
            if line_items:
                data['request_line_ids'].extend(line_items)
                if self.debug_mode:
                    _logger.info(f"Found {len(line_items)} line items from header row {header_row_idx}")
        
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
                "No valid line items found in the Excel file. Please ensure your file has a 'Purchase Type' column.\n"
                "This is required for all line items."
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
                
        # For this to be a valid header row, we need at least purchase_type column
        if 'purchase_type' not in columns:
            if self.debug_mode:
                _logger.info(f"Row {header_row_idx} doesn't have required 'Purchase Type' column")
            return {}
            
        return columns

    def _extract_line_items(self, sheet, header_row_idx, columns):
        """Extract line items from the sheet based on the mapped columns."""
        line_items = []
        
        # Process rows after the header
        for row_idx in range(header_row_idx + 1, sheet.nrows):
            try:
                # Check if this row has a purchase type (required field)
                if 'purchase_type' not in columns:
                    continue
                    
                purchase_type_value = str(sheet.cell_value(row_idx, columns['purchase_type'])).strip()
                if not purchase_type_value:
                    continue  # Skip rows without a purchase type
                
                # Create line data dictionary
                line_data = {
                    'purchase_type': self._determine_purchase_type(purchase_type_value)
                }
                
                # Don't set defaults for other fields - let the form handle them based on purchase type
                
                # Fill in fields from mapped columns
                if 'description' in columns:
                    description = str(sheet.cell_value(row_idx, columns['description'])).strip()
                    if description:
                        line_data['name'] = description
                    else:
                        line_data['name'] = ''
                
                if 'uom' in columns:
                    uom_name = str(sheet.cell_value(row_idx, columns['uom'])).strip()
                    if uom_name:
                        line_data['product_uom_id'] = self._get_uom_id(uom_name)
                    
                if 'qty' in columns:
                    qty_value = sheet.cell_value(row_idx, columns['qty'])
                    if qty_value and str(qty_value).strip():
                        try:
                            line_data['quantity'] = float(qty_value)
                        except (ValueError, TypeError):
                            line_data['quantity'] = 0.0  # Set default value if conversion fails
                    else:
                        line_data['quantity'] = 0.0
                else:
                    line_data['quantity'] = 0.0
                            
                # Modify your _extract_line_items method to set a default price_unit value
                if 'price' in columns:
                    price_value = sheet.cell_value(row_idx, columns['price'])
                    if price_value and str(price_value).strip():
                        try:
                            line_data['price_unit'] = float(price_value)
                        except (ValueError, TypeError):
                            line_data['price_unit'] = 0.0  # Set default value if conversion fails
                    else:
                        line_data['price_unit'] = 0.0  # Set default if cell is empty
                else:
                    line_data['price_unit'] = 0.0  # Always set a default price if column not found
                            
                if 'job' in columns:
                    job_name = str(sheet.cell_value(row_idx, columns['job'])).strip()
                    if job_name:
                        line_data['job'] = self._get_job_id(job_name)
                    
                if 'expense_type' in columns:
                    expense_type = str(sheet.cell_value(row_idx, columns['expense_type'])).strip()
                    if expense_type:
                        line_data['expense_type'] = self._get_expense_type(expense_type)
                    
                if 'pop_start' in columns:
                    pop_start = self._convert_date(sheet.cell_value(row_idx, columns['pop_start']))
                    if pop_start:
                        line_data['pop_start'] = pop_start
                    
                if 'pop_end' in columns:
                    pop_end = self._convert_date(sheet.cell_value(row_idx, columns['pop_end']))
                    if pop_end:
                        line_data['pop_end'] = pop_end
                    
                if 'mfr' in columns:
                    manufacturer = str(sheet.cell_value(row_idx, columns['mfr'])).strip()
                    if manufacturer:
                        line_data['manufacturer'] = manufacturer
                    
                if 'mfr_pn' in columns:
                    mfr_pn = str(sheet.cell_value(row_idx, columns['mfr_pn'])).strip()
                    if mfr_pn:
                        line_data['manufacturer_number'] = mfr_pn
                    
                if 'cage' in columns:
                    cage_code = str(sheet.cell_value(row_idx, columns['cage'])).strip()
                    if cage_code:
                        line_data['cage_code'] = cage_code
                
                # For Direct Materials, try to find product by part number if provided
                if line_data['purchase_type'] == 'direct_materials' and 'part_number' in columns:
                    part_number = str(sheet.cell_value(row_idx, columns['part_number'])).strip()
                    if part_number:
                        product = self.env['product.product'].search([
                            ('default_code', '=', part_number)
                        ], limit=1)
                        if product:
                            line_data['product_id'] = product.id
                        else:
                            raise UserError(_("Please enter a valid part number for direct materials."))
                
                # Set appropriate product for non-direct-materials based on purchase type
                if line_data['purchase_type'] != 'direct_materials':
                    if line_data['purchase_type'] == 'indirect_materials':
                        product = self.env['product.product'].search([
                            ('default_code', '=', 'IndirectMisc')
                        ], limit=1)
                        if product:
                            line_data['product_id'] = product.id
                    elif line_data['purchase_type'] == 'direct_services':
                        product = self.env['product.product'].search([
                            ('default_code', '=', 'DirectService')
                        ], limit=1)
                        if product:
                            line_data['product_id'] = product.id
                    elif line_data['purchase_type'] == 'indirect_services':
                        product = self.env['product.product'].search([
                            ('default_code', '=', 'IndirectService')
                        ], limit=1)
                        if product:
                            line_data['product_id'] = product.id
                
                # Add UOM for product if not specified
                if 'product_id' in line_data and 'product_uom_id' not in line_data:
                    product = self.env['product.product'].browse(line_data['product_id'])
                    line_data['product_uom_id'] = product.uom_po_id.id or product.uom_id.id
                
                # Add the line if it has the required purchase_type and name
                if 'purchase_type' in line_data and 'product_id' in line_data and 'name' in line_data:
                    line_items.append((0, 0, line_data))
                    if self.debug_mode:
                        _logger.info(f"Added line item: {line_data.get('name', 'No description')} - {line_data['purchase_type']}")
                
            except Exception as e:
                if self.debug_mode:
                    _logger.warning(f"Error processing row {row_idx}: {str(e)}", exc_info=True)
                
        return line_items

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
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
            supplier_name = sheet.cell_value(11, 1).strip()
            if supplier_name and supplier_name != 'Suggested Supplier':
                supplier = self.env['res.partner'].search([
                    ('name', 'ilike', supplier_name),
                    ('supplier_rank', '>', 0)
                ], limit=1)
                if supplier:
                    data['partner_id'] = supplier.id
        except Exception as e:
            _logger.warning("Error extracting supplier: %s", str(e))

        # Production Stoppage (row 14, column B)
        try:
            production_stoppage = sheet.cell_value(13, 1).strip()
            if production_stoppage in ['Yes', 'True', '1']:
                data['production_stoppage'] = True
        except Exception as e:
            _logger.warning("Error extracting production stoppage: %s", str(e))

        # Need by date (row 15, column B)
        try:
            need_by_date = sheet.cell_value(14, 1)
            if isinstance(need_by_date, str) and need_by_date.strip():
                try:
                    # Try to convert to odoo date format if it's a string
                    from datetime import datetime
                    date_obj = datetime.strptime(need_by_date, '%m/%d/%Y')
                    data['need_by_date'] = date_obj.strftime('%Y-%m-%d')
                except Exception:
                    # If conversion fails, just use the value as is
                    data['need_by_date'] = need_by_date
        except Exception as e:
            _logger.warning("Error extracting need by date: %s", str(e))

        # Delivery Location (row 16, column B)
        try:
            delivery_location = sheet.cell_value(15, 1).strip()
            if delivery_location and delivery_location.lower() == 'other':
                data['deliver_to_address'] = 'other'
        except Exception as e:
            _logger.warning("Error extracting delivery location: %s", str(e))

        # Delivery Address (row 17, column B)
        try:
            delivery_address = sheet.cell_value(16, 1).strip()
            if delivery_address and data['deliver_to_address'] == 'other':
                data['deliver_to_other_address'] = delivery_address
        except Exception as e:
            _logger.warning("Error extracting delivery address: %s", str(e))

        # Delivery Point of Contact (row 18, column B)
        try:
            delivery_contact = sheet.cell_value(17, 1).strip()
            if delivery_contact and data['deliver_to_address'] == 'other':
                data['deliver_to_other'] = delivery_contact
        except Exception as e:
            _logger.warning("Error extracting delivery contact: %s", str(e))

        # Delivery POC Phone Number (row 19, column B)
        try:
            delivery_phone = sheet.cell_value(18, 1).strip()
            if delivery_phone and data['deliver_to_address'] == 'other':
                data['deliver_to_other_phone'] = delivery_phone
        except Exception as e:
            _logger.warning("Error extracting delivery phone: %s", str(e))

        # Invoice Approver (row 20, column B)
        try:
            invoice_approver = sheet.cell_value(19, 1).strip()
            if invoice_approver:
                user = self.env['res.users'].search([
                    ('name', 'ilike', invoice_approver)
                ], limit=1)
                if user:
                    data['invoice_approver_id'] = user.id
        except Exception as e:
            _logger.warning("Error extracting invoice approver: %s", str(e))

        # Resale/No Resale (row 21, column B)
        try:
            resale_designation = sheet.cell_value(20, 1).strip().lower()
            if resale_designation == 'resale':
                data['resale_designation'] = 'resale'
        except Exception as e:
            _logger.warning("Error extracting resale designation: %s", str(e))

        # Notes/Links (row 22, column B)
        try:
            notes = sheet.cell_value(21, 1).strip()
            if notes and notes != 'Notes/Links':
                data['requester_notes'] = notes
        except Exception as e:
            _logger.warning("Error extracting notes: %s", str(e))

        # Extract line items - start from row 25
        row = 24
        while row < sheet.nrows:
            try:
                # Skip the header row
                if row == 24:
                    row += 1
                    continue
                
                # Check if we've reached the end of the data
                if not sheet.cell_value(row, 1).strip():
                    row += 1
                    continue
                
                # Extract line data
                line_data = {
                    'purchase_type': self._determine_purchase_type(sheet.cell_value(row, 0).strip()),
                    'name': sheet.cell_value(row, 2).strip(),  # Description
                    'product_uom_id': self._get_uom_id(sheet.cell_value(row, 3).strip()),  # UOM
                    'quantity': sheet.cell_value(row, 4) or 1.0,  # Qty
                    'price_unit': sheet.cell_value(row, 5) or 0.0,  # Est Unit Price
                    'job': self._get_job_id(sheet.cell_value(row, 7).strip()),  # Job
                    'expense_type': self._get_expense_type(sheet.cell_value(row, 8).strip()),  # Expense Type
                    'pop_start': self._convert_date(sheet.cell_value(row, 9)),  # POP Start
                    'pop_end': self._convert_date(sheet.cell_value(row, 10)),  # POP End
                    'manufacturer': sheet.cell_value(row, 11).strip(),  # Mfr
                    'manufacturer_number': sheet.cell_value(row, 12).strip(),  # Mfr PN
                    'cage_code': sheet.cell_value(row, 13).strip(),  # CAGE Code
                }
                
                # Find product by internal reference or create a placeholder
                product_internal_ref = sheet.cell_value(row, 1).strip()  # Edge Internal Part Number
                product = False
                
                if product_internal_ref:
                    product = self.env['product.product'].search([
                        ('default_code', '=', product_internal_ref)
                    ], limit=1)
                
                if not product:
                    # First try to find by manufacturer number if available
                    if line_data['manufacturer_number']:
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
                            # For direct materials, we need to identify or create a product
                            # Use a generic product for now
                            product = self.env.ref('product.product_product_consumable', raise_if_not_found=False)
                        elif line_data['purchase_type'] == 'indirect_materials':
                            product = self.env['product.product'].search([
                                ('default_code', '=', 'IndirectMisc')
                            ], limit=1)
                        elif line_data['purchase_type'] == 'direct_services':
                            product = self.env['product.product'].search([
                                ('default_code', '=', 'DirectService')
                            ], limit=1)
                        elif line_data['purchase_type'] == 'indirect_services':
                            product = self.env['product.product'].search([
                                ('default_code', '=', 'IndirectService')
                            ], limit=1)
                
                if product:
                    line_data['product_id'] = product.id
                    # If we didn't get a UOM from the file, use the product's UOM
                    if not line_data['product_uom_id']:
                        line_data['product_uom_id'] = product.uom_po_id.id or product.uom_id.id
                
                # Add line to the list if it has product and name
                if line_data.get('product_id') and line_data['name']:
                    data['request_line_ids'].append((0, 0, line_data))
                
                row += 1
            except Exception as e:
                _logger.warning("Error processing line %s: %s", row, str(e))
                row += 1

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
            raise UserError(_("No valid line items found in the Excel file. product_internal_ref: %s, product: %s", product_internal_ref, product.id if product else 'None'))

    def _determine_purchase_type(self, value):
        """Determine the purchase type based on the Excel value."""
        value = value.lower() if isinstance(value, str) else ""
        
        if 'direct' in value and 'material' in value:
            return 'direct_materials'
        elif 'direct' in value and 'service' in value:
            return 'direct_services'
        elif 'indirect' in value and 'material' in value:
            return 'indirect_materials'
        elif 'indirect' in value and 'service' in value:
            return 'indirect_services'
        
        # Default
        return 'direct_materials'

    def _get_uom_id(self, uom_name):
        """Find the UOM ID based on the name from Excel."""
        if not uom_name:
            return False
            
        # Try to find the UOM
        uom = self.env['uom.uom'].search([
            '|', ('name', '=ilike', uom_name),
            ('name', '=ilike', uom_name.replace(' ', '')),
        ], limit=1)
        
        if uom:
            return uom.id
        
        # Return the default UOM (EA) if not found
        default_uom = self.env.ref('uom.product_uom_unit', raise_if_not_found=False)
        return default_uom.id if default_uom else False
    
    def _get_job_id(self, job_name):
        """Find the job ID based on the name or number from Excel."""
        if not job_name:
            return False
            
        # Try to find the job by name or number
        job = self.env['job'].search([
            '|', ('name', '=ilike', job_name),
            ('number', '=ilike', job_name),
        ], limit=1)
        
        if job:
            return job.id
        
        return False
    
    def _get_expense_type(self, expense_type_name):
        """Map the expense type name to Odoo's expense type options."""
        if not expense_type_name:
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
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import base64
import io
import logging
import xlrd

_logger = logging.getLogger(__name__)

class PurchaseRequestImportWizard(models.TransientModel):
    _name = 'purchase.request.import.wizard'
    _description = 'Purchase Request Import Wizard'

    excel_file = fields.Binary(string='Excel File', required=True)
    filename = fields.Char(string='Filename')

    def action_import(self):
        """Process the Excel file and import data into the purchase request form"""
        if not self.excel_file:
            raise UserError(_("Please upload an Excel file."))

        # Get active model and ID
        active_id = self.env.context.get('active_id')
        active_model = self.env.context.get('active_model')
        
        if not active_id or active_model != 'purchase.request':
            raise UserError(_("This wizard should only be called from a purchase request form."))
        
        request = self.env['purchase.request'].browse(active_id)
        
        # Process Excel file
        try:
            # Decode file content
            file_content = base64.b64decode(self.excel_file)
            excel_fileobj = io.BytesIO(file_content)
            
            # Open workbook
            workbook = xlrd.open_workbook(file_contents=excel_fileobj.getvalue())
            sheet = workbook.sheet_by_index(0)
            
            # Map Excel data to form fields
            form_values = {}
            line_values = []
            
            # The following mappings need to be adjusted based on exact Excel template structure
            # Sheet headers (row, column) for the main form fields
            headers = {
                'supplier': (12, 1),  # Suggested Supplier (B13)
                'production_stoppage': (14, 1),  # Production Stoppage (B15)
                'need_by_date': (15, 1),  # Need Date (B16)
                'delivery_location': (16, 1),  # Delivery Location (B17)
                'delivery_address': (17, 1),  # Delivery Address (B18)
                'delivery_contact': (18, 1),  # Delivery Point of Contact (B19)
                'delivery_phone': (19, 1),  # Delivery POC Phone Number (B20)
                'invoice_approver': (20, 1),  # Invoice Approver (B21)
                'resale_designation': (21, 1),  # Resale/No Resale (B22)
                'notes': (22, 1),  # Notes/Links (B23)
            }
            
            # Extract values from the Excel
            supplier_name = self._get_cell_value(sheet, headers['supplier'][0], headers['supplier'][1])
            production_stoppage = self._get_cell_value(sheet, headers['production_stoppage'][0], headers['production_stoppage'][1])
            need_by_date = self._get_cell_value(sheet, headers['need_by_date'][0], headers['need_by_date'][1])
            delivery_location = self._get_cell_value(sheet, headers['delivery_location'][0], headers['delivery_location'][1])
            delivery_address = self._get_cell_value(sheet, headers['delivery_address'][0], headers['delivery_address'][1])
            delivery_contact = self._get_cell_value(sheet, headers['delivery_contact'][0], headers['delivery_contact'][1])
            delivery_phone = self._get_cell_value(sheet, headers['delivery_phone'][0], headers['delivery_phone'][1])
            invoice_approver = self._get_cell_value(sheet, headers['invoice_approver'][0], headers['invoice_approver'][1])
            resale_designation = self._get_cell_value(sheet, headers['resale_designation'][0], headers['resale_designation'][1])
            notes = self._get_cell_value(sheet, headers['notes'][0], headers['notes'][1])
            
            # Process values and set form values
            form_values = self._process_form_values(
                supplier_name, production_stoppage, need_by_date, 
                delivery_location, delivery_address, delivery_contact,
                delivery_phone, invoice_approver, resale_designation, notes
            )
            
            # Process line items starting from row 25
            line_start_row = 25
            for row in range(line_start_row, sheet.nrows):
                # Skip if the row is empty
                if not any(self._get_cell_value(sheet, row, col) for col in range(sheet.ncols)):
                    continue
                
                line = self._process_line_item(sheet, row)
                if line:
                    line_values.append(line)
            
            # Update the request with form values
            request.write(form_values)
            
            # Clear existing lines and create new ones
            if line_values:
                request.request_line_ids.unlink()
                for line_vals in line_values:
                    self.env['purchase.request.line'].create(dict(
                        request_id=request.id,
                        **line_vals
                    ))
            
            return {'type': 'ir.actions.act_window_close'}
            
        except Exception as e:
            _logger.exception("Error processing Excel file")
            raise UserError(_("Error processing Excel file: %s") % str(e))

    def _get_cell_value(self, sheet, row, col):
        """Extract cell value from Excel sheet"""
        try:
            cell = sheet.cell(row, col)
            if cell.ctype == xlrd.XL_CELL_DATE:
                # Handle date values
                date_tuple = xlrd.xldate_as_tuple(cell.value, sheet.book.datemode)
                return fields.Date.to_string(fields.Date.from_string(f"{date_tuple[0]}-{date_tuple[1]}-{date_tuple[2]}"))
            elif cell.ctype == xlrd.XL_CELL_NUMBER:
                # Handle numeric values
                if cell.value == int(cell.value):
                    return int(cell.value)
                return cell.value
            elif cell.ctype == xlrd.XL_CELL_BOOLEAN:
                # Handle boolean values
                return bool(cell.value)
            else:
                # Handle text and other types
                return str(cell.value).strip() if cell.value else False
        except IndexError:
            return False

    def _process_form_values(self, supplier_name, production_stoppage, need_by_date,
                            delivery_location, delivery_address, delivery_contact,
                            delivery_phone, invoice_approver, resale_designation, notes):
        """Process and map Excel values to form fields"""
        values = {}
        
        # Process supplier
        if supplier_name:
            partner = self.env['res.partner'].search([
                ('name', 'ilike', supplier_name),
                ('supplier_rank', '>', 0)
            ], limit=1)
            if partner:
                values['partner_id'] = partner.id
        
        # Process production stoppage
        if production_stoppage and isinstance(production_stoppage, str):
            values['production_stoppage'] = 'yes' in production_stoppage.lower() or 'true' in production_stoppage.lower()
        
        # Process need by date
        if need_by_date:
            try:
                values['need_by_date'] = need_by_date
            except ValueError:
                _logger.warning(f"Could not convert {need_by_date} to date")
        
        # Process delivery location
        if delivery_location:
            values['deliver_to_address'] = 'other' if 'other' in delivery_location.lower() else 'edge_slo'
        
        # Process delivery information for external delivery
        if values.get('deliver_to_address') == 'other':
            values['deliver_to_other_address'] = delivery_address
            values['deliver_to_other'] = delivery_contact
            values['deliver_to_other_phone'] = delivery_phone
        elif delivery_contact:
            # Try to find employee by name
            employee = self.env['hr.employee'].search([
                ('name', 'ilike', delivery_contact)
            ], limit=1)
            if employee:
                values['deliver_to'] = employee.id
        
        # Process invoice approver
        if invoice_approver:
            user = self.env['res.users'].search([
                ('name', 'ilike', invoice_approver)
            ], limit=1)
            if user:
                values['invoice_approver_id'] = user.id
        
        # Process resale designation
        if resale_designation:
            if 'no' in resale_designation.lower():
                values['resale_designation'] = 'no_resale'
            else:
                values['resale_designation'] = 'resale'
        
        # Process notes
        if notes:
            values['requester_notes'] = notes
        
        return values

    def _process_line_item(self, sheet, row):
        """Process Excel row into purchase request line values"""
        # Map columns to field names
        col_map = {
            'purchase_type': 0,  # Purchase Type
            'product_id': 1,     # Edge Internal Part Number
            'name': 2,           # Description
            'product_uom_id': 3, # UOM
            'quantity': 4,       # Qty
            'price_unit': 5,     # Est Unit Price
            'job': 7,            # Job
            'expense_type': 8,   # Expense Type
            'pop_start': 9,      # POP Start
            'pop_end': 10,       # POP End
            'manufacturer': 11,  # Mfr
            'manufacturer_number': 12, # Mfr PN
            'cage_code': 13,     # CAGE Code
        }
        
        # Get values from row
        purchase_type = self._get_cell_value(sheet, row, col_map['purchase_type'])
        product_code = self._get_cell_value(sheet, row, col_map['product_id'])
        description = self._get_cell_value(sheet, row, col_map['name'])
        uom_name = self._get_cell_value(sheet, row, col_map['product_uom_id'])
        quantity = self._get_cell_value(sheet, row, col_map['quantity'])
        price_unit = self._get_cell_value(sheet, row, col_map['price_unit'])
        job_name = self._get_cell_value(sheet, row, col_map['job'])
        expense_type = self._get_cell_value(sheet, row, col_map['expense_type'])
        pop_start = self._get_cell_value(sheet, row, col_map['pop_start'])
        pop_end = self._get_cell_value(sheet, row, col_map['pop_end'])
        manufacturer = self._get_cell_value(sheet, row, col_map['manufacturer'])
        manufacturer_number = self._get_cell_value(sheet, row, col_map['manufacturer_number'])
        cage_code = self._get_cell_value(sheet, row, col_map['cage_code'])
        
        # Skip if essential fields are empty
        if not (product_code or description):
            return False
        
        line_vals = {}
        
        # Determine purchase type
        if purchase_type:
            if 'direct' in purchase_type.lower() and 'material' in purchase_type.lower():
                line_vals['purchase_type'] = 'direct_materials'
            elif 'direct' in purchase_type.lower() and 'service' in purchase_type.lower():
                line_vals['purchase_type'] = 'direct_services'
            elif 'indirect' in purchase_type.lower() and 'material' in purchase_type.lower():
                line_vals['purchase_type'] = 'indirect_materials'
            elif 'indirect' in purchase_type.lower() and 'service' in purchase_type.lower():
                line_vals['purchase_type'] = 'indirect_services'
        
        # Find product
        if product_code:
            product = self.env['product.product'].search([
                '|', 
                ('default_code', '=', product_code),
                ('name', '=', product_code)
            ], limit=1)
            if product:
                line_vals['product_id'] = product.id
        
        # Set description
        if description:
            line_vals['name'] = description
        
        # Find UOM
        if uom_name:
            uom = self.env['uom.uom'].search([
                ('name', 'ilike', uom_name)
            ], limit=1)
            if uom:
                line_vals['product_uom_id'] = uom.id
        
        # Set quantity
        if quantity:
            line_vals['quantity'] = float(quantity)
        
        # Set price
        if price_unit:
            line_vals['price_unit'] = float(price_unit)
        
        # Find job
        if job_name:
            job = self.env['job'].search([
                '|',
                ('name', 'ilike', job_name),
                ('number', '=', job_name)
            ], limit=1)
            if job:
                line_vals['job'] = job.id
        
        # Map expense type
        if expense_type:
            # This mapping needs to be adjusted based on the actual expense type values in Odoo
            expense_mapping = {
                'inventory': 'raw_materials',
                'raw material': 'raw_materials',
                'consumable': 'consumables',
                'tooling': 'small_tooling',
                'manufacturing': 'manufacturing_supplies',
                'engineering': 'engineering_supplies',
                'office': 'office_supplies',
                'building': 'building_supplies',
                'janitorial': 'janitorial',
                'communications': 'communications',
                'utilities': 'utilities',
                'flight': 'flight_ops',
                'hardware': 'it_hardware',
                'software': 'it_software',
                'services': 'it_services',
                'repair': 'repairs',
                'business': 'business_dev',
                'training': 'training',
                'license': 'licenses',
                'vehicle': 'vehicle',
                'rental': 'equipment_rental',
                'morale': 'employee_morale',
                'safety': 'safety',
                'marketing': 'marketing',
                'recruiting': 'recruiting',
                'shipping': 'shipping',
                'award': 'direct_award',
                'capital': 'capex',
                'subcontract': 'subcontractors'
            }
            
            for key, value in expense_mapping.items():
                if key in expense_type.lower():
                    line_vals['expense_type'] = value
                    break
        
        # Set POP dates
        if pop_start:
            line_vals['pop_start'] = pop_start
        if pop_end:
            line_vals['pop_end'] = pop_end
        
        # Set manufacturer info
        if manufacturer:
            line_vals['manufacturer'] = manufacturer
        if manufacturer_number:
            line_vals['manufacturer_number'] = manufacturer_number
        if cage_code:
            line_vals['cage_code'] = cage_code
        
        return line_vals
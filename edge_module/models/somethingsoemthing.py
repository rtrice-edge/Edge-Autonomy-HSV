# -*- coding: utf-8 -*-
# Script to be run in Odoo Shell (`odoo-bin shell -d <database_name>`)
# Purpose: For a list of top-level products (by default_code), recursively
#          explode their BoMs, calculate total quantities for all components,
#          filter these components based on name patterns, and output the
#          results in a CSV grid format.

import logging
from collections import defaultdict
import csv
import io  # To write CSV to a string buffer

# Configure logging
# Change logging.INFO to logging.DEBUG for very detailed step-by-step output
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
_logger = logging.getLogger(__name__)


# --- Configuration ---
# List of default_codes for the TOP-LEVEL products whose BoMs you want to explode.
# Extracted from the user-provided image.
TOP_PRODUCT_CODES_LIST = [
    'A-012-0002-PF-802', 'ACC1000-803', 'D450XR-802', 'ENC1000-802',
    'ENC1000-809', 'FCS1000-801', 'FHS1000-802', 'FHS1000-815 Rev A',
    'P250i-4001', 'STK0062', 'STK0064', 'SUB1108', 'SUB1110', 'SYS0080 Rev 001',
]

# Define the list of text patterns to search for within the component's name/description.
# The script will show results for any component whose name contains ANY of these strings.
# These are the components that will form the columns of the grid.
FILTER_NAME_PATTERNS = [
    '114-105901', '114-105904', '114-106509', '114-106508',
    '114-105906', '107-102613', '114-105899', 'Battery Charger Power Supply',
    'Main FCR Battery Checker', 'VXE30 HBL Checker, Assembly', 'VXE30 Main Battery Charger', '116-106151-1',
    'Fuselage Power Harness to Battery', '107-102189-2', '107-102094',
]

# Set maximum recursion depth to prevent potential infinite loops in case of circular BoMs
MAX_DEPTH = 20
# --- End Configuration ---


def explode_bom_recursively(bom, component_totals_dict, factor=1.0, depth=0, visited_boms=None):
    """
    Recursively traverses a BoM structure and aggregates the total quantity
    of EVERY component found. Modifies the passed `component_totals_dict`.

    :param bom: The mrp.bom record to process.
    :param component_totals_dict: The dictionary to store component totals ({product: qty}).
                                   This dictionary is modified in place.
    :param factor: The cumulative quantity multiplier from parent BoMs.
    :param depth: Current recursion depth.
    :param visited_boms: A set of BoM IDs already visited in the current path.
    """
    # --- Base cases for recursion termination ---
    if not bom:
        return
    if depth > MAX_DEPTH:
        _logger.warning(f"{'  ' * depth}Max recursion depth ({MAX_DEPTH}) reached for BoM '{bom.display_name}'. Stopping this branch.")
        return

    # Initialize visited set for the top-level call of this specific branch
    if visited_boms is None:
        visited_boms = set()

    # --- Cycle detection ---
    if bom.id in visited_boms:
        _logger.warning(f"{'  ' * depth}Circular BoM detected: BoM ID {bom.id} ('{bom.display_name}') already visited. Skipping.")
        return

    visited_boms.add(bom.id)
    _logger.info(f"{'  ' * depth}Processing BoM: '{bom.display_name or 'Unnamed BoM'}' (Product: {bom.product_tmpl_id.name}, Factor: {factor:.4f}, Depth: {depth})")

    # --- Iterate through BoM lines (components) ---
    for line in bom.bom_line_ids:
        product = line.product_id
        if not product:
             _logger.warning(f"{'  ' * (depth + 1)}Skipping BoM line {line.id} - No product defined.")
             continue

        line_qty = line.product_qty
        current_total_qty = line_qty * factor

        _logger.debug(f"{'  ' * (depth + 1)}Component: {product.display_name} [{product.default_code or 'No Code'}] (Line Qty: {line_qty}, Cumulative Qty: {current_total_qty:.4f})")

        # Add the component and its calculated quantity to the overall totals dict
        component_totals_dict[product] += current_total_qty

        # --- Recursive Step: Find and process sub-BoM for the component ---
        sub_bom = env['mrp.bom'].search([
            ('product_tmpl_id', '=', product.product_tmpl_id.id),
            # ('company_id', '=', bom.company_id.id), # Add if multi-company
            ('product_id', 'in', [False, product.id]), # Match template or specific variant
            # ('type', '=', 'normal'), # Add if needed
        ], order='product_id, sequence, id', limit=1)

        if sub_bom:
             _logger.debug(f"{'  ' * (depth + 1)}Found sub-BoM '{sub_bom.display_name}' for {product.display_name}. Descending...")
             # Pass the *same* component_totals_dict down, but a *copy* of visited_boms
             explode_bom_recursively(sub_bom, component_totals_dict, current_total_qty, depth + 1, visited_boms.copy())
        else:
             _logger.debug(f"{'  ' * (depth + 1)}No further sub-BoM found for {product.display_name}")

    # --- Backtracking ---
    # Visited set removal happens implicitly by passing copies down in recursion


# --- Main Execution Block ---
if __name__ == '__main__':
    print(f"\nStarting Multi-BoM explosion process...")
    print(f"Processing {len(TOP_PRODUCT_CODES_LIST)} Top-Level Products.")
    print(f"Filtering for components with name/description containing: {FILTER_NAME_PATTERNS}")
    print("-" * 80)

    # Structure to hold the final grid data:
    # results_grid[top_product_code][filtered_component_identifier] = total_quantity
    results_grid = {}
    # Keep track of all unique filtered components found across all BoMs (for columns)
    all_filtered_component_identifiers = set()

    # --- Outer Loop: Iterate through each Top-Level Product Code ---
    for top_code in TOP_PRODUCT_CODES_LIST:
        print(f"\nProcessing Top-Level Product Code: {top_code}")

        # Find the top-level product by its default_code
        top_product = env['product.product'].search([('default_code', '=', top_code)], limit=1)

        if not top_product:
            _logger.error(f"Product with code '{top_code}' not found. Skipping.")
            results_grid[top_code] = {'Error': 'Product Not Found'} # Mark error in results
            continue

        _logger.info(f"Found Top-Level Product: {top_product.display_name} [{top_product.default_code}] (ID: {top_product.id})")

        # Find the BoM for the selected top-level product
        top_bom = env['mrp.bom'].search([
            ('product_tmpl_id', '=', top_product.product_tmpl_id.id),
            ('product_id', 'in', [False, top_product.id]),
        ], order='product_id, sequence, id', limit=1)

        if not top_bom:
            _logger.error(f"No BoM found for product '{top_product.display_name}'. Skipping.")
            results_grid[top_code] = {'Error': 'BoM Not Found'} # Mark error in results
            continue

        _logger.info(f"Found BoM: '{top_bom.display_name or 'Unnamed BoM'}' (Ref: {top_bom.code or 'N/A'}, ID: {top_bom.id})")

        # --- BoM Explosion for the current top_product ---
        # Initialize a fresh dictionary to hold component totals for THIS top_product
        current_component_totals = defaultdict(float)
        explode_bom_recursively(top_bom, current_component_totals, factor=1.0)

        # --- Filter the results for the current top_product ---
        filtered_results_for_top_product = {}
        if not current_component_totals:
             _logger.info(f"BoM for {top_code} appears to be empty or only contains non-product lines.")
        else:
            _logger.info(f"Filtering {len(current_component_totals)} unique components found in BoM for {top_code}...")
            for product, total_qty in current_component_totals.items():
                product_desc = product.display_name or ""
                match_found = False
                for pattern in FILTER_NAME_PATTERNS:
                    if pattern.lower() in product_desc.lower():
                        match_found = True
                        break # Found a match for this product

                if match_found:
                    # Use default_code as identifier if available, otherwise display_name
                    comp_id = product.default_code or product.display_name
                    filtered_results_for_top_product[comp_id] = total_qty
                    all_filtered_component_identifiers.add(comp_id) # Add to set of all column headers
                    _logger.debug(f"  Match: '{comp_id}' (Qty: {total_qty:.4f})")

        # Store the filtered results for this top_code
        results_grid[top_code] = filtered_results_for_top_product
        print(f"Finished processing {top_code}. Found {len(filtered_results_for_top_product)} matching components.")

    # --- Format and Print Results Grid (CSV) ---
    print("-" * 80)
    print("\n--- Results Grid (CSV Format) ---")

    if not all_filtered_component_identifiers:
        print("No components matching the filter patterns were found in any of the processed BoMs.")
    else:
        # Sort column headers alphabetically
        sorted_headers = sorted(list(all_filtered_component_identifiers))

        # Use io.StringIO to build the CSV in memory
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

        # Write Header Row
        header_row = ["Top Product Code"] + sorted_headers
        writer.writerow(header_row)

        # Write Data Rows
        for top_code in TOP_PRODUCT_CODES_LIST:
            row_data = [top_code]
            results_for_row = results_grid.get(top_code, {})

            # Check if there was an error processing this row
            if 'Error' in results_for_row:
                 row_data.extend([results_for_row['Error']] * len(sorted_headers)) # Fill row with error message
            else:
                for header in sorted_headers:
                    qty = results_for_row.get(header, 0.0) # Get qty, default to 0.0 if not found
                    row_data.append(f"{qty:.4f}") # Format quantity to 4 decimal places

            writer.writerow(row_data)

        # Print the CSV content
        print(output.getvalue())
        output.close()

    print("-" * 80)
    print("\nScript finished.")

# --- End of Script ---
# To run:
# 1. Ensure TOP_PRODUCT_CODES_LIST and FILTER_NAME_PATTERNS are set correctly.
# 2. Save this code as a .py file (e.g., bom_multi_grid.py) on your Odoo server OR copy-paste directly.
# 3. Open terminal/command prompt on your Odoo server.
# 4. Navigate to your Odoo source code directory (where odoo-bin is).
# 5. Run the shell: `python odoo-bin shell -d <your_database_name>`
# 6. If saved as file: `exec(open('bom_multi_grid.py').read())`
# 7. If copy-pasting: Paste the entire script content into the '>>>' prompt and press Enter.
# 8. Review the output. The final grid will be printed in CSV format. You can copy/paste this into a spreadsheet.


# -*- coding: utf-8 -*-
# Script to be run in Odoo Shell (`odoo-bin shell -d <database_name>`)
# Purpose: Find products based on name patterns and output their
#          default_codes in a comma-separated, single-quoted list.

# -*- coding: utf-8 -*-
# Script to be run in Odoo Shell (`odoo-bin shell -d <database_name>`)
# Purpose: Find products based on name patterns (searching the description field)
#          and output their default_codes in a comma-separated, single-quoted list.

import logging

# Configure logging (optional, can be helpful for debugging)
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
_logger = logging.getLogger(__name__)

# --- Configuration ---
# Define the list of text patterns to search for within the component's description field.
# These are the same patterns used in the main BoM script.
FILTER_NAME_PATTERNS = [
    '114-105901', '114-105904', '114-106509', '114-106508',
    '114-105906', '107-102613', '114-105899', 'Battery Charger Power Supply',
    'Main FCR Battery Checker', 'VXE30 HBL Checker, Assembly', 'VXE30 Main Battery Charger', '116-106151-1',
    'Fuselage Power Harness to Battery', '107-102189-2', '107-102094',
]
# --- End Configuration ---

# --- Main Execution Block ---
if __name__ == '__main__':
    print(f"\nSearching for products whose description contains:")
    print(f"{FILTER_NAME_PATTERNS}")
    print("-" * 40)

    # Use a set to store default codes to automatically handle duplicates
    found_default_codes = set()

    # Iterate through each pattern
    for pattern in FILTER_NAME_PATTERNS:
        _logger.info(f"Searching for pattern: '{pattern}' in product description")
        # Search for products matching the pattern (case-insensitive) in the description field
        # The 'description' field is typically on the product.template model.
        # We search through the related field from product.product.
        # Note: If you intended to search 'description_sale', change the field name below.
        matching_products = env['product.product'].search([('product_tmpl_id.name', 'ilike', f'%{pattern}%')])

        if not matching_products:
            _logger.info(f"  No products found with description matching '{pattern}'.")
            continue

        _logger.info(f"  Found {len(matching_products)} product(s) potentially matching '{pattern}' in description. Checking default codes...")
        # Iterate through found products and extract default codes
        for product in matching_products:
            if product.default_code:
                _logger.debug(f"    -> Found code: {product.default_code} for product: {product.display_name}")
                found_default_codes.add(product.default_code)
            else:
                _logger.debug(f"    -> Product '{product.display_name}' (ID: {product.id}) matches pattern in description but has no default_code.")

    # --- Format and Print Results ---
    print("-" * 40)
    if not found_default_codes:
        print("Result: No products with default codes found matching any of the patterns in their description.")
    else:
        # Sort the codes alphabetically for consistent output
        sorted_codes = sorted(list(found_default_codes))
        # Format the list into a comma-separated string with single quotes
        formatted_list = ", ".join([f"'{code}'" for code in sorted_codes])
        print("Resulting list of default_codes (from description match):")
        print(formatted_list)

    print("-" * 40)
    print("\nScript finished.")

# --- End of Script ---
# To run:
# 1. Copy this script.
# 2. Open terminal/command prompt on your Odoo server.
# 3. Navigate to your Odoo source code directory.
# 4. Run the shell: `python odoo-bin shell -d <your_database_name>`
# 5. Paste the script content into the '>>>' prompt and press Enter.
# 6. The script will print the formatted list of default codes found based on description search.


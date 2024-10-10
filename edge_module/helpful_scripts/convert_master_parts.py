import pandas as pd

def read_master_list(file_path):
    return pd.read_excel(file_path)

def create_odoo_import(master_df):
    odoo_df = pd.DataFrame()
    
    # Map columns from master list to Odoo import format
    odoo_df['id'] = ''  # Leave blank as products don't have external IDs yet
    odoo_df['name'] = master_df['Description']
    odoo_df['default_code'] = master_df['Part Number']
    odoo_df['type'] = 'product'  # Assuming all are storable products
    odoo_df['categ_id'] = 'All'  # Default category, adjust as needed
    
    # Set routes based on Make/Buy
    odoo_df['route_ids/id'] = master_df['Make Or Buy'].apply(
        lambda x: 'stock.route_warehouse0_mto,mrp.route_warehouse0_manufacture' if x == 'Make' 
        else 'purchase_stock.route_warehouse0_buy'
    )
    
    # Set 'can be purchased' and 'can be sold'
    odoo_df['purchase_ok'] = True
    odoo_df['sale_ok'] = master_df['Make Or Buy'].apply(lambda x: True if x == 'Make' else False)
    odoo_df['iuid_required'] = master_df['IUID Required'].apply(lambda x: True if x == 'Yes' else False)
    
    # Fill NaN values with False for iuid_required
    odoo_df['iuid_required'] = odoo_df['iuid_required'].fillna(False)

    # Process Obsolete field and map to archived
    odoo_df['active'] = master_df['Obsolete'].apply(lambda x: False if x == 'Yes' else True)
    
    # Fill NaN values with False for archived
    odoo_df['active'] = odoo_df['active'].fillna(False)

    # Process ECCN field
    odoo_df['eccn'] = master_df['Export Control Classification Number']
    # Map other fields
    odoo_df['standard_price'] = master_df['Unit Cost']
    odoo_df['ncnr'] = master_df['NCNR']  # Assuming if NCNR has a value, it's non-cancellable
    country_mapping = {
        "USA": "base.us",
        "Canada": "base.ca",
        "Indonesia": "base.id",
        "Mexico": "base.mx",
        "Latvia": "base.lv",
        "Peoples Republic of China": "base.cn",
        "Germany": "base.de"
    }
    
    # Map country of origin
    odoo_df['country_of_origin'] = master_df['Country of Origin'].map(country_mapping)

    
    return odoo_df

def main():
    master_file = 'Master Parts.xlsx'
    output_file = 'odoo_product_import.xlsx'
    
    master_df = read_master_list(master_file)
    odoo_df = create_odoo_import(master_df)
    
    odoo_df.to_excel(output_file, index=False)
    print(f"Odoo import file created: {output_file}")

if __name__ == "__main__":
    main()
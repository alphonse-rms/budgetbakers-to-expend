import csv
import json
import random
import uuid
import re
from datetime import datetime, timedelta
from collections import OrderedDict

# Color options for categories
COLORS = ["gray", "orange", "red", "green", "teal", "blue", "yellow", "purple"]

def generate_id_from_name(name):
    """Generate _id from category name (lowercase, replace special chars with -)"""
    # Convert to lowercase and replace spaces/special chars with hyphens
    result = re.sub(r'[^a-z0-9]+', '-', name.lower())
    # Remove leading/trailing hyphens
    return result.strip('-')

def generate_uuid():
    """Generate a UUID similar to the format in the JSON"""
    return str(uuid.uuid4())

def convert_utc3_to_utc(date_str):
    """Parse date from CSV (YYYY-mm-dd HH:MM:SS) in UTC+3 and convert to UTC"""
    try:
        # Parse the datetime string (assumed to be in UTC+3)
        dt_utc3 = datetime.strptime(date_str.strip(), "%Y-%m-%d %H:%M:%S")

        # Subtract 3 hours to convert from UTC+3 to UTC
        dt_utc = dt_utc3 - timedelta(hours=3)

        # Return in ISO format with Z (UTC)
        return dt_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    except Exception as e:
        print(f"Warning: Could not parse date '{date_str}': {e}")
        # Fallback to current date in UTC
        return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")

def load_json_template(json_file_path):
    """Load the uploaded JSON to get static data"""
    with open(json_file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def process_csv_to_json(csv_file_path, json_template):
    """Process CSV file and generate JSON backup"""

    # Read CSV file
    transactions_data = []
    with open(csv_file_path, 'r', encoding='utf-8') as f:
        # Using semicolon as delimiter
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            transactions_data.append(row)

    print(f"Read {len(transactions_data)} rows from CSV")

    # Step 1: Build unique categories from CSV records
    categories_from_csv = OrderedDict()
    for record in transactions_data:
        category_name = record['category'].strip()
        transaction_type = record['type'].strip()

        # Skip TRANSFER category
        if category_name.upper() == 'TRANSFER':
            continue

        if category_name not in categories_from_csv:
            categories_from_csv[category_name] = {
                'type': 'expense' if transaction_type == 'Expenses' else 'income'
            }

    # Create categories list starting with static categories (order=0)
    static_categories = [cat for cat in json_template['categories'] if cat.get('order') == 0]
    categories = []

    # Add static categories first
    for cat in static_categories:
        categories.append(cat.copy())

    # Add new categories from CSV
    order_counter = 1
    for category_name, category_info in categories_from_csv.items():
        category_obj = {
            "_id": generate_id_from_name(category_name),
            "name": category_name,
            "type": category_info['type'],
            "icon": "coin",
            "color": random.choice(COLORS),
            "deleted": False,
            "hidden": False,
            "subcategories": [],
            "order": order_counter
        }
        categories.append(category_obj)
        order_counter += 1

    # Create mapping for categories
    category_mapping = {}
    for cat in categories:
        if cat['name'] != "Transfer" and cat['name'] != "Transfer Fee":
            category_mapping[cat['name']] = cat['_id']

    print(f"Created {len(categories_from_csv)} new categories")

    # Step 2: Keep wallets from template
    wallets = json_template['wallets'].copy()

    # Create mapping for wallets (case-insensitive for better matching)
    wallet_mapping = {}
    wallet_name_mapping = {}  # Store original names for debugging
    for wallet in wallets:
        wallet_mapping[wallet['name'].lower()] = wallet['_id']
        wallet_name_mapping[wallet['name'].lower()] = wallet['name']

    print(f"Available wallets: {[w['name'] for w in wallets]}")

    # Track unmapped wallets for debugging
    unmapped_wallets = set()

    # Step 3: Process transactions
    transactions = []
    i = 0
    skipped_transfers = 0

    while i < len(transactions_data):
        record = transactions_data[i]
        transaction_type = record['type'].strip()
        category_name = record['category'].strip()
        account_name = record['account'].strip()

        # Find wallet ID
        wallet_id = wallet_mapping.get(account_name.lower(), "")
        if not wallet_id and account_name:
            unmapped_wallets.add(account_name)

        # Handle TRANSFER (two consecutive records)
        if category_name.upper() == 'TRANSFER' and i + 1 < len(transactions_data):
            next_record = transactions_data[i + 1]
            next_account_name = next_record['account'].strip()

            # Find destination wallet ID
            dest_wallet_id = wallet_mapping.get(next_account_name.lower(), "")
            if not dest_wallet_id and next_account_name:
                unmapped_wallets.add(next_account_name)

            # Skip if either wallet is missing
            if not wallet_id or not dest_wallet_id:
                print(f"WARNING: Skipping transfer - missing wallet mapping: '{account_name}' -> '{next_account_name}'")
                skipped_transfers += 1
                i += 2
                continue

            # Convert date from UTC+3 to UTC
            converted_date = convert_utc3_to_utc(record['date'])

            # Create transfer transaction
            transfer_transaction = {
                "_id": generate_uuid(),
                "name": record.get('note', '').replace('\n', ' & ') if record.get('note') else "",
                "type": "transfer",
                "category": "transfer",
                "subcategory": None,
                "amount": abs(int(float(record['amount']))),
                "destAmount": abs(int(float(next_record['amount']))),
                "srcWallet": wallet_id,
                "destWallet": dest_wallet_id,
                "conversionRate": 1,
                "dateCreated": converted_date,
                "lastUpdated": converted_date,
                "notes": record.get('note', '').replace('\n', ' & ') if record.get('note') else "",
                "debt": None,
                "secondaryCategory": None,
                "secondarySubcategory": None,
                "initialDebtTransaction": None,
                "budgets": [],
                "excludeFromBudgets": False
            }
            transactions.append(transfer_transaction)
            i += 2
            continue

        # Handle normal expense or income
        # Skip if wallet is missing (only for non-transfer transactions)
        if not wallet_id and account_name:
            print(f"WARNING: Skipping transaction - missing wallet mapping for '{account_name}'")
            unmapped_wallets.add(account_name)
            i += 1
            continue

        # Get category ID
        category_id = category_mapping.get(category_name, "")
        if not category_id and category_name.upper() != 'TRANSFER':
            print(f"WARNING: Missing category mapping for '{category_name}'")

        # Determine transaction type
        if transaction_type == "Expenses":
            trans_type = "expense"
        elif transaction_type == "Income":
            trans_type = "income"
        else:
            trans_type = transaction_type.lower()

        # Convert date from UTC+3 to UTC
        converted_date = convert_utc3_to_utc(record['date'])

        transaction = {
            "_id": generate_uuid(),
            "name": record.get('note', '').replace('\n', ' & ') if record.get('note') else "",
            "type": trans_type,
            "category": category_id,
            "subcategory": None,
            "amount": abs(int(float(record['amount']))),  # Use absolute value
            "destAmount": None,
            "srcWallet": wallet_id,
            "destWallet": None,
            "conversionRate": 1,
            "dateCreated": converted_date,
            "lastUpdated": converted_date,
            "notes": record.get('note', '').replace('\n', ' & ') if record.get('note') else "",
            "debt": None,
            "secondaryCategory": None,
            "secondarySubcategory": None,
            "initialDebtTransaction": None,
            "budgets": [],
            "excludeFromBudgets": False
        }
        transactions.append(transaction)
        i += 1

    # Print unmapped wallets warning
    if unmapped_wallets:
        print("\n" + "="*50)
        print("WARNING: The following wallet names in CSV were not found in the JSON template:")
        for wallet in sorted(unmapped_wallets):
            print(f"  - '{wallet}'")
        print("\nPlease add these wallets to the JSON template or update the CSV to use existing wallet names.")
        print("Available wallet names:", [w['name'] for w in wallets])
        print("="*50 + "\n")

    if skipped_transfers > 0:
        print(f"NOTE: Skipped {skipped_transfers} transfer transactions due to missing wallet mappings")

    # Build the complete JSON structure
    output_json = {
        "categories": categories,
        "subcategories": [],
        "wallets": wallets,
        "budgets": [],
        "templates": json_template['templates'].copy(),
        "transactions": transactions,
        "recurringTransactions": [],
        "debts": [],
        "profile": json_template['profile'].copy()
    }

    return output_json

def main():
    # File paths
    csv_file = input("Enter the path to your Budgetbakers Wallet CSV file (example: report_2026-04-16_164728.csv): ").strip()
    json_template_file = input("Enter the path to your eXpend backup file (example: expend-backup-20260416_152825.json): ").strip()

    # Load JSON template
    print(f"\nLoading template from {json_template_file}...")
    try:
        json_template = load_json_template(json_template_file)
        print(f"Template loaded successfully")
    except FileNotFoundError:
        print(f"Error: Template file '{json_template_file}' not found!")
        return
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in template file: {e}")
        return

    # Process CSV to JSON
    print(f"\nProcessing CSV file {csv_file}...")
    try:
        result_json = process_csv_to_json(csv_file, json_template)
    except FileNotFoundError:
        print(f"Error: CSV file '{csv_file}' not found!")
        return
    except Exception as e:
        print(f"Error processing CSV: {e}")
        return

    # Generate output filename
    timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    output_file = f"import-from-budgetbakers-{timestamp}.json"

    # Write JSON to file
    print(f"\nWriting output to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result_json, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Success! Generated {output_file}")
    print(f"  - Total categories: {len(result_json['categories'])}")
    print(f"  - New categories added: {len([c for c in result_json['categories'] if c.get('order', 0) > 0])}")
    print(f"  - Total transactions: {len(result_json['transactions'])}")
    print(f"  - Total wallets: {len(result_json['wallets'])}")

    # Show date conversion info
    if result_json['transactions']:
        print(f"\n  - Date conversion: UTC+3 → UTC applied to all {len(result_json['transactions'])} transactions")
        print(f"  - Example date (first transaction): {result_json['transactions'][0]['dateCreated']}")

    # Validate that no srcWallet is empty
    empty_wallet_tx = [tx for tx in result_json['transactions'] if tx.get('srcWallet') == ""]
    if empty_wallet_tx:
        print(f"\n⚠️  WARNING: {len(empty_wallet_tx)} transactions have empty srcWallet!")
        print("   These transactions were skipped. Check the wallet names in your CSV.")

if __name__ == "__main__":
    main()

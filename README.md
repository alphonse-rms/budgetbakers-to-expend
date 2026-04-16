# Wallet by BudgetBakers CSV to eXpend JSON Converter

## Overview

This script converts CSV exports from **Budgetbakers Wallet** app into a JSON backup file compatible with the **eXpend** expense tracker app. It's designed specifically for migration purposes, allowing you to transfer your transaction history from Budgetbakers Wallet to eXpend.

## Features

- ✅ Converts CSV transactions (expenses, incomes, and transfers) to eXpend JSON format
- ✅ Automatically creates categories based on your transaction data
- ✅ Preserves static categories from existing eXpend backup
- ✅ Handles transfer transactions (requires two consecutive CSV rows)
- ✅ Converts dates from UTC+3 to UTC format
- ✅ Interactive wallet balance update prompt
- ✅ Case-insensitive wallet name matching
- ✅ Skips transactions with missing wallet mappings (with warnings)
- ✅ Generates unique UUIDs for all transactions

## Prerequisites

- PC with Python 3.6 or higher
- Having **the same wallets/accounts list** on both Wallet Budgetbakers and eXpend app
- CSV format backup file from the **Wallet by Budgetbakers** app (tested with the version 9.2.6)
  - Click on the sandwich menu on the top left corner
  - Scroll until you see **Others** and click on it
  - Click on **Exports**
  - Set your export date range and click on **CSV** button
  - Choose the export directory
- JSON format backup from **eXpend** app (tested with the version 1.8.21)
  - Click on the avatar icon on the bottom right corner
  - Scroll until you see **Backup & Restore**
  - Click on **Backup Data**, confirm
  - Choose the export directory

## Usage

### Basic Usage

```bash
python expend-backup-generator.py
```

The script will prompt you for:

1. **CSV file path** - Path to your Budgetbakers Wallet export
2. **JSON template path** - Path to an existing eXpend backup file
3. **Wallet balance update** - Whether to update wallet balances (y/n)

### Example Session

```bash
$ python expend-backup-generator.py

Enter the path to your CSV file: budgetbakers_export.csv
Enter the path to the JSON template file: expend-backup-20260416_120701.json

============================================================
Do you want to update wallet balances? (y/n, default: y): y

============================================================
UPDATE WALLET BALANCES
============================================================
Please enter the current balance for each wallet.
Press Enter to keep the existing balance.

Wallet: Cash
  Current balance in JSON: 1,750 MGA
  Enter new balance (or press Enter to keep): 2500
  ✓ Updated to: 2,500 MGA

Wallet: BOA Current
  Current balance in JSON: 123,498 MGA
  Enter new balance (or press Enter to keep): 
  → Keeping existing balance: 123,498 MGA

... (more wallets) ...

Processing CSV file budgetbakers_export.csv...
Read 150 rows from CSV
Created 25 new categories

✓ Success! Generated import-from-budgetbakers-20260416-143022.json
  - Total categories: 35
  - New categories added: 25
  - Total transactions: 148
  - Total wallets: 6

  - Final wallet balances:
      • Cash: 2,500 MGA
      • BOA Current: 123,498 MGA
      • BOA Saving: 0 MGA
      • MVola: 1,502 MGA
      • Airtel Money: 0 MGA
      • BNI: 0 MGA

  - Date conversion: UTC+3 → UTC applied to all 148 transactions
```

## Output

The script generates a file named: `import-from-budgetbakers-YYYY-MM-DD-HHMMSS.json`

This file can be directly imported into the eXpend app.

## Important Notes

### ⚠️ After Import: Update Category Icons

The script sets all new categories with a default icon of `"coin"`. After importing the JSON file into eXpend, you **MUST manually update the icons** for each newly created category:

1. Open eXpend app
2. Go to Settings → Categories
3. Find all categories with the default "coin" icon
4. Edit each category and select an appropriate icon

Categories with `order: 0` (transfers, adjustments, debts, etc.) already have correct icons and should not be modified.

### Wallet Name Matching

- Wallet names are matched **case-insensitively** (e.g., "cash" matches "Cash")
- If a wallet in your CSV doesn't match any wallet in the JSON template, the transaction will be **skipped** with a warning
- Check the console output for any unmapped wallet warnings

### Date Conversion

- CSV dates are assumed to be in **UTC+3** timezone
- The script automatically converts them to **UTC** format (with `Z` suffix)
- Example: `2026-04-16 09:03:54` (UTC+3) → `2026-04-16T06:03:54.000Z` (UTC)

### Transaction Amounts

- The script uses absolute values for all amounts
- Expenses and incomes are handled correctly regardless of sign in CSV
- Transfer amounts are also converted to positive values

## Troubleshooting

### Issue: "WARNING: Skipping transaction - missing wallet mapping"

**Cause**: Wallet name in CSV doesn't match any wallet in the JSON template

**Solution**: 
- Check the wallet names in your CSV file
- Either update CSV to use exact wallet names from the template, or
- Add the missing wallets to your JSON template file

### Issue: Empty `srcWallet` in output JSON

**Cause**: Transactions were skipped due to missing wallet mappings

**Solution**: Fix wallet name mismatches as described above and re-run the script

### Issue: "WARNING: Missing category mapping"

**Cause**: Category couldn't be mapped (rare, usually due to TRANSFER handling)

**Solution**: Check your CSV for any malformed category names

### Issue: Transfer transactions not showing correctly

**Cause**: Transfer rows not consecutive or missing one of the rows

**Solution**: Ensure transfers always have exactly two consecutive rows in the CSV

## Limitations

1. **One-way migration only** - This script is designed for migrating FROM Budgetbakers Wallet TO eXpend, not the other way
2. **No subcategory support** - Subcategories from Budgetbakers Wallet are not preserved
3. **Basic icon assignment** - All new categories get the "coin" icon (must be updated manually in eXpend)
4. **No debt tracking migration** - Debt-related transactions are not migrated
5. **No recurring transactions** - Recurring transaction settings are not migrated

## Backups details

1. **CSV file** - Exported from Budgetbakers Wallet app with the following format:
   - Delimiter: semicolon (`;`)
   - Encoding: UTF-8
   - Required columns: `date`, `type`, `category`, `account`, `amount`, `note`

2. **JSON template file** - An existing eXpend backup file (e.g., `expend-backup-*.json`) that contains:
   - Static categories (with `order: 0`)
   - Wallet definitions
   - Templates
   - Profile settings

## CSV Format Specification

Your CSV file must have the following columns (order doesn't matter, but names must match exactly):

| Column | Description | Example |
|--------|-------------|---------|
| `date` | Transaction date and time (UTC+3) | `2026-04-16 09:03:54` |
| `type` | Transaction type | `Expenses` or `Income` |
| `category` | Category name | `Food`, `Salary`, `Shopping` |
| `account` | Wallet/account name | `Cash`, `BOA Current` |
| `amount` | Transaction amount (positive for income, positive for expenses) | `125000` |
| `note` | Transaction description/notes | `Monthly salary` |

### Special Handling for Transfer Transactions

**IMPORTANT**: Transfer transactions must appear as **two consecutive rows** in the CSV:

```
Row 1: date,TRANSFER,Source Account,amount,note
Row 2: date,TRANSFER,Destination Account,amount,note
```

Example:
```csv
date;type;category;account;amount;note
2026-04-16 09:05:55;TRANSFER;TRANSFER;BOA Current;1502;Test transfer
2026-04-16 09:05:55;TRANSFER;TRANSFER;MVola;1502;Test transfer
```

## File Structure

The generated JSON follows the eXpend app structure:

```json
{
  "categories": [...],        // Combined static + new categories
  "subcategories": [],        // Empty (not supported)
  "wallets": [...],           // From template with updated balances
  "budgets": [],              // Empty array
  "templates": [...],         // From template
  "transactions": [...],      // Converted from CSV
  "recurringTransactions": [], // Empty array
  "debts": [],                // Empty array
  "profile": {...}            // From template
}
```

## Support

For issues or questions:
- Check the console output for detailed warnings and errors
- Verify CSV format matches the specification
- Ensure you're using the latest version of the script

## Version History

- **v1.0** - Initial release
  - Basic CSV to JSON conversion
  - UTC+3 to UTC date conversion
  - Interactive wallet balance updates
  - Transfer transaction support

## License

This script is provided for personal use only. Use at your own risk. Always backup your data before performing migrations.

---

**Happy budgeting with eXpend!** 🚀

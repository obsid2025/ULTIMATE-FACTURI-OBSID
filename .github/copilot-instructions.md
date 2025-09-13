# Ultimate FACTURI - AI Coding Agent Guide

## Project Overview
Ultimate FACTURI is a Romanian business automation tool that processes courier delivery receipts, payment gateway transactions, and e-commerce platform data to generate consolidated financial reports. The core application (`grupare facturi.py`) is a tkinter GUI that integrates with multiple data sources to match invoices with payments and calculate commissions.

## Architecture & Data Flow

### Core Components
- **Main GUI Application**: `grupare facturi.py` - Single 1900+ line file containing the entire tkinter application
- **Data Sources Integration**: Processes Excel/CSV files from GLS, Sameday, Netopia, eMag, Gomag, and Oblio
- **Configuration Persistence**: `config.txt` stores file paths between sessions
- **Analysis & Debug Scripts**: `analiza_dp.py`, `debug_*.py`, `test_*.py` for data validation

### Data Processing Pipeline
1. **Courier Data** (GLS/Sameday): AWB tracking numbers → Invoice matching via Gomag XLSX
2. **Payment Gateways** (Netopia): CSV batch processing with XML bank statement reconciliation
3. **E-commerce Platform** (eMag): Complex multi-file DP (payment), DC (commission), DED, DCCO, DCCD processing with TVA calculations
4. **Invoice Fallback**: Oblio XLS integration when Gomag mapping fails
5. **Final Export**: Consolidated Excel report with OP (payment order) matching

## Critical Business Logic

### eMag Processing Complexity
- **Formula**: `DP total - (DC + DCCD + DCCO + DED) + DV + DCS = Final Amount`
- **TVA Handling**: 19% for July 2025, 21% from August 2025 onwards
- **File Naming Convention**: `nortia_[type]_[MMYYYY]_[id].xlsx` (e.g., `nortia_dp_072025_1754104695_v1.xlsx`)
- **Duplicate Detection**: Order IDs can appear multiple times (refunds/modifications)
- **Canceled Orders**: Must be filtered out using easySales Status column

### Data Matching Patterns
- **AWB Normalization**: Remove spaces, strip leading zeros for GLS/Sameday matching
- **Numeric Tolerance**: ±0.01 for currency comparisons, ±1.0 for OP matching
- **XML Parsing**: Bank statements use `<movement><ref>` for OP numbers, `<credit>` for amounts
- **BatchId Extraction**: Netopia uses regex `r'batchId\.(\d+)'` for transaction grouping

## Development Workflows

### Testing Strategy
```bash
# Run main application
python "grupare facturi.py"

# Test eMag formula components
python test_emag_simple.py

# Analyze specific DP files
python analiza_dp.py

# Debug commission calculations
python debug_comisioane_folder_corect.py
```

### Virtual Environment
- Uses `.venv` directory with Python 3.10+
- Deployment via `Ultimate_FACTURI.bat` or `Ultimate_FACTURI_direct.vbs`
- Silent execution option: `Ultimate_FACTURI_silent.vbs`

## Project-Specific Conventions

### File Handling Patterns
- **Excel Engines**: Use `xlrd` for `.xls` files (Oblio), `openpyxl` for modern Excel files
- **Header Locations**: Oblio data starts at row 6 (header row 5), Sameday uses multiple sheets
- **Path Storage**: All file paths saved to `config.txt` for persistence between sessions
- **Error Accumulation**: `self.erori` list collects all validation errors for batch reporting

### UI Threading Model
- Main processing runs in separate thread (`export_threaded()`)
- Progress updates via `self.progress_var` and `self.progress_text`
- Tab-based error reporting in dedicated "Erori" tab

### Romanian Business Context
- Currency: RON (Romanian Lei)
- AWB: "Aviz de Însoțire a Mărfii" (delivery receipt numbers)
- OP: "Ordin de Plată" (payment order from bank statements)
- Invoice matching relies on Romanian e-commerce platform integrations

## Key Files to Understand
- `grupare facturi.py`: Complete application logic (start here)
- `test_emag_simple.py`: eMag processing validation pattern
- `config.txt`: Runtime configuration example
- `8 August/`: Sample data structure showing expected folder organization

## Common Patterns
- **Column Normalization**: `df.columns.str.strip().str.lower()` for consistent matching
- **Numeric Conversion**: `pd.to_numeric(errors='coerce')` with NaN handling
- **File Type Detection**: Extension-based processing (`.xlsx`, `.csv`, `.xls`, `.xml`)
- **Progress Reporting**: Always update `progress_var` and `progress_text` for long operations
- **Error Handling**: Append to `self.erori` list, display in GUI tab, continue processing

When making changes, prioritize data accuracy over performance - financial reconciliation correctness is critical.
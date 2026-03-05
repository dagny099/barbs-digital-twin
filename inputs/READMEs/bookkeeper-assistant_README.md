# Poolula LLC Transaction Classification Reviewer

A web application for reviewing and refining LLM-generated transaction classifications for QuickBooks Online import.

## 📚 Documentation

- **[USER_GUIDE.md](USER_GUIDE.md)** - Complete step-by-step guide for using the application
- **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - Quick reference for daily use
- **[README.md](README.md)** - Technical documentation and setup (this file)

## 🚀 Quick Start

**New User?** → Read the [USER_GUIDE.md](USER_GUIDE.md) first  
**Need a quick reminder?** → Check [QUICK_REFERENCE.md](QUICK_REFERENCE.md)  
**Setting up or troubleshooting?** → Continue reading below

## Overview

This application helps you:
- ✅ Review LLM transaction classifications 
- ✅ Manually correct and approve classifications
- ✅ Create auto-classification rules
- ✅ Export clean data for QBO import
- ✅ Track review progress and maintain audit trail

## Data Reconciliation Results

**✅ Data Integrity Verified**
- 1,880 total transactions processed from 5 source CSV files
- Perfect match: All transactions accounted for in LLM output
- 746 duplicate transactions identified (RBFCU checking/savings mirror transactions)

**Classification Summary:**
- 70.5% Non-LLC (Personal) transactions
- 22.7% "Possible LLC Expense (Needs Review)" 
- 3.7% "Uncategorized – Needs Review"
- 3.1% Classified business expenses across 8 categories

## Quick Start

### 1. Install Dependencies
```bash
npm run install-all
```

### 2. Configure Environment (Optional)
Copy `.env.example` to `.env` and customize paths if needed:
```bash
cp .env.example .env
```

### 3. Start the Application
```bash
npm run dev
```

This starts:
- Backend API: http://localhost:3001
- Frontend: http://localhost:3000

### 4. Initial Data Load
The backend automatically loads your classification data from:
`llc_transaction_classification_OUTPUT.csv` (in project root or configured DATA_PATH)

## Features

### 📊 Dashboard
- Overview of classification progress
- Breakdown by category and account
- Quick actions for common tasks

### 🔍 Transaction Review
- Sortable/filterable transaction grid
- Inline editing of classifications and notes
- Bulk operations (approve, reclassify)
- Color-coded status indicators
- Pagination for large datasets

### ⚙️ Rule Builder
- Create pattern-based classification rules
- Test rules against existing data
- Support for description, vendor, and amount matching
- Confidence scoring for rule quality

### 📤 QBO Export
- Generate QBO-ready CSV files
- Proper category mapping for rental property business
- Exclude personal transactions automatically
- Include Member Equity contributions

## Classification Categories

**Business Categories:**
- Utilities (Electric, Water, Gas, Internet)
- Repairs & Maintenance
- Supplies
- Insurance
- Property Taxes
- Legal & Professional Fees
- Bank Charges
- Capital Improvements
- Meals/Travel (business-related)
- Other Ordinary & Necessary Expenses

**Special Categories:**
- Equity Contribution (property purchase funding)
- Non-LLC (Personal) - excluded from QBO export

## Workflow Recommendations

**📖 For detailed workflows and step-by-step instructions, see [USER_GUIDE.md](USER_GUIDE.md)**

### Phase 1: Review High-Priority Items
1. Focus on "Needs Review" transactions (497 items)
2. Verify "Possible LLC Expense" items (427 items)  
3. Confirm Equity Contributions (7 items)

### Phase 2: Create Classification Rules
1. Identify common vendors/patterns
2. Create rules for automatic classification
3. Test rules against existing data
4. Apply rules to reduce manual review load

### Phase 3: QBO Preparation
1. Mark all reviewed transactions as "Reviewed"
2. Export business transactions to CSV
3. Import to QuickBooks Online
4. Set up Bank Rules in QBO based on created patterns

## Technical Details

### Backend (Node.js/Express)
- SQLite database for local storage
- CSV import/export capabilities
- RESTful API with comprehensive validation
- Rate limiting and security middleware
- Comprehensive error handling and logging
- Environment-based configuration

### Frontend (React/TypeScript)
- Material-UI for professional interface
- Real-time data synchronization
- Responsive design for all screen sizes
- Component-based architecture
- Comprehensive test coverage

### Security & Quality
- Input validation with Joi schemas
- SQL injection protection
- Rate limiting and security headers
- ESLint + Prettier code formatting
- Comprehensive test suite (Jest + React Testing Library)
- Environment variable configuration

### Data Storage
- Local SQLite database (no cloud dependencies)
- Original CSV files preserved unchanged
- All changes tracked with timestamps
- Audit trail for compliance

## File Structure

```
poolula-accounting/
├── backend/
│   ├── server.js           # Main API server
│   ├── transactions.db     # SQLite database (auto-created)
│   └── package.json
├── frontend/
│   ├── src/
│   │   ├── components/     # React components
│   │   └── App.tsx         # Main application
│   └── package.json
├── data/
│   └── reconcile.js        # Data validation script
├── docs/
│   └── screenshots/        # UI screenshots directory
├── USER_GUIDE.md           # Comprehensive user guide
├── QUICK_REFERENCE.md      # Quick reference guide
├── README.md               # Technical documentation
└── package.json            # Root package scripts
```

## Available Scripts

### Development
```bash
npm run dev          # Start both backend and frontend
npm run backend      # Start backend only
npm run frontend     # Start frontend only
```

### Testing
```bash
npm test             # Run all tests
npm run test:backend # Run backend tests only
npm run test:frontend # Run frontend tests only
```

### Code Quality
```bash
npm run lint         # Lint all code
npm run lint:fix     # Fix linting issues
npm run format       # Format code with Prettier
```

## API Endpoints

- `GET /api/dashboard` - Summary statistics (with validation)
- `GET /api/transactions` - Transaction list with filtering
- `PUT /api/transactions/:id` - Update single transaction (rate limited)
- `PUT /api/transactions/bulk` - Bulk update operations (rate limited)
- `GET /api/rules` - Classification rules
- `POST /api/rules` - Create new rule (rate limited)
- `POST /api/rules/test` - Test rule against data (validated)
- `GET /api/export/qbo` - Export QBO-ready CSV (rate limited)

## Security & Privacy

- ✅ Runs completely locally (no cloud/external dependencies)
- ✅ No data transmitted over internet
- ✅ SQLite database stored locally
- ✅ All financial data remains on your machine
- ✅ Input validation and SQL injection protection
- ✅ Rate limiting and security headers
- ✅ Comprehensive error handling and logging

## Troubleshooting

### Backend Issues
```bash
cd backend
npm install
node server.js
```

### Frontend Issues  
```bash
cd frontend
npm install
npm start
```

### Data Issues
```bash
node data/reconcile.js
```

### Testing Issues
```bash
npm test                    # Run all tests
npm run test:coverage      # Check test coverage
```

### Code Quality Issues  
```bash
npm run lint               # Check for linting errors
npm run format            # Fix formatting issues
```

## Support

For issues or questions:
1. Check the browser console for error messages
2. Run `npm test` to verify system functionality
3. Verify environment configuration in `.env`
4. Ensure Node.js version 16+ is installed
5. Check logs in the terminal for detailed error information

## Next Steps

After reviewing classifications:
1. **Export to QBO**: Use the export function to generate CSV
2. **Import to QuickBooks**: Use QBO's CSV import feature
3. **Set up Bank Rules**: Use learned patterns to create QBO rules
4. **Monitor Going Forward**: Apply lessons learned to future transactions

---

*Built for Poolula LLC bookkeeping workflow - Professional, secure, audit-ready.*
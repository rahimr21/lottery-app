# 🎫 Lottery Stock Tracker

A comprehensive Flask web application for tracking lottery ticket stock, managing daily sales reports, and calculating lottery deposit amounts.

## ✨ Features

- **📊 Stock Management**: Track lottery ticket stock numbers by holder and date
- **📈 Daily Reports**: Create comprehensive daily lottery reports with automated calculations
- **📋 Report Management**: View, edit, and manage saved daily reports
- **🖨️ Print Support**: Professional printable reports with proper formatting
- **💾 Data Persistence**: SQLite database for reliable data storage
- **🔧 Easy Management**: User-friendly interface for all operations

## 🚀 Quick Start

### Prerequisites

- Python 3.7 or higher
- pip (Python package installer)

### Installation

#### Option 1: Automated Setup (Recommended)

1. **Clone the repository**
   ```bash
   git clone https://github.com/rahimr21/lottery-app.git
   cd lottery-app
   ```

2. **Create and activate virtual environment**
   ```bash
   # On Windows
   python -m venv lottery-env
   lottery-env\Scripts\activate

   # On macOS/Linux
   python3 -m venv lottery-env
   source lottery-env/bin/activate
   ```

3. **Run the setup script**
   ```bash
   python setup.py
   ```

4. **Start the application**
   ```bash
   python app.py
   ```

#### Option 2: Manual Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/lottery-app.git
   cd lottery-app
   ```

2. **Create a virtual environment**
   ```bash
   # On Windows
   python -m venv lottery-env
   lottery-env\Scripts\activate

   # On macOS/Linux
   python3 -m venv lottery-env
   source lottery-env/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize the database**
   ```bash
   flask init-db
   ```

5. **Run the application**
   ```bash
   python app.py
   ```

6. **Open your browser**
   Navigate to `http://localhost:5000`

## 📖 Usage Guide

### 👥 User Access Levels

The application has two access levels:

**Employee Access (No Password Required):**
- 🏠 Enter Stock - Input daily lottery stock numbers
- 📊 Stock Reports - View and manage stock data

**Admin Access (Requires Passcode: `2222`):**
- 📈 Create Report - Generate daily lottery reports  
- 📋 Lottery Reports - View and manage saved reports

### 🏠 Home Page - Enter Stock
- Enter lottery ticket stock numbers for all holders (1-56)
- Automatic ticket value assignment based on holder numbers
- Date-specific data entry with validation

### 📊 Stock Reports
- View detailed stock reports by date
- Edit individual stock entries
- Delete specific entries or entire date records
- View totals and grand totals by ticket value

### 📈 Create Report (Admin Only)
- Generate daily lottery reports with automated calculations
- Input fields for new books opened ($1, $2, $5, $10, $20, $30, $50)
- Machine lottery sales, tickets cashed, and online cashed tracking
- Automatic calculation of deposit amounts

### 📋 Lottery Reports (Admin Only)
- View all saved daily reports
- Edit existing reports with real-time recalculation
- View full detailed reports with print functionality
- Delete reports as needed

### 🔐 Admin Access
- Click on admin-protected pages to see login prompt
- Enter passcode `2222` to gain admin access
- Admin status shown in navigation with logout option
- Session-based authentication (logout removes access)

## 🔧 Ticket Value Mapping

The application uses the following ticket value mapping by holder number:

| Holders | Ticket Value |
|---------|-------------|
| 1-4     | $30         |
| 5-8     | $50         |
| 9-13    | $20         |
| 14-31   | $10         |
| 32-41   | $5          |
| 42      | $2          |
| 43-48   | $1          |
| 49-56   | $2          |

## 📊 Report Calculations

Daily reports follow this calculation sequence:

1. **Total New Books Opened** = Sum of all book amounts ($1 + $2 + $5 + $10 + $20 + $30 + $50)
2. **Net Total Scratch** = (Yesterday Closing + Total New Books Opened) - Today Closing
3. **Total Lottery Sale** = Net Total Scratch + Machine Lottery Sold
4. **Current Date Lottery Deposit Amount** = Total Lottery Sale - (Tickets Cashed + Online Cashed)

## 🗂️ Project Structure

```
lottery-app/
├── app.py                      # Main Flask application
├── requirements.txt            # Python dependencies
├── setup.py                   # Automated setup script
├── .gitignore                 # Git ignore rules
├── README.md                  # This file
├── templates/                 # HTML templates
│   ├── base.html             # Base template with navigation
│   ├── enter_stock.html      # Stock entry form
│   ├── reports.html          # Stock reports view
│   ├── create_report.html    # Daily report creation
│   ├── lottery_reports.html  # Saved reports management
│   └── view_lottery_report.html # Full report view
└── instance/                  # Flask instance folder (auto-created)
    └── stock_data.db         # SQLite database (created after init)
```

## 🛠️ Development

### Database Schema

**lottery_stock table:**
- `id`: Primary key
- `date`: Stock date (YYYY-MM-DD)
- `holder_number`: Holder number (1-56)
- `stock_number`: Number of tickets in stock
- `ticket_value`: Value per ticket
- `created_at`: Timestamp

**daily_reports table:**
- `id`: Primary key
- `date`: Report date (YYYY-MM-DD)
- `yesterday_closing`, `today_closing`: Stock totals
- `books_1` through `books_50`: New book amounts
- `machine_sold`, `tickets_cashed`, `online_cashed`: Transaction amounts
- Calculated fields: `total_new_books`, `net_total_scratch`, `total_lottery_sale`, `lottery_deposit_amount`
- `created_at`: Timestamp

### Flask CLI Commands

- `flask init-db`: Initialize database with required tables and indexes

### Environment Variables

- `SECRET_KEY`: Flask secret key (defaults to development key)
- `ADMIN_PASSCODE`: Admin access passcode (defaults to "2222")

## 🔒 Security Notes

- Change the default `SECRET_KEY` in production
- Change the default `ADMIN_PASSCODE` from "2222" to a secure passcode
- Use environment variables for sensitive configuration
- Consider using a production WSGI server (e.g., Gunicorn) instead of the development server

## 📝 License

This project is open source and available under the [MIT License](LICENSE).

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📞 Support

If you encounter any issues or have questions, please open an issue on GitHub.

## 🔄 Version History

- **v1.0.0** - Initial release with full lottery tracking functionality
- **v1.1.0** - Added delete functionality and report viewing
- **v1.2.0** - Improved UI and added Flask CLI commands
- **v1.3.0** - Added admin authentication system for role-based access

---

Made with ❤️ for lottery stock management
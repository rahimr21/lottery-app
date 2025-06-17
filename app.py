from flask import Flask, render_template, request, redirect, flash, url_for, session
import os
import sqlite3
from datetime import datetime
import logging
import click

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-key-please-change-in-production')

# Admin passcode (in production, this should be in environment variables)
ADMIN_PASSCODE = os.environ.get('ADMIN_PASSCODE', '2222')

def check_admin_access():
    """Check if user has admin access"""
    return session.get('admin_authenticated', False)

def require_admin():
    """Decorator to require admin access"""
    from functools import wraps
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not check_admin_access():
                return redirect(url_for('admin_login', next=request.url))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    """Admin login page"""
    if request.method == 'POST':
        passcode = request.form.get('passcode', '')
        next_url = request.form.get('next', url_for('create_report'))
        
        if passcode == ADMIN_PASSCODE:
            session['admin_authenticated'] = True
            flash('Admin access granted!', 'success')
            return redirect(next_url)
        else:
            flash('Invalid passcode. Please try again.', 'error')
    
    next_url = request.args.get('next', url_for('create_report'))
    return render_template('admin_login.html', next=next_url)

@app.route('/admin-logout')
def admin_logout():
    """Admin logout"""
    session.pop('admin_authenticated', None)
    flash('Admin access removed.', 'info')
    return redirect(url_for('enter_stock'))

def get_db_connection():
    # Ensure instance folder exists
    os.makedirs(app.instance_path, exist_ok=True)
    # Use instance folder for database
    db_path = os.path.join(app.instance_path, 'stock_data.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def get_daily_grand_total(date):
    """Calculate the grand total for a given date including both holder tickets and extra tickets."""
    conn = get_db_connection()
    try:
        # Calculate total from holder tickets
        holder_total = conn.execute('''
            SELECT SUM(stock_number * ticket_value) as total
            FROM lottery_stock 
            WHERE date = ?
        ''', (date,)).fetchone()['total'] or 0
        
        # Calculate total from extra tickets
        extra_total = conn.execute('''
            SELECT SUM(stock_number * ticket_price) as total
            FROM extra_tickets 
            WHERE date = ?
        ''', (date,)).fetchone()['total'] or 0
        
        return holder_total + extra_total
    finally:
        conn.close()

def init_database():
    """Initialize the database with required tables and indexes."""
    # Ensure instance folder exists
    os.makedirs(app.instance_path, exist_ok=True)
    # Use instance folder for database
    db_path = os.path.join(app.instance_path, 'stock_data.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # Create a table for lottery stock entries
    c.execute('''
        CREATE TABLE IF NOT EXISTS lottery_stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            holder_number INTEGER NOT NULL CHECK(holder_number BETWEEN 1 AND 56),
            stock_number INTEGER NOT NULL CHECK(stock_number >= 0),
            ticket_value INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(date, holder_number)
        )
    ''')
    
    # Create a table for extra tickets (not in holders)
    c.execute('''
        CREATE TABLE IF NOT EXISTS extra_tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            ticket_price INTEGER NOT NULL CHECK(ticket_price > 0),
            stock_number INTEGER NOT NULL CHECK(stock_number >= 0),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create the daily_reports table for the Create Report functionality
    c.execute('''
        CREATE TABLE IF NOT EXISTS daily_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT UNIQUE NOT NULL,
            yesterday_closing REAL NOT NULL,
            today_closing REAL NOT NULL,
            books_1 REAL NOT NULL DEFAULT 0,
            books_2 REAL NOT NULL DEFAULT 0,
            books_5 REAL NOT NULL DEFAULT 0,
            books_10 REAL NOT NULL DEFAULT 0,
            books_20 REAL NOT NULL DEFAULT 0,
            books_30 REAL NOT NULL DEFAULT 0,
            books_50 REAL NOT NULL DEFAULT 0,
            machine_sold REAL NOT NULL DEFAULT 0,
            tickets_cashed REAL NOT NULL DEFAULT 0,
            online_cashed REAL NOT NULL DEFAULT 0,
            total_new_books REAL NOT NULL DEFAULT 0,
            net_total_scratch REAL NOT NULL DEFAULT 0,
            total_lottery_sale REAL NOT NULL DEFAULT 0,
            lottery_deposit_amount REAL NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create indexes for faster date-based queries
    c.execute('''
        CREATE INDEX IF NOT EXISTS idx_lottery_stock_date 
        ON lottery_stock(date)
    ''')
    
    c.execute('''
        CREATE INDEX IF NOT EXISTS idx_daily_reports_date 
        ON daily_reports(date)
    ''')
    
    conn.commit()
    conn.close()
    click.echo('Database initialized and tables created successfully.')

@app.cli.command('init-db')
def init_db_command():
    """Clear existing data and create new tables."""
    init_database()

# Real-world ticket value mapping by holder number
holder_ticket_values = {}
# Holders 1-4: $30
for i in range(1, 5): holder_ticket_values[i] = 30
# Holders 5-8: $50
for i in range(5, 9): holder_ticket_values[i] = 50
# Holders 9-14: $20
for i in range(9, 15): holder_ticket_values[i] = 20
# Holders 15-42: $10
for i in range(15, 43): holder_ticket_values[i] = 10
# Holders 33-41: $5
for i in range(33, 42): holder_ticket_values[i] = 5
# Holder 42: $10
holder_ticket_values[42] = 10
# Holders 43-46: $1
for i in range(43, 47): holder_ticket_values[i] = 1
# Holders 47-55: $2
for i in range(47, 56): holder_ticket_values[i] = 2
# Holder 56: $5
holder_ticket_values[56] = 5

@app.route('/', methods=['GET', 'POST'])
def enter_stock():
    REQUIRE_ALL_FIELDS = True
    holder_sequence = (
        list(range(1, 15)) +         # 1–14
        list(range(28, 14, -1)) +    # 28–15
        list(range(29, 43)) +        # 29–42
        list(range(56, 42, -1))      # 56–43
    )

    error_message = None
    previous_values = {}
    current_date = datetime.now().strftime('%Y-%m-%d')

    if request.method == 'POST':
        try:
            date = request.form['date']
            if not date:
                raise ValueError("Date is required")
            
            # Validate date format
            try:
                datetime.strptime(date, '%Y-%m-%d')
            except ValueError:
                raise ValueError("Invalid date format. Use YYYY-MM-DD")
            
            entries = []
            missing = []
            conn = get_db_connection()
            
            try:
                for i in holder_sequence:
                    field_name = f'holder_{i}'
                    stock_number = request.form.get(field_name)
                    previous_values[i] = stock_number

                    if not stock_number and REQUIRE_ALL_FIELDS:
                        missing.append(i)
                        continue

                    if stock_number:
                        try:
                            stock_number = int(stock_number)
                            if stock_number < 0:
                                raise ValueError(f"Stock number for holder {i} cannot be negative")
                        except ValueError:
                            raise ValueError(f"Invalid stock number for holder {i}")
                        
                        ticket_value = holder_ticket_values.get(i, 0)
                        entries.append((date, i, stock_number, ticket_value))

                # Handle extra tickets
                extra_ticket_entries = []
                extra_index = 1
                while True:
                    price_field = f'extra_price_{extra_index}'
                    stock_field = f'extra_stock_{extra_index}'
                    
                    price = request.form.get(price_field)
                    stock = request.form.get(stock_field)
                    
                    if not price and not stock:
                        break
                    
                    if price and stock:
                        try:
                            price = int(price)
                            stock = int(stock)
                            if price <= 0:
                                raise ValueError(f"Extra ticket price must be positive")
                            if stock < 0:
                                raise ValueError(f"Extra ticket stock number cannot be negative")
                            extra_ticket_entries.append((date, price, stock))
                        except ValueError as e:
                            raise ValueError(f"Invalid extra ticket entry {extra_index}: {str(e)}")
                    elif price or stock:
                        raise ValueError(f"Both price and stock number must be provided for extra ticket {extra_index}")
                    
                    extra_index += 1

                if missing:
                    error_message = f"Please fill in all holders. Missing: {missing}"
                else:
                    # Insert holder entries
                    conn.executemany('''
                        INSERT INTO lottery_stock (date, holder_number, stock_number, ticket_value)
                        VALUES (?, ?, ?, ?)
                    ''', entries)
                    
                    # Insert extra ticket entries
                    if extra_ticket_entries:
                        conn.executemany('''
                            INSERT INTO extra_tickets (date, ticket_price, stock_number)
                            VALUES (?, ?, ?)
                        ''', extra_ticket_entries)
                    
                    conn.commit()
                    flash('Stock numbers successfully recorded!', 'success')
                    return redirect(url_for('enter_stock'))
            
            finally:
                conn.close()
                
        except ValueError as e:
            error_message = str(e)
        except sqlite3.Error as e:
            logger.error(f"Database error: {str(e)}")
            error_message = "Database error occurred. Please try again."
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            error_message = "An unexpected error occurred. Please try again."

    holder_data = [
        {
            "number": i,
            "value": holder_ticket_values.get(i, 0),
            "entered": previous_values.get(i, "")
        }
        for i in holder_sequence
    ]

    return render_template(
        'enter_stock.html',
        holder_order=holder_data,
        error=error_message,
        current_date=current_date
    )

@app.route('/reports', methods=['GET', 'POST'])
def reports():
    conn = get_db_connection()
    try:
        if request.method == 'POST':
            action = request.form.get('action', 'update')
            
            if action == 'update':
                # Handle data updates
                date = request.form['date']
                holder_number = int(request.form['holder_number'])
                new_stock = int(request.form['new_stock'])
                
                # Update the stock number
                conn.execute('''
                    UPDATE lottery_stock 
                    SET stock_number = ? 
                    WHERE date = ? AND holder_number = ?
                ''', (new_stock, date, holder_number))
                conn.commit()
                flash('Stock number updated successfully!', 'success')
                return redirect(url_for('reports', date=date))
            
            elif action == 'delete_entry':
                # Delete individual stock entry
                date = request.form['date']
                holder_number = int(request.form['holder_number'])
                
                conn.execute('''
                    DELETE FROM lottery_stock 
                    WHERE date = ? AND holder_number = ?
                ''', (date, holder_number))
                conn.commit()
                flash('Stock entry deleted successfully!', 'success')
                return redirect(url_for('reports', date=date))
            
            elif action == 'delete_all_date':
                # Delete all stock entries for a specific date
                date = request.form['date']
                
                # Check how many entries will be deleted
                count = conn.execute('''
                    SELECT COUNT(*) as count 
                    FROM lottery_stock 
                    WHERE date = ?
                ''', (date,)).fetchone()['count']
                
                if count > 0:
                    conn.execute('''
                        DELETE FROM lottery_stock 
                        WHERE date = ?
                    ''', (date,))
                    conn.commit()
                    flash(f'All {count} stock entries for {date} deleted successfully!', 'success')
                else:
                    flash('No stock entries found for this date.', 'error')
                
                return redirect(url_for('reports'))

        # Get the selected date from query parameters or use today's date
        selected_date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
        
        # Get all unique dates for the date selector
        dates = conn.execute('''
            SELECT DISTINCT date 
            FROM lottery_stock 
            ORDER BY date DESC
        ''').fetchall()
        
        # Get all stock entries for the selected date
        entries = conn.execute('''
            SELECT * 
            FROM lottery_stock 
            WHERE date = ? 
            ORDER BY holder_number
        ''', (selected_date,)).fetchall()
        
        # Calculate totals by ticket value from holders
        totals = conn.execute('''
            SELECT 
                ticket_value,
                SUM(stock_number) as total_tickets,
                SUM(stock_number * ticket_value) as total_value
            FROM lottery_stock 
            WHERE date = ? 
            GROUP BY ticket_value
            ORDER BY ticket_value DESC
        ''', (selected_date,)).fetchall()
        
        # Get extra tickets for the selected date
        extra_tickets = conn.execute('''
            SELECT * 
            FROM extra_tickets 
            WHERE date = ? 
            ORDER BY ticket_price DESC, id
        ''', (selected_date,)).fetchall()
        
        # Calculate totals by ticket price from extra tickets
        extra_totals = conn.execute('''
            SELECT 
                ticket_price as ticket_value,
                SUM(stock_number) as total_tickets,
                SUM(stock_number * ticket_price) as total_value
            FROM extra_tickets 
            WHERE date = ? 
            GROUP BY ticket_price
            ORDER BY ticket_price DESC
        ''', (selected_date,)).fetchall()
        
        # Calculate grand total (holders + extra tickets)
        holder_total = conn.execute('''
            SELECT SUM(stock_number * ticket_value) as total
            FROM lottery_stock 
            WHERE date = ?
        ''', (selected_date,)).fetchone()['total'] or 0
        
        extra_total = conn.execute('''
            SELECT SUM(stock_number * ticket_price) as total
            FROM extra_tickets 
            WHERE date = ?
        ''', (selected_date,)).fetchone()['total'] or 0
        
        grand_total = holder_total + extra_total

        return render_template(
            'reports.html',
            dates=dates,
            selected_date=selected_date,
            entries=entries,
            totals=totals,
            extra_tickets=extra_tickets,
            extra_totals=extra_totals,
            grand_total=grand_total
        )
    except Exception as e:
        logger.error(f"Error in reports: {str(e)}")
        flash('An error occurred while processing the report.', 'error')
        return redirect(url_for('reports'))
    finally:
        conn.close()

@app.route('/create-report', methods=['GET', 'POST'])
@require_admin()
def create_report():
    from datetime import timedelta
    conn = get_db_connection()
    error_message = None
    
    try:
        if request.method == 'POST':
            # Get form data
            selected_date = request.form['date']
            
            # Check if override values are provided
            override_today = request.form.get('override_today_closing')
            override_yesterday = request.form.get('override_yesterday_closing')
            
            # Get lottery totals including both holder tickets and extra tickets
            if override_today and override_today.strip():
                today_closing = float(override_today)
            else:
                today_closing = get_daily_grand_total(selected_date)
            
            # Calculate yesterday's date
            selected_dt = datetime.strptime(selected_date, '%Y-%m-%d')
            yesterday = (selected_dt - timedelta(days=1)).strftime('%Y-%m-%d')
            
            if override_yesterday and override_yesterday.strip():
                yesterday_closing = float(override_yesterday)
            else:
                yesterday_closing = get_daily_grand_total(yesterday)
            
            # Check if we have data for both dates
            # Check if there's any lottery data for today (either holders or extra tickets)
            today_has_data = conn.execute('''
                SELECT COUNT(*) as count FROM (
                    SELECT 1 FROM lottery_stock WHERE date = ?
                    UNION
                    SELECT 1 FROM extra_tickets WHERE date = ?
                )
            ''', (selected_date, selected_date)).fetchone()['count'] > 0
            
            # Check if there's any lottery data for yesterday
            yesterday_has_data = conn.execute('''
                SELECT COUNT(*) as count FROM (
                    SELECT 1 FROM lottery_stock WHERE date = ?
                    UNION
                    SELECT 1 FROM extra_tickets WHERE date = ?
                )
            ''', (yesterday, yesterday)).fetchone()['count'] > 0
            
            if not today_has_data:
                error_message = f'No lottery stock data found for today ({selected_date}). Please enter stock data first.'
            elif not yesterday_has_data:
                error_message = f'No lottery stock data found for yesterday ({yesterday}). Cannot generate report.'
            else:
                # Get user input values
                try:
                    books_1 = float(request.form.get('books_1', 0) or 0)
                    books_2 = float(request.form.get('books_2', 0) or 0)
                    books_5 = float(request.form.get('books_5', 0) or 0)
                    books_10 = float(request.form.get('books_10', 0) or 0)
                    books_20 = float(request.form.get('books_20', 0) or 0)
                    books_30 = float(request.form.get('books_30', 0) or 0)
                    books_50 = float(request.form.get('books_50', 0) or 0)
                    machine_sold = float(request.form.get('machine_sold', 0) or 0)
                    tickets_cashed = float(request.form.get('tickets_cashed', 0) or 0)
                    online_cashed = float(request.form.get('online_cashed', 0) or 0)
                    
                    # Perform calculations in the exact order specified
                    total_new_books = books_1 + books_2 + books_5 + books_10 + books_20 + books_30 + books_50
                    net_total_scratch = (yesterday_closing + total_new_books) - today_closing
                    total_lottery_sale = net_total_scratch + machine_sold
                    lottery_deposit_amount = total_lottery_sale - (tickets_cashed + online_cashed)
                    
                    # Save to database (replace if exists for same date)
                    conn.execute('''
                        INSERT OR REPLACE INTO daily_reports (
                            date, yesterday_closing, today_closing,
                            books_1, books_2, books_5, books_10, books_20, books_30, books_50,
                            machine_sold, tickets_cashed, online_cashed,
                            total_new_books, net_total_scratch, total_lottery_sale, lottery_deposit_amount
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (selected_date, yesterday_closing, today_closing,
                          books_1, books_2, books_5, books_10, books_20, books_30, books_50,
                          machine_sold, tickets_cashed, online_cashed,
                          total_new_books, net_total_scratch, total_lottery_sale, lottery_deposit_amount))
                    conn.commit()
                    
                    # Prepare data for template
                    report_data = {
                        'date': selected_date,
                        'yesterday': yesterday,
                        'yesterday_closing': yesterday_closing,
                        'today_closing': today_closing,
                        'books_1': books_1,
                        'books_2': books_2,
                        'books_5': books_5,
                        'books_10': books_10,
                        'books_20': books_20,
                        'books_30': books_30,
                        'books_50': books_50,
                        'machine_sold': machine_sold,
                        'tickets_cashed': tickets_cashed,
                        'online_cashed': online_cashed,
                        'total_new_books': total_new_books,
                        'net_total_scratch': net_total_scratch,
                        'total_lottery_sale': total_lottery_sale,
                        'lottery_deposit_amount': lottery_deposit_amount
                    }
                    
                    flash('Report created successfully!', 'success')
                    return render_template('create_report.html', report_data=report_data, show_report=True)
                    
                except ValueError:
                    error_message = 'Please enter valid numbers for all fields.'
        
        # GET request or POST with errors - show form
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        # Get daily totals for current date to display
        totals = []
        extra_totals = []
        today_closing_value = 0
        yesterday_closing_value = 0
        
        # If a date is selected (GET parameter), get totals for that date
        selected_date = request.args.get('date', current_date)
        if selected_date:
            try:
                # Calculate totals by ticket value from holders
                totals = conn.execute('''
                    SELECT 
                        ticket_value,
                        SUM(stock_number) as total_tickets,
                        SUM(stock_number * ticket_value) as total_value
                    FROM lottery_stock 
                    WHERE date = ? 
                    GROUP BY ticket_value
                    ORDER BY ticket_value DESC
                ''', (selected_date,)).fetchall()
                
                # Calculate totals by ticket price from extra tickets
                extra_totals = conn.execute('''
                    SELECT 
                        ticket_price as ticket_value,
                        SUM(stock_number) as total_tickets,
                        SUM(stock_number * ticket_price) as total_value
                    FROM extra_tickets 
                    WHERE date = ? 
                    GROUP BY ticket_price
                    ORDER BY ticket_price DESC
                ''', (selected_date,)).fetchall()
                
                # Get closing values
                today_closing_value = get_daily_grand_total(selected_date)
                selected_dt = datetime.strptime(selected_date, '%Y-%m-%d')
                yesterday = (selected_dt - timedelta(days=1)).strftime('%Y-%m-%d')
                yesterday_closing_value = get_daily_grand_total(yesterday)
                
            except Exception as e:
                logger.error(f"Error getting daily totals: {str(e)}")
        
        return render_template('create_report.html', 
                             current_date=current_date, 
                             selected_date=selected_date,
                             show_report=False, 
                             error=error_message,
                             totals=totals,
                             extra_totals=extra_totals,
                             today_closing_value=today_closing_value,
                             yesterday_closing_value=yesterday_closing_value)
        
    except Exception as e:
        logger.error(f"Error in create_report: {str(e)}")
        error_message = 'An error occurred while processing the report.'
        current_date = datetime.now().strftime('%Y-%m-%d')
        return render_template('create_report.html', current_date=current_date, show_report=False, error=error_message)
    finally:
        conn.close()

@app.route('/lottery-reports', methods=['GET', 'POST'])
@require_admin()
def lottery_reports():
    conn = get_db_connection()
    try:
        if request.method == 'POST':
            # Handle editing existing reports
            action = request.form.get('action')
            
            if action == 'edit':
                report_id = request.form['report_id']
                
                # Get user input values
                try:
                    books_1 = float(request.form.get('books_1', 0) or 0)
                    books_2 = float(request.form.get('books_2', 0) or 0)
                    books_5 = float(request.form.get('books_5', 0) or 0)
                    books_10 = float(request.form.get('books_10', 0) or 0)
                    books_20 = float(request.form.get('books_20', 0) or 0)
                    books_30 = float(request.form.get('books_30', 0) or 0)
                    books_50 = float(request.form.get('books_50', 0) or 0)
                    machine_sold = float(request.form.get('machine_sold', 0) or 0)
                    tickets_cashed = float(request.form.get('tickets_cashed', 0) or 0)
                    online_cashed = float(request.form.get('online_cashed', 0) or 0)
                    
                    # Check for override values
                    override_today = request.form.get('override_today_closing')
                    override_yesterday = request.form.get('override_yesterday_closing')
                    
                    # Get existing report data for date calculations
                    existing_report = conn.execute('''
                        SELECT date, yesterday_closing, today_closing 
                        FROM daily_reports 
                        WHERE id = ?
                    ''', (report_id,)).fetchone()
                    
                    if existing_report:
                        # Use override values if provided, otherwise use existing values
                        if override_today and override_today.strip():
                            today_closing = float(override_today)
                        else:
                            today_closing = existing_report['today_closing']
                            
                        if override_yesterday and override_yesterday.strip():
                            yesterday_closing = float(override_yesterday)
                        else:
                            yesterday_closing = existing_report['yesterday_closing']
                        
                        # Recalculate all values
                        total_new_books = books_1 + books_2 + books_5 + books_10 + books_20 + books_30 + books_50
                        net_total_scratch = (yesterday_closing + total_new_books) - today_closing
                        total_lottery_sale = net_total_scratch + machine_sold
                        lottery_deposit_amount = total_lottery_sale - (tickets_cashed + online_cashed)
                        
                        # Update the report (including potentially overridden closing values)
                        conn.execute('''
                            UPDATE daily_reports SET
                                yesterday_closing = ?, today_closing = ?,
                                books_1 = ?, books_2 = ?, books_5 = ?, books_10 = ?, 
                                books_20 = ?, books_30 = ?, books_50 = ?,
                                machine_sold = ?, tickets_cashed = ?, online_cashed = ?,
                                total_new_books = ?, net_total_scratch = ?, 
                                total_lottery_sale = ?, lottery_deposit_amount = ?
                            WHERE id = ?
                        ''', (yesterday_closing, today_closing,
                              books_1, books_2, books_5, books_10, books_20, books_30, books_50,
                              machine_sold, tickets_cashed, online_cashed,
                              total_new_books, net_total_scratch, total_lottery_sale, 
                              lottery_deposit_amount, report_id))
                        conn.commit()
                        flash('Report updated successfully!', 'success')
                    else:
                        flash('Report not found.', 'error')
                        
                except ValueError:
                    flash('Please enter valid numbers for all fields.', 'error')
            
            elif action == 'delete':
                report_id = request.form['report_id']
                conn.execute('DELETE FROM daily_reports WHERE id = ?', (report_id,))
                conn.commit()
                flash('Report deleted successfully!', 'success')
        
        # Get all saved daily reports
        reports = conn.execute('''
            SELECT * FROM daily_reports 
            ORDER BY date DESC
        ''').fetchall()
        
        return render_template('lottery_reports.html', reports=reports)
        
    except Exception as e:
        logger.error(f"Error in lottery_reports: {str(e)}")
        flash('An error occurred while processing the request.', 'error')
        return render_template('lottery_reports.html', reports=[])
    finally:
        conn.close()

@app.route('/view-lottery-report/<int:report_id>')
@require_admin()
def view_lottery_report(report_id):
    conn = get_db_connection()
    try:
        # Get the specific report
        report = conn.execute('''
            SELECT * FROM daily_reports 
            WHERE id = ?
        ''', (report_id,)).fetchone()
        
        if not report:
            flash('Report not found.', 'error')
            return redirect(url_for('lottery_reports'))
        
        # Calculate yesterday's date for display
        from datetime import datetime, timedelta
        report_dt = datetime.strptime(report['date'], '%Y-%m-%d')
        yesterday = (report_dt - timedelta(days=1)).strftime('%Y-%m-%d')
        
        # Get daily totals data for the report date (same as stock reports page)
        selected_date = report['date']
        
        # Calculate totals by ticket value from holders
        totals = conn.execute('''
            SELECT 
                ticket_value,
                SUM(stock_number) as total_tickets,
                SUM(stock_number * ticket_value) as total_value
            FROM lottery_stock 
            WHERE date = ? 
            GROUP BY ticket_value
            ORDER BY ticket_value DESC
        ''', (selected_date,)).fetchall()
        
        # Calculate totals by ticket price from extra tickets
        extra_totals = conn.execute('''
            SELECT 
                ticket_price as ticket_value,
                SUM(stock_number) as total_tickets,
                SUM(stock_number * ticket_price) as total_value
            FROM extra_tickets 
            WHERE date = ? 
            GROUP BY ticket_price
            ORDER BY ticket_price DESC
        ''', (selected_date,)).fetchall()
        
        # Prepare data for template (same format as create_report)
        report_data = {
            'date': report['date'],
            'yesterday': yesterday,
            'yesterday_closing': report['yesterday_closing'],
            'today_closing': report['today_closing'],
            'books_1': report['books_1'],
            'books_2': report['books_2'],
            'books_5': report['books_5'],
            'books_10': report['books_10'],
            'books_20': report['books_20'],
            'books_30': report['books_30'],
            'books_50': report['books_50'],
            'machine_sold': report['machine_sold'],
            'tickets_cashed': report['tickets_cashed'],
            'online_cashed': report['online_cashed'],
            'total_new_books': report['total_new_books'],
            'net_total_scratch': report['net_total_scratch'],
            'total_lottery_sale': report['total_lottery_sale'],
            'lottery_deposit_amount': report['lottery_deposit_amount']
        }
        
        return render_template('view_lottery_report.html', 
                             report_data=report_data, 
                             totals=totals,
                             extra_totals=extra_totals,
                             show_report=True)
        
    except Exception as e:
        logger.error(f"Error viewing lottery report: {str(e)}")
        flash('An error occurred while loading the report.', 'error')
        return redirect(url_for('lottery_reports'))
    finally:
        conn.close()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

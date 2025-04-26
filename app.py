from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from supabase import create_client
import os
import datetime
from functools import wraps
from datetime import timedelta

app = Flask(__name__)
# Use a strong secret key in production
app.secret_key = os.urandom(24)
# Configure session
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
app.config['SESSION_COOKIE_SECURE'] = True  # For HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Initialize Supabase client
SUPABASE_URL = 'https://uxkfexylolypukjtbcbh.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InV4a2ZleHlsb2x5cHVranRiY2JoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDU1NzQ0OTcsImV4cCI6MjA2MTE1MDQ5N30.2242Zpsj4dW0M-kfzaFFuXlmZlKAh1UjRm7EKzojBYE'
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Add these constants at the top of the file with other configurations
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"  # In production, use a secure password and store it safely

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            # Return JSON if it's an API request
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'error': 'Unauthorized', 'redirect': url_for('index')}), 401
            # Otherwise redirect to login page
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin'):
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'error': 'Unauthorized', 'redirect': url_for('index')}), 401
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    if session.get('admin'):
        return redirect(url_for('admin_dashboard'))
    return render_template('index.html')

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    number = data.get('number')
    username = data.get('username')
    password = data.get('password')  # Password will be stored directly

    try:
        # Check if username already exists
        existing_user = supabase.table('users').select('*').eq('username', username).execute()
        if existing_user.data:
            return jsonify({'error': 'Username already exists'}), 400

        # Insert user data into Supabase with direct password
        response = supabase.table('users').insert({
            'phone_number': number,
            'username': username,
            'password': password,  # Storing password directly
            'balance': 0.00
        }).execute()

        return jsonify({'message': 'Registration successful'}), 200
    except Exception as e:
        print(f"Registration error: {str(e)}")
        return jsonify({'error': str(e)}), 400

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    try:
        response = supabase.table('users').select('*').eq('username', username).eq('password', password).execute()
        
        if not response.data:
            return jsonify({'error': 'Invalid credentials'}), 401
        
        user = response.data[0]
        
        # Set session data
        session.clear()
        session.permanent = True
        session['user_id'] = user['id']
        session['username'] = user['username']
        session.modified = True
        
        return jsonify({
            'message': 'Login successful',
            'user_id': user['id']
        }), 200

    except Exception as e:
        print(f"Login error: {str(e)}")
        return jsonify({'error': 'Login failed'}), 400

@app.route('/dashboard')
@login_required
def dashboard():
    # Verify user exists in database
    try:
        user_response = supabase.table('users').select('*').eq('id', session['user_id']).execute()
        if not user_response.data:
            session.clear()
            return redirect(url_for('index'))
        return render_template('dashboard.html')
    except Exception as e:
        print(f"Dashboard error: {str(e)}")
        session.clear()
        return redirect(url_for('index'))

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'Logout successful'}), 200

@app.route('/admin/login', methods=['POST'])
def admin_login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        session['admin'] = True
        return jsonify({'message': 'Login successful'}), 200
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/admin/user-bets')
@admin_required
def admin_user_bets():
    if not session.get('admin'):
        return jsonify({'error': 'Unauthorized'}), 401

    game_type = request.args.get('gameType', 'all')
    
    try:
        query = supabase.table('bets').select('*')
        if game_type != 'all':
            query = query.eq('game_type', game_type)
        
        response = query.execute()
        
        # Get usernames for each bet
        bets_with_usernames = []
        for bet in response.data:
            user_response = supabase.table('users').select('username').eq('id', bet['user_id']).execute()
            username = user_response.data[0]['username'] if user_response.data else 'Unknown'
            
            bets_with_usernames.append({
                'username': username,
                'gameType': bet['game_type'],
                'numbers': bet['numbers'],
                'amount': bet['amount'],
                'date': bet['created_at'],
                'status': bet['status']
            })
        
        return jsonify({'bets': bets_with_usernames})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/admin')
@admin_required
def admin_dashboard():
    return render_template('admin.html')

@app.route('/deposit')
@login_required
def deposit():
    return render_template('deposit.html')

@app.route('/submit_deposit', methods=['POST'])
@login_required
def submit_deposit():
    try:
        data = request.json
        utr_number = data.get('utrNumber')
        amount = float(data.get('amount'))
        
        if amount < 100:  # Minimum deposit amount
            return jsonify({'error': 'Minimum deposit amount is ₹100'}), 400

        if not utr_number:  # Add validation for UTR
            return jsonify({'error': 'UTR number is required'}), 400

        deposit_data = {
            'user_id': session['user_id'],
            'type': 'deposit',
            'amount': amount,
            'utr_number': utr_number,
            'status': 'pending'
        }

        response = supabase.table('transactions').insert(deposit_data).execute()
        return jsonify({'message': 'Deposit request submitted successfully'}), 200

    except Exception as e:
        print(f"Deposit error: {str(e)}")
        return jsonify({'error': str(e)}), 400

@app.route('/withdraw')
@login_required
def withdraw():
    return render_template('withdraw.html')

@app.route('/submit_withdraw', methods=['POST'])
@login_required
def submit_withdraw():
    try:
        data = request.json
        amount = float(data.get('amount'))
        
        if amount < 500:  # Minimum withdrawal amount
            return jsonify({'error': 'Minimum withdrawal amount is ₹500'}), 400

        # Check user balance
        user = supabase.table('users').select('balance').eq('id', session['user_id']).execute()
        if not user.data or user.data[0]['balance'] < amount:
            return jsonify({'error': 'Insufficient balance'}), 400

        withdraw_data = {
            'user_id': session['user_id'],
            'type': 'withdraw',
            'amount': amount,
            'bank_name': data.get('bankName'),
            'account_number': data.get('accountNumber'),
            'ifsc_code': data.get('ifscCode'),
            'account_holder': data.get('accountHolder'),
            'status': 'pending'
        }

        # Insert withdrawal request without deducting balance
        supabase.table('transactions').insert(withdraw_data).execute()

        return jsonify({
            'message': 'Withdrawal request submitted successfully',
            'status': 'success'
        }), 200

    except Exception as e:
        print(f"Error submitting withdrawal: {str(e)}")
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 400

@app.route('/rules')
@login_required
def rules():
    return render_template('rules.html')

@app.route('/results')
@login_required
def results():
    return render_template('results.html')

@app.route('/bets')
@login_required
def bets():
    return render_template('bets.html')

@app.route('/transactions')
@login_required
def transactions():
    return render_template('transactions.html')

@app.route('/complaints')
@login_required
def complaints():
    return render_template('complaints.html')

@app.route('/game')
@login_required
def game():
    return render_template('game.html')

@app.route('/admin/handle_deposit', methods=['POST'])
@admin_required
def handle_deposit():
    try:
        data = request.get_json()
        print("Received data:", data)  # Debug log

        if not data:
            return jsonify({'error': 'No data received'}), 400

        transaction_id = data.get('transaction_id')
        action = data.get('action')

        print(f"Processing transaction: {transaction_id} with action: {action}")  # Debug log

        if not transaction_id:
            return jsonify({'error': 'Missing transaction_id'}), 400
        if action not in ['approve', 'reject']:
            return jsonify({'error': 'Invalid action'}), 400

        # Get transaction details
        transaction = supabase.table('transactions')\
            .select('*')\
            .eq('id', transaction_id)\
            .single()\
            .execute()

        if not transaction.data:
            return jsonify({'error': 'Transaction not found'}), 404

        # Update transaction status
        new_status = 'completed' if action == 'approve' else 'rejected'
        
        # Update transaction status
        supabase.table('transactions')\
            .update({'status': new_status})\
            .eq('id', transaction_id)\
            .execute()

        if action == 'approve':
            # Get current user balance
            user = supabase.table('users')\
                .select('balance')\
                .eq('id', transaction.data['user_id'])\
                .single()\
                .execute()
            
            current_balance = float(user.data['balance']) if user.data['balance'] else 0
            new_balance = current_balance + float(transaction.data['amount'])

            # Update user balance
            supabase.table('users')\
                .update({'balance': new_balance})\
                .eq('id', transaction.data['user_id'])\
                .execute()

        return jsonify({
            'message': f'Deposit {action}ed successfully',
            'status': 'success'
        }), 200

    except Exception as e:
        print(f"Error handling deposit: {str(e)}")  # Debug log
        return jsonify({'error': str(e)}), 400

@app.route('/admin/handle_withdrawal', methods=['POST'])
@admin_required
def handle_withdrawal():
    try:
        data = request.json
        transaction_id = data.get('transaction_id')
        action = data.get('action')

        print(f"Handling withdrawal: {transaction_id} - {action}")  # Debug log

        if not transaction_id or action not in ['approve', 'reject']:
            return jsonify({'error': 'Invalid request parameters'}), 400

        # Get transaction details
        transaction = supabase.table('transactions')\
            .select('*')\
            .eq('id', transaction_id)\
            .single()\
            .execute()

        if not transaction.data:
            return jsonify({'error': 'Transaction not found'}), 404

        # Update transaction status
        new_status = 'completed' if action == 'approve' else 'rejected'
        
        # Update transaction status
        supabase.table('transactions')\
            .update({
                'status': new_status,
                'processed_at': datetime.datetime.now().isoformat()
            })\
            .eq('id', transaction_id)\
            .execute()

        if action == 'approve':
            # Get current user balance
            user = supabase.table('users')\
                .select('balance')\
                .eq('id', transaction.data['user_id'])\
                .single()\
                .execute()
            
            current_balance = float(user.data['balance']) if user.data['balance'] else 0
            new_balance = current_balance - float(transaction.data['amount'])

            # Update user balance (subtract the withdrawal amount)
            supabase.table('users')\
                .update({'balance': new_balance})\
                .eq('id', transaction.data['user_id'])\
                .execute()
        elif action == 'reject':
            # No need to refund for rejections since we haven't deducted the amount yet
            pass

        return jsonify({
            'message': f'Withdrawal {action}ed successfully',
            'status': 'success'
        }), 200

    except Exception as e:
        print(f"Error handling withdrawal: {str(e)}")
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 400

@app.route('/admin/add_result', methods=['POST'])
@admin_required
def add_result():
    try:
        data = request.json
        game_type = data.get('gameType')
        winning_numbers = data.get('winningNumbers')
        date = data.get('date')  # Get the date from the request

        if not game_type or not winning_numbers or not date:
            return jsonify({'error': 'Missing required fields'}), 400

        if len(winning_numbers) != 5:
            return jsonify({'error': 'Exactly 5 numbers are required'}), 400

        # Check if result already exists for this game type and date
        existing_result = supabase.table('game_results')\
            .select('*')\
            .eq('game_type', game_type)\
            .eq('date', date)\
            .execute()

        if existing_result.data:
            return jsonify({'error': f'Result for {game_type} game already exists for {date}'}), 400

        # Insert new result
        result_data = {
            'game_type': game_type,
            'winning_numbers': winning_numbers,
            'date': date,
            'created_at': datetime.datetime.now().isoformat(),
            'total_bets': 0,
            'total_payout': 0
        }

        response = supabase.table('game_results').insert(result_data).execute()

        # Process winning bets
        process_winning_bets(game_type, winning_numbers, date)

        return jsonify({'message': 'Game result added successfully'}), 200

    except Exception as e:
        print(f"Admin add result error: {str(e)}")
        return jsonify({'error': str(e)}), 400

def process_winning_bets(game_type, winning_numbers, date):
    try:
        # Get all pending bets for this game type and date
        bets = supabase.table('bets')\
            .select('*')\
            .eq('game_type', game_type)\
            .eq('status', 'pending')\
            .execute()

        for bet in bets.data:
            bet_numbers = bet['numbers']
            winning_count = len(set(bet_numbers) & set(winning_numbers))
            
            if winning_count > 0:
                # Calculate winnings based on game type and matching numbers
                multiplier = {
                    'morning': 20,
                    'afternoon': 10,
                    'evening': 4
                }.get(game_type, 0)
                
                winnings = float(bet['amount']) * multiplier * winning_count

                # Update bet status
                supabase.table('bets')\
                    .update({
                        'status': 'won',
                        'winning_amount': str(winnings),
                        'winning_count': winning_count
                    })\
                    .eq('id', bet['id'])\
                    .execute()

                # Update user balance
                user = supabase.table('users')\
                    .select('balance')\
                    .eq('id', bet['user_id'])\
                    .single()\
                    .execute()
                
                current_balance = float(user.data['balance']) if user.data['balance'] else 0
                new_balance = current_balance + winnings

                supabase.table('users')\
                    .update({'balance': str(new_balance)})\
                    .eq('id', bet['user_id'])\
                    .execute()
            else:
                # Update losing bets
                supabase.table('bets')\
                    .update({'status': 'lost'})\
                    .eq('id', bet['id'])\
                    .execute()

    except Exception as e:
        print(f"Error processing winning bets: {str(e)}")
        raise

@app.route('/check_session')
def check_session():
    if 'user_id' in session:
        return jsonify({'status': 'valid'}), 200
    return jsonify({'error': 'Invalid session'}), 401

@app.route('/admin/transactions')
@admin_required
def admin_transactions():
    try:
        # Get all transactions with user details
        query = """
            SELECT 
                t.*,
                u.username
            FROM transactions t
            JOIN users u ON t.user_id = u.id
            ORDER BY t.created_at DESC
        """
        
        result = supabase.table('transactions')\
            .select('*, users(username)')\
            .order('created_at', desc=True)\
            .execute()

        transactions = []
        for t in result.data:
            transactions.append({
                'id': t['id'],
                'username': t['users']['username'],
                'type': t['type'],
                'amount': str(t['amount']),
                'status': t['status'],
                'created_at': t['created_at'],
                'utr_number': t.get('utr_number'),
                'bank_name': t.get('bank_name'),
                'account_number': t.get('account_number'),
                'ifsc_code': t.get('ifsc_code'),
                'account_holder': t.get('account_holder')
            })

        return jsonify({'transactions': transactions})
    except Exception as e:
        print(f"Error fetching transactions: {str(e)}")
        return jsonify({'error': str(e)}), 400

@app.route('/get_transactions')
@login_required
def get_transactions():
    try:
        transaction_type = request.args.get('type', 'all')
        
        # Base query
        query = supabase.table('transactions').select('*').eq('user_id', session['user_id'])
        
        # Filter by type if specified
        if transaction_type != 'all':
            if transaction_type == 'deposits':
                query = query.eq('type', 'deposit')
            elif transaction_type == 'withdrawals':
                query = query.eq('type', 'withdraw')
            elif transaction_type == 'bets':
                query = query.eq('type', 'bet')
        
        # Execute query and order by created_at desc
        response = query.order('created_at', desc=True).execute()
        
        transactions = []
        for trans in response.data:
            transactions.append({
                'id': trans['id'],
                'type': trans['type'],
                'amount': float(trans['amount']),
                'status': trans['status'],
                'date': trans['created_at']
            })
        
        return jsonify({'transactions': transactions})
    except Exception as e:
        print(f"Error fetching transactions: {str(e)}")
        return jsonify({'error': str(e)}), 400

@app.route('/place_bet', methods=['POST'])
@login_required
def place_bet():
    try:
        data = request.json
        game_type = data.get('type')
        numbers = data.get('numbers')
        amount_per_bet = float(data.get('amount'))
        total_bets = len(numbers)  # Number of bets is equal to number of selected numbers
        total_amount = amount_per_bet * total_bets  # Calculate total amount

        # Validate inputs
        if not game_type or not numbers or not amount_per_bet:
            return jsonify({'error': 'Missing required fields'}), 400

        if amount_per_bet < 10:  # Minimum bet amount per number
            return jsonify({'error': 'Minimum bet amount is ₹10 per number'}), 400

        # Check user balance
        user_response = supabase.table('users').select('balance').eq('id', session['user_id']).execute()
        if not user_response.data:
            return jsonify({'error': 'User not found'}), 404

        current_balance = float(user_response.data[0]['balance'])
        if current_balance < total_amount:
            return jsonify({'error': f'Insufficient balance. Required: ₹{total_amount}'}, 400)

        # Calculate multiplier based on game type
        multiplier = {
            'morning': 20,
            'afternoon': 10,
            'evening': 4
        }.get(game_type)

        if not multiplier:
            return jsonify({'error': 'Invalid game type'}), 400

        # Insert individual bets into database
        for number in numbers:
            bet_data = {
                'user_id': session['user_id'],
                'game_type': game_type,
                'numbers': [number],  # Store as single number in array
                'amount': str(amount_per_bet),
                'potential_win': str(amount_per_bet * multiplier),
                'status': 'pending'
            }
            
            # Insert bet
            bet_response = supabase.table('bets').insert(bet_data).execute()

        # Update user balance
        new_balance = current_balance - total_amount
        supabase.table('users').update({'balance': str(new_balance)}).eq('id', session['user_id']).execute()

        # Add transaction record
        transaction_data = {
            'user_id': session['user_id'],
            'type': 'game_bet',
            'amount': str(total_amount),
            'status': 'completed'
        }
        supabase.table('transactions').insert(transaction_data).execute()

        return jsonify({
            'message': 'Bets placed successfully',
            'new_balance': new_balance,
            'total_amount': total_amount,
            'number_of_bets': total_bets
        }), 200

    except Exception as e:
        print(f"Error placing bet: {str(e)}")
        return jsonify({'error': str(e)}), 400

@app.route('/admin/dashboard-stats')
@admin_required
def get_dashboard_stats():
    try:
        # Get total users
        users_response = supabase.table('users').select('count', count='exact').execute()
        total_users = users_response.count if users_response.count else 0

        # Get total deposits
        deposits_response = supabase.table('transactions')\
            .select('amount')\
            .eq('type', 'deposit')\
            .eq('status', 'completed')\
            .execute()
        total_deposits = sum(float(t['amount']) for t in deposits_response.data) if deposits_response.data else 0

        # Get total withdrawals
        withdrawals_response = supabase.table('transactions')\
            .select('amount')\
            .eq('type', 'withdraw')\
            .eq('status', 'completed')\
            .execute()
        total_withdrawals = sum(float(t['amount']) for t in withdrawals_response.data) if withdrawals_response.data else 0

        # Get active bets
        active_bets_response = supabase.table('bets')\
            .select('count', count='exact')\
            .eq('status', 'pending')\
            .execute()
        active_bets = active_bets_response.count if active_bets_response.count else 0

        return jsonify({
            'totalUsers': total_users,
            'totalDeposits': total_deposits,
            'totalWithdrawals': total_withdrawals,
            'activeBets': active_bets
        })

    except Exception as e:
        print(f"Error fetching dashboard stats: {str(e)}")
        return jsonify({'error': str(e)}), 400

@app.route('/admin/pending-transactions')
@admin_required
def get_pending_transactions():
    try:
        # Get pending deposits and withdrawals with user details
        query = """
        SELECT 
            t.*,
            u.username,
            u.phone_number
        FROM transactions t
        JOIN users u ON t.user_id = u.id
        WHERE t.status = 'pending'
        AND (t.type = 'deposit' OR t.type = 'withdraw')
        ORDER BY t.created_at DESC
        """
        
        response = supabase.rpc('get_pending_transactions').execute()
        
        transactions = []
        for t in response.data:
            transactions.append({
                'id': t['id'],
                'username': t['username'],
                'type': t['type'],
                'amount': float(t['amount']),
                'status': t['status'],
                'date': t['created_at'],
                'utr_number': t.get('utr_number'),  # For deposits
                'bank_details': {  # For withdrawals
                    'bank_name': t.get('bank_name'),
                    'account_number': t.get('account_number'),
                    'ifsc_code': t.get('ifsc_code'),
                    'account_holder': t.get('account_holder')
                } if t.get('bank_name') else None
            })
        
        return jsonify({'transactions': transactions})

    except Exception as e:
        print(f"Error fetching pending transactions: {str(e)}")
        return jsonify({'error': str(e)}), 400

@app.route('/get_user_bets')
@login_required
def get_user_bets():
    try:
        response = supabase.table('bets')\
            .select('*')\
            .eq('user_id', session['user_id'])\
            .order('created_at', desc=True)\
            .execute()
        
        bets = []
        for bet in response.data:
            bets.append({
                'id': bet['id'],
                'game_type': bet['game_type'],
                'numbers': bet['numbers'],
                'amount': float(bet['amount']),
                'potential_win': float(bet['potential_win']),
                'status': bet['status'],
                'date': bet['created_at']
            })
        
        return jsonify({'bets': bets})
    except Exception as e:
        print(f"Error fetching bets: {str(e)}")
        return jsonify({'error': str(e)}), 400

@app.route('/admin/deposit-requests')
@admin_required
def get_deposit_requests():
    try:
        # Get pending deposits with user details and explicitly select utr_number
        response = supabase.table('transactions')\
            .select('id, amount, utr_number, created_at, users(username, phone_number)')\
            .eq('type', 'deposit')\
            .eq('status', 'pending')\
            .order('created_at', desc=True)\
            .execute()
        
        deposit_requests = []
        for transaction in response.data:
            deposit_requests.append({
                'id': transaction['id'],
                'username': transaction['users']['username'],
                'phone_number': transaction['users']['phone_number'],
                'amount': float(transaction['amount']),
                'utr_number': transaction.get('utr_number', 'N/A'),  # Added default value
                'created_at': transaction['created_at']
            })
            
        return jsonify({'deposit_requests': deposit_requests})
    except Exception as e:
        print(f"Error fetching deposit requests: {str(e)}")
        return jsonify({'error': str(e)}), 400

@app.route('/admin/withdrawal-requests')
@admin_required
def get_withdrawal_requests():
    try:
        # Get pending withdrawals with user details
        response = supabase.table('transactions')\
            .select('*, users(username, phone_number)')\
            .eq('type', 'withdraw')\
            .eq('status', 'pending')\
            .order('created_at', desc=True)\
            .execute()
        
        withdrawal_requests = []
        for transaction in response.data:
            withdrawal_requests.append({
                'id': transaction['id'],
                'username': transaction['users']['username'],
                'phone_number': transaction['users']['phone_number'],
                'amount': float(transaction['amount']),
                'bank_name': transaction['bank_name'],
                'account_number': transaction['account_number'],
                'ifsc_code': transaction['ifsc_code'],
                'account_holder': transaction['account_holder'],
                'created_at': transaction['created_at']
            })
            
        return jsonify({'withdrawal_requests': withdrawal_requests})
    except Exception as e:
        print(f"Error fetching withdrawal requests: {str(e)}")
        return jsonify({'error': str(e)}), 400

@app.route('/admin/users')
@admin_required
def admin_users():
    try:
        print("Fetching users from database...")  # Debug log
        response = supabase.table('users')\
            .select('id, username, phone_number, balance, created_at')\
            .order('created_at', desc=True)\
            .execute()
        
        print(f"Response from database: {response}")  # Debug log
        
        users = []
        for user in response.data:
            users.append({
                'id': user['id'],
                'username': user['username'],
                'phone_number': user['phone_number'],
                'balance': float(user['balance']) if user['balance'] else 0.0,
                'created_at': user['created_at']
            })
        
        print(f"Processed users: {users}")  # Debug log
        return jsonify({'users': users})
    
    except Exception as e:
        print(f"Error in admin_users route: {str(e)}")  # Debug log
        return jsonify({'error': str(e), 'users': []}), 400  # Added empty users array

@app.route('/admin/toggle-user-status', methods=['POST'])
@admin_required
def toggle_user_status():
    try:
        data = request.json
        user_id = data.get('user_id')
        is_active = data.get('is_active')

        if user_id is None or is_active is None:
            return jsonify({'error': 'Missing required parameters'}), 400

        # Update user status
        supabase.table('users')\
            .update({'is_active': is_active})\
            .eq('id', user_id)\
            .execute()

        return jsonify({'success': True, 'message': 'User status updated successfully'})
    except Exception as e:
        print(f"Error updating user status: {str(e)}")
        return jsonify({'error': str(e)}), 400

@app.route('/get_wallet_amount')
@login_required
def get_wallet_amount():
    try:
        response = supabase.table('users')\
            .select('balance')\
            .eq('id', session['user_id'])\
            .single()\
            .execute()
        
        if response.data:
            balance = float(response.data['balance']) if response.data['balance'] else 0.0
            return jsonify({'amount': balance})
        return jsonify({'amount': 0})
    except Exception as e:
        print(f"Error fetching wallet amount: {str(e)}")
        return jsonify({'error': str(e)}), 400

@app.route('/get_results')
@login_required
def get_results():
    try:
        date = request.args.get('date')
        if not date:
            date = datetime.datetime.now().date().isoformat()

        # Get results for the specified date using the date field directly
        response = supabase.table('game_results')\
            .select('*')\
            .eq('date', date)\
            .execute()

        results = []
        for result in response.data:
            game_type_display = {
                'morning': 'Morning Game (20x)',
                'afternoon': 'Afternoon Game (10x)',
                'evening': 'Evening Game (4x)'
            }.get(result['game_type'], result['game_type'])

            multiplier = {
                'morning': 20,
                'afternoon': 10,
                'evening': 4
            }.get(result['game_type'], 0)

            results.append({
                'type': game_type_display,
                'numbers': result['winning_numbers'],
                'multiplier': multiplier
            })

        # Sort results by game type (morning first, then afternoon, then evening)
        game_type_order = {'morning': 1, 'afternoon': 2, 'evening': 3}
        results.sort(key=lambda x: game_type_order.get(x['type'].split()[0].lower(), 4))

        return jsonify({'results': results})
    except Exception as e:
        print(f"Error fetching results: {str(e)}")
        return jsonify({'error': str(e)}), 400

@app.route('/get_user_info')
@login_required
def get_user_info():
    try:
        response = supabase.table('users')\
            .select('username, balance')\
            .eq('id', session['user_id'])\
            .single()\
            .execute()
        
        if response.data:
            return jsonify({
                'username': response.data['username'],
                'balance': float(response.data['balance']) if response.data['balance'] else 0.0
            })
        return jsonify({'error': 'User not found'}), 404
    except Exception as e:
        print(f"Error fetching user info: {str(e)}")
        return jsonify({'error': str(e)}), 400

@app.route('/admin/user/<user_id>')
@admin_required
def get_user_details(user_id):
    try:
        response = supabase.table('users')\
            .select('id, username, phone_number, balance, created_at, last_login')\
            .eq('id', user_id)\
            .single()\
            .execute()
        
        if not response.data:
            return jsonify({'error': 'User not found'}), 404
            
        user_data = {
            'id': response.data['id'],
            'username': response.data['username'],
            'phone_number': response.data['phone_number'],
            'balance': str(response.data['balance']) if response.data['balance'] else '0.00',
            'created_at': response.data['created_at'],
            'last_login': response.data['last_login']
        }
        return jsonify(user_data)
    except Exception as e:
        print(f"Error fetching user details: {str(e)}")
        return jsonify({'error': str(e)}), 400

@app.route('/admin/adjust-wallet', methods=['POST'])
@admin_required
def adjust_wallet():
    try:
        data = request.json
        user_id = data.get('user_id')
        amount = float(data.get('amount', 0))
        adjustment_type = data.get('type')  # 'add' or 'subtract'
        
        # Get current balance
        user = supabase.table('users')\
            .select('balance')\
            .eq('id', user_id)\
            .single()\
            .execute()
            
        if not user.data:
            return jsonify({'error': 'User not found'}), 404
            
        current_balance = float(user.data['balance'] or 0)
        
        # Calculate new balance
        if adjustment_type == 'add':
            new_balance = current_balance + amount
            transaction_type = 'winnings'  # Using 'winnings' for additions
        else:  # subtract
            if current_balance < amount:
                return jsonify({'error': 'Insufficient balance'}), 400
            new_balance = current_balance - amount
            transaction_type = 'withdraw'  # Using 'withdraw' for subtractions
            
        # Update balance
        supabase.table('users')\
            .update({'balance': str(new_balance)})\
            .eq('id', user_id)\
            .execute()
            
        # Add transaction record
        transaction_data = {
            'user_id': user_id,
            'type': transaction_type,
            'amount': str(amount),
            'status': 'completed'
        }
        supabase.table('transactions').insert(transaction_data).execute()
        
        return jsonify({
            'message': 'Wallet adjusted successfully',
            'new_balance': new_balance
        })
        
    except Exception as e:
        print(f"Error adjusting wallet: {str(e)}")
        return jsonify({'error': str(e)}), 400

@app.route('/admin/game-results')
@admin_required
def admin_game_results():
    try:
        # Get all results for the last 7 days, ordered by date and game type
        seven_days_ago = (datetime.datetime.now() - datetime.timedelta(days=7)).date().isoformat()
        
        response = supabase.table('game_results')\
            .select('*')\
            .gte('date', seven_days_ago)\
            .order('date', desc=True)\
            .order('created_at', desc=True)\
            .execute()

        results = []
        for result in response.data:
            # Format the game type display
            game_type_display = {
                'morning': 'Morning Game',
                'afternoon': 'Afternoon Game',
                'evening': 'Evening Game'
            }.get(result['game_type'], result['game_type'])

            # Convert numbers to strings and pad with zeros
            winning_numbers = [str(num).zfill(2) for num in result['winning_numbers']]

            results.append({
                'id': result['id'],
                'gameType': game_type_display,
                'winningNumber': ' - '.join(winning_numbers),
                'date': result['date'],
                'totalBets': result['total_bets'],
                'totalPayout': float(result['total_payout'])
            })

        return jsonify({'results': results})
    except Exception as e:
        print(f"Error fetching game results: {str(e)}")
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run()  # Remove debug=True

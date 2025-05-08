import os
import json
import mysql.connector
import pyotp
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from collections import Counter
import math
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import uuid
from decimal import Decimal

app = Flask(__name__)
app.secret_key = 'supersecretkey123'
app.permanent_session_lifetime = timedelta(minutes=30)

# Download NLTK data
nltk.download('punkt')
nltk.download('stopwords')
stop_words = set(stopwords.words('english'))

# MySQL Configuration
db_config = {
    'user': 'root',
    'password': '53143519',
    'host': 'localhost',
    'database': 'iwb_system_db'
}

def get_db_connection():
    return mysql.connector.connect(**db_config)

# Custom JSON encoder to handle Decimal
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

# Backup function with Decimal handling
def backup_data(table, data):
    backup_dir = 'backups'
    os.makedirs(backup_dir, exist_ok=True)
    backup_file = os.path.join(backup_dir, f'{table}_backup.json')
    with open(backup_file, 'a') as f:
        json.dump(data, f, cls=DecimalEncoder)
        f.write('\n')

# Word similarity for automated replies
def cosine_similarity(text1, text2):
    tokens1 = [w.lower() for w in word_tokenize(text1) if w.lower() not in stop_words]
    tokens2 = [w.lower() for w in word_tokenize(text2) if w.lower() not in stop_words]
    counter1 = Counter(tokens1)
    counter2 = Counter(tokens2)
    terms = set(counter1).union(counter2)
    dotprod = sum(counter1.get(k, 0) * counter2.get(k, 0) for k in terms)
    mag1 = math.sqrt(sum(counter1.get(k, 0)**2 for k in terms))
    mag2 = math.sqrt(sum(counter2.get(k, 0)**2 for k in terms))
    return dotprod / (mag1 * mag2) if mag1 * mag2 != 0 else 0

# Home Page
@app.route('/')
def home():
    return render_template('home.html')

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            session['mfa_secret'] = user['mfa_secret']
            return redirect(url_for('mfa'))
        flash('Invalid credentials')
    return render_template('login.html')

# Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT COUNT(*) AS count FROM users WHERE role = %s', (role,))
        count = cursor.fetchone()['count']
        if (role in ['Sales', 'Finance', 'Developer'] and count >= 3) or username == '':
            flash('Role limit reached or invalid username')
            cursor.close()
            conn.close()
            return render_template('register.html')
        cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
        if cursor.fetchone():
            flash('Username exists')
            cursor.close()
            conn.close()
            return render_template('register.html')
        mfa_secret = pyotp.random_base32()
        hashed_password = generate_password_hash(password)
        cursor.execute('INSERT INTO users (username, password, role, mfa_secret) VALUES (%s, %s, %s, %s)',
                       (username, hashed_password, role, mfa_secret))
        conn.commit()
        cursor.close()
        conn.close()
        flash('Registration successful. Please log in.')
        return redirect(url_for('login'))
    return render_template('register.html')

# MFA Verification
@app.route('/mfa', methods=['GET', 'POST'])
def mfa():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        mfa_code = request.form['mfa_code']
        totp = pyotp.TOTP(session['mfa_secret'])
        if totp.verify(mfa_code):
            session['mfa_verified'] = True
            return redirect(url_for('dashboard'))
        flash('Invalid MFA code')
    totp = pyotp.TOTP(session['mfa_secret'])
    mfa_code = totp.now()
    return render_template('mfa.html', mfa_code=mfa_code)

# Dashboard
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session or not session.get('mfa_verified'):
        return redirect(url_for('login'))
    role = session['role']
    return render_template('dashboard.html', role=role)

# Products
@app.route('/products', methods=['GET', 'POST'])
def products():
    if 'user_id' not in session or not session.get('mfa_verified'):
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    category = request.form.get('category') if request.method == 'POST' else None
    if category:
        cursor.execute('SELECT * FROM products WHERE category = %s', (category,))
    else:
        cursor.execute('SELECT * FROM products')
    products = cursor.fetchall()
    cursor.execute('SELECT DISTINCT category FROM products')
    categories = [row['category'] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return render_template('products.html', products=products, categories=categories)

# Buy Product
@app.route('/buy/<int:product_id>', methods=['POST'])
def buy_product(product_id):
    if 'user_id' not in session or not session.get('mfa_verified') or session['role'] != 'Client':
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM products WHERE id = %s', (product_id,))
    product = cursor.fetchone()
    if product:
        sale = {
            'id': str(uuid.uuid4()),
            'user_id': session['user_id'],
            'product_id': product_id,
            'amount': product['price'],
            'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        cursor.execute('INSERT INTO sales (id, user_id, product_id, amount, date) VALUES (%s, %s, %s, %s, %s)',
                       (sale['id'], sale['user_id'], sale['product_id'], sale['amount'], sale['date']))
        conn.commit()
        backup_data('sales', sale)
    cursor.close()
    conn.close()
    flash('Purchase successful')
    return redirect(url_for('products'))

# Queries
@app.route('/queries', methods=['GET', 'POST'])
def queries():
    if 'user_id' not in session or not session.get('mfa_verified'):
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    if request.method == 'POST' and session['role'] == 'Client':
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']
        query_id = str(uuid.uuid4())
        # Check for similar queries
        cursor.execute('SELECT message, response FROM queries WHERE status = %s', ('complete',))
        past_queries = cursor.fetchall()
        max_similarity = 0
        response = None
        for past_query in past_queries:
            similarity = cosine_similarity(message, past_query['message'])
            if similarity > max_similarity and similarity > 0.7:
                max_similarity = similarity
                response = past_query['response']
        status = 'complete' if response else 'pending'
        response = response or ''
        cursor.execute('INSERT INTO queries (id, name, email, message, status, response) VALUES (%s, %s, %s, %s, %s, %s)',
                       (query_id, name, email, message, status, response))
        conn.commit()
        backup_data('queries', {'id': query_id, 'name': name, 'email': email, 'message': message, 'status': status, 'response': response})
        flash('Query submitted')
    if session['role'] == 'Sales':
        if request.method == 'POST' and 'respond' in request.form:
            query_id = request.form['query_id']
            response = request.form['response']
            cursor.execute('UPDATE queries SET response = %s, status = %s WHERE id = %s',
                           (response, 'complete', query_id))
            conn.commit()
            backup_data('queries', {'id': query_id, 'response': response, 'status': 'complete'})
            flash('Response submitted')
        cursor.execute('SELECT * FROM queries')
        queries = cursor.fetchall()
        return render_template('queries.html', queries=queries, role=session['role'])
    cursor.close()
    conn.close()
    return render_template('queries.html', role=session['role'])

# Income Statement
@app.route('/income_statement', methods=['GET', 'POST'])
def income_statement():
    if 'user_id' not in session or not session.get('mfa_verified') or session['role'] not in ['Finance', 'Investor']:
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    if request.method == 'POST' and session['role'] == 'Finance':
        month = request.form['month']
        revenue = float(request.form['revenue'])
        expenses = float(request.form['expenses'])
        cursor.execute('INSERT INTO income_statements (month, revenue, expenses) VALUES (%s, %s, %s)',
                       (month, revenue, expenses))
        conn.commit()
        flash('Income statement updated')
    cursor.execute('SELECT * FROM income_statements ORDER BY month')
    statements = cursor.fetchall()
    chart_data = {
        'labels': [s['month'] for s in statements],
        'revenue': [s['revenue'] for s in statements],
        'expenses': [s['expenses'] for s in statements],
        'profit': [s['revenue'] - s['expenses'] for s in statements]
    }
    cursor.close()
    conn.close()
    return render_template('income_statement.html', statements=statements, chart_data=chart_data, role=session['role'])

# IWC Partner Access (Simulated Multi-Tenant)
@app.route('/iwc_access')
def iwc_access():
    if 'user_id' not in session or not session.get('mfa_verified') or session['role'] != 'Partner':
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM products')
    products = cursor.fetchall()
    cursor.execute('SELECT * FROM sales')
    sales = cursor.fetchall()
    cursor.execute('SELECT * FROM income_statements')
    statements = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('dashboard.html', role='Partner', products=products, sales=sales, statements=statements)

# Logout
@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out')
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
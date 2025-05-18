from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
import os
import uuid


app = Flask(__name__)
app.secret_key = "your_secret_key"

# Upload folder setup
app.config['UPLOAD_FOLDER'] = 'uploadimages'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Database config
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "Priya123",
    "database": "register_db"
}

# Home route
@app.route('/')
def index():
    return render_template('index.html')

# About page
# @app.route('/about')
# def about():
#     return render_template('about.html')

#Early Prediction
@app.route('/Resume')
def Resume():
    return render_template('Resume.html')

@app.route('/Analyse')
def Analyse():
    return render_template('Analyzer.html')



# Web: Register view
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        password = generate_password_hash(request.form['password'])

        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (name, email, phone, password) VALUES (%s, %s, %s, %s)",
                           (name, email, phone, password))
            conn.commit()
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for('login'))
        except mysql.connector.Error as err:
            flash(f"Database error: {err}", "danger")
        finally:
            cursor.close()
            conn.close()

    return render_template('register.html')

# Web: Login view
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s AND password = %s", (email, password))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            session['user_id'] = user['id']
            flash("Login successful!", "success")
            return redirect(url_for('dashboard'))  # Redirect to dashboard after login
        else:
            flash("Invalid credentials", "danger")
    return render_template('login.html')

# Dashboard (only for logged-in users)
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash("Please log in to access your dashboard.", "warning")
        return redirect(url_for('login'))  # Redirect to login page instead of dashboard itself.

    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)

        # Fetch user details
        cursor.execute("SELECT name, email, phone FROM users WHERE id = %s", (session['user_id'],))
        user_details = cursor.fetchone()

        # Fetch scan history
        cursor.execute(""" 
            SELECT prediction, confidence, notes, created_at 
            FROM history 
            WHERE user_id = %s 
            ORDER BY created_at DESC
        """, (session['user_id'],))
        history = cursor.fetchall()

        total_scans = len(history)
        disease_count = sum(1 for scan in history if scan['prediction'].lower() != 'healthy')
        last_scan = history[0]['created_at'].strftime('%b %d, %Y') if history else 'N/A'

        return render_template('dashboard.html',
                               name=user_details['name'],
                               email=user_details['email'],
                               phone=user_details['phone'],
                               total_scans=total_scans,
                               disease_count=disease_count,
                               last_scan=last_scan,
                               history=history)

    except mysql.connector.Error as err:
        flash(f"Error loading dashboard: {err}", "danger")
        return redirect(url_for('home'))
    finally:
        cursor.close()
        conn.close()

# Disease check (image upload)
@app.route('/disease', methods=['GET', 'POST'])
def disease():
    if request.method == 'POST' and 'img' in request.files:
        image = request.files['img']
        filename = f"{uuid.uuid4().hex}_{image.filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image.save(filepath)

        # Simulated prediction
        prediction = "Disease"
        confidence = 0.85
        notes = "Symptoms observed"

        # Save only if user is logged in
        if 'user_id' in session:
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO history (user_id, prediction, confidence, notes, created_at)
                VALUES (%s, %s, %s, %s, NOW())
            """, (session['user_id'], prediction, confidence, notes))
            conn.commit()
            cursor.close()
            conn.close()

        return render_template('disease.html', imagepath=filepath, prediction=prediction)

    return render_template('disease.html')

# API: Register
@app.route('/api/register', methods=['POST'])
def api_register():
    try:
        name = request.json.get('name')
        email = request.json.get('email')
        phone = request.json.get('phone')
        password = generate_password_hash(request.json.get('password'))

        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (name, email, phone, password) VALUES (%s, %s, %s, %s)",
                       (name, email, phone, password))
        conn.commit()
        cursor.close()
        conn.close()

        return {"message": "Registration successful!"}, 200
    except mysql.connector.Error as err:
        return {"error": f"Database error: {err}"}, 500

# API: Login
@app.route('/api/login', methods=['POST'])
def api_login():
    try:
        email = request.json.get('email')
        password = request.json.get('password')

        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['name'] = user['name']
            flash("Login successful!", "success")
            return redirect(url_for('dashboard'))  # <-- change made here

        else:
            return jsonify({"error": "Invalid email or password"}), 400

    except mysql.connector.Error as err:
        return jsonify({"error": f"Database error: {err}"}), 500

# Logout
@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))

# Run the app
if __name__ == "__main__":
    app.run(host='127.0.0.1', port=5000, debug=True)

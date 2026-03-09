import os
import requests
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import pyrebase
from dotenv import load_dotenv
import uuid
from functools import wraps

load_dotenv()

app = Flask(__name__)
app.secret_key = 'super_secret_hackathon_key'

firebaseApi = os.getenv('FIREBASE_API')

# -------------------------------------------------------------
# FIREBASE CONFIGURATION
# -------------------------------------------------------------
firebaseConfig = {
  'apiKey': firebaseApi,
  'authDomain': "agentwork-286b1.firebaseapp.com",
  'databaseURL': "https://agentwork-286b1-default-rtdb.europe-west1.firebasedatabase.app",
  'projectId': "agentwork-286b1",
  'storageBucket': "agentwork-286b1.firebasestorage.app",
  'messagingSenderId': "853364448721",
  'appId': "1:853364448721:web:bad7cda4a5cb002849d4f0"
}

try:
    firebase = pyrebase.initialize_app(firebaseConfig)
    db = firebase.database()
    auth = firebase.auth() 
    print("🔥 Firebase DB and Auth connected successfully!")
except Exception as e:
    db = None
    auth = None
    print(f"❌ Firebase not connected yet: {e}")

# -------------------------------------------------------------
# SECURITY DECORATOR (Locks down routes)
# -------------------------------------------------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("🔒 Please login to access this secure area.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# -------------------------------------------------------------
# MOCK DATABASE (Fallback)
# -------------------------------------------------------------
mock_bots = [
    {
        "id": "1", "name": "DocuForge Architect", "dev": "TechNinja", "price": "₦5,000 / mo", 
        "desc": "Instantly generates beautiful, professional GitHub READMEs from messy descriptions.",
        "endpoint": "http://127.0.0.1:5001/generate", "rating": "4.9", "reviews": "142"
    },
    {
        "id": "2", "name": "React Optimizer", "dev": "FrontendGod", "price": "₦12,000 / mo", 
        "desc": "Analyzes React components and suggests rapid performance optimizations.",
        "endpoint": "mock", "rating": "4.7", "reviews": "89"
    },
    {
        "id": "3", "name": "SQL Whisperer", "dev": "DataKing", "price": "₦8,500 / mo", 
        "desc": "Translates plain English into complex, highly optimized SQL queries.",
        "endpoint": "mock", "rating": "4.8", "reviews": "215"
    },
    {
        "id": "4", "name": "Bug Hunter Pro", "dev": "QA_Master", "price": "₦15,000 / mo", 
        "desc": "Scans your Python codebase for security vulnerabilities and logic errors.",
        "endpoint": "mock", "rating": "4.6", "reviews": "56"
    },
    {
        "id": "5", "name": "Regex Wizard", "dev": "StringLord", "price": "₦2,500 / mo", 
        "desc": "Generates and perfectly explains complex Regular Expressions instantly.",
        "endpoint": "mock", "rating": "4.9", "reviews": "340"
    }
]

# -------------------------------------------------------------
# PUBLIC ROUTES
# -------------------------------------------------------------
@app.route('/')
def index():
    live_bots = []
    if db:
        try:
            bots_query = db.child("bots").get()
            if bots_query.each():
                for bot in bots_query.each():
                    if bot.val():
                        live_bots.append(bot.val())
        except Exception as e:
            print(f"Error fetching from Firebase: {e}")
            live_bots = mock_bots 
    else:
        live_bots = mock_bots
        
    return render_template('index.html', bots=live_bots)

# -------------------------------------------------------------
# AUTHENTICATION ROUTES
# -------------------------------------------------------------
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role') # 'employer' or 'developer'
        
        try:
            # Create the user in Firebase Auth
            user = auth.create_user_with_email_and_password(email, password)
            
            # Store their profile/role in the Database
            user_data = {
                "email": email,
                "role": role,
                "uid": user['localId']
            }
            db.child("users").child(user['localId']).set(user_data)
            
            flash("Account created! Please log in.", "success")
            return redirect(url_for('login'))
        except Exception as e:
            # Simplify the error message for the UI
            print(f"🔥 FIREBASE AUTH ERROR: {e}") 
            flash(f"Signup error: {e}", "danger")
            
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        try:
            # Authenticate with Firebase
            user = auth.sign_in_with_email_and_password(email, password)
            
            # Fetch their role from the DB
            user_profile = db.child("users").child(user['localId']).get().val()
            
            # Set the Session securely
            session['user_id'] = user['localId']
            session['role'] = user_profile.get('role', 'employer')
            session['email'] = email
            
            if 'purchased_bots' not in session:
                session['purchased_bots'] = []
                
            flash(f"Welcome back to AgentGrid!", "success")
            
            if session['role'] == 'developer':
                return redirect(url_for('developer_dashboard'))
            return redirect(url_for('employer_dashboard'))
            
        except Exception as e:
            flash("Invalid email or password.", "danger")
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been securely logged out.", "success")
    return redirect(url_for('index'))

# -------------------------------------------------------------
# SECURE WORKSPACE & MARKETPLACE ROUTES
# -------------------------------------------------------------
@app.route('/bot/<bot_id>')
def bot_details(bot_id):
    bot = None
    if db:
        try:
            bot = db.child("bots").child(bot_id).get().val()
        except Exception as e:
            print(f"Error fetching bot {bot_id} from Firebase: {e}")
            
    if not bot:
        bot = next((b for b in mock_bots if str(b['id']) == str(bot_id)), None)
        
    if not bot:
        return "Bot not found", 404
        
    purchased = session.get('purchased_bots', [])
    has_purchased = str(bot_id) in [str(pid) for pid in purchased]
    
    return render_template('bot_details.html', bot=bot, has_purchased=has_purchased)

@app.route('/buy/<bot_id>', methods=['POST'])
@login_required
def buy_bot(bot_id):
    if session.get('role') != 'employer':
        flash("Only Employers can acquire agents.", "warning")
        return redirect(url_for('index'))

    if 'purchased_bots' not in session:
        session['purchased_bots'] = []
        
    if bot_id not in session['purchased_bots']:
        session['purchased_bots'].append(bot_id)
        session.modified = True
        flash("Agent successfully acquired!", "success")
        
    return redirect(url_for('employer_dashboard'))

@app.route('/dashboard/employer')
@login_required
def employer_dashboard():
    if session.get('role') != 'employer':
        return redirect(url_for('index'))
        
    purchased_ids = [str(pid) for pid in session.get('purchased_bots', [])]
    my_bots = []
    
    if db:
        try:
            bots_query = db.child("bots").get()
            if bots_query.each():
                for bot in bots_query.each():
                    bot_data = bot.val()
                    if bot_data and str(bot_data.get('id')) in purchased_ids:
                        my_bots.append(bot_data)
        except Exception as e:
            print(f"Dashboard Firebase Error: {e}")
            
    return render_template('dashboard.html', bots=my_bots, role='employer')

@app.route('/dashboard/developer')
@login_required
def developer_dashboard():
    if session.get('role') != 'developer':
        return redirect(url_for('index'))
    return render_template('dashboard.html', role='developer')

@app.route('/deploy', methods=['GET', 'POST'])
@login_required
def deploy():
    if session.get('role') != 'developer':
        flash("Only Developers can deploy new agents.", "warning")
        return redirect(url_for('index'))

    if request.method == 'POST':
        bot_id = str(uuid.uuid4())[:8]
        new_bot = {
            "id": bot_id, 
            "name": request.form.get('name'),
            "dev": request.form.get('dev', session.get('email', 'Unknown')),
            "price": request.form.get('price') + " / mo",
            "desc": request.form.get('desc'),
            "endpoint": request.form.get('endpoint'),
            "rating": "New", 
            "reviews": "0"
        }
        
        if db:
            db.child("bots").child(bot_id).set(new_bot)
        else:
            mock_bots.append(new_bot) 
        
        flash(f"Agent '{new_bot['name']}' successfully deployed to the grid!", "success")
        return redirect(url_for('developer_dashboard'))
        
    return render_template('deploy.html')

# -------------------------------------------------------------
# THE MICROSERVICE PROXY
# -------------------------------------------------------------
@app.route('/chat/<bot_id>')
@login_required
def chat_ui(bot_id):
    purchased = session.get('purchased_bots', [])
    if str(bot_id) not in [str(pid) for pid in purchased]:
        flash("You must acquire this agent before launching the terminal.", "warning")
        return redirect(url_for('bot_details', bot_id=bot_id))
        
    bot = None
    if db:
        bot = db.child("bots").child(bot_id).get().val()
        
    if not bot:
        bot = next((b for b in mock_bots if str(b['id']) == str(bot_id)), None)

    if not bot:
        return "Agent data corrupted or missing.", 404
        
    return render_template('chat.html', bot=bot)

@app.route('/api/chat', methods=['POST'])
@login_required
def api_chat():
    data = request.json
    bot_id = str(data.get('agent_id'))
    user_message = data.get('message')
    
    bot = None
    if db:
        bot = db.child("bots").child(bot_id).get().val()
    if not bot:
        bot = next((b for b in mock_bots if str(b['id']) == bot_id), None)
    
    if bot and bot.get('endpoint') and bot['endpoint'] != 'mock':
        try:
            response = requests.post(
                bot['endpoint'], 
                json={"message": user_message},
                timeout=15
            )
            return jsonify(response.json())
        except requests.exceptions.RequestException as e:
            return jsonify({"reply": f"**Connection Error:** Agent offline or endpoint unreachable. Details: {str(e)}"})
            
    return jsonify({"reply": "🔒 *Premium Agent Locked.* This is a mocked bot simulation."})

# -------------------------------------------------------------
# DATABASE SEEDING
# -------------------------------------------------------------
@app.route('/seed')
def seed_db():
    if not db:
        return "❌ Firebase is not connected. Check your .env and config."
    try:
        for bot in mock_bots:
            db.child("bots").child(bot['id']).set(bot)
        return "✅ BOOM! Database successfully populated! Go check your Firebase console."
    except Exception as e:
        return f"❌ Error populating database: {e}"

if __name__ == '__main__':
    app.run(debug=True, port=5000)
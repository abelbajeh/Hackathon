import os
import requests
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import pyrebase
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = 'super_secret_hackathon_key'

# -------------------------------------------------------------
# FIREBASE CONFIGURATION (Add real keys in .env later)
# -------------------------------------------------------------
firebaseConfig = {
    "apiKey": os.getenv("FIREBASE_API_KEY", "mock_key"),
    "authDomain": "your-project.firebaseapp.com",
    "databaseURL": "https://your-project-default-rtdb.firebaseio.com",
    "projectId": "your-project",
    "storageBucket": "your-project.appspot.com",
    "messagingSenderId": "123456789",
    "appId": "1:123:web:456"
}

try:
    firebase = pyrebase.initialize_app(firebaseConfig)
    db = firebase.database()
except Exception as e:
    db = None
    print(f"Firebase not connected yet: {e}")

# -------------------------------------------------------------
# MOCK DATABASE
# -------------------------------------------------------------
# -------------------------------------------------------------
# MOCK DATABASE
# -------------------------------------------------------------
# -------------------------------------------------------------
# MOCK DATABASE (10 Premium Agents)
# -------------------------------------------------------------
mock_bots = [
    {
        "id": "1", "name": "DocuForge Architect", "dev": "TechNinja", "price": "₦5,000", 
        "desc": "Instantly generates beautiful, professional GitHub READMEs from messy descriptions.",
        "endpoint": "http://127.0.0.1:5001/generate", "rating": "4.9", "reviews": "142"
    },
    {
        "id": "2", "name": "React Optimizer", "dev": "FrontendGod", "price": "₦12,000", 
        "desc": "Analyzes React components and suggests rapid performance optimizations.",
        "endpoint": "mock", "rating": "4.7", "reviews": "89"
    },
    {
        "id": "3", "name": "SQL Whisperer", "dev": "DataKing", "price": "₦8,500", 
        "desc": "Translates plain English into complex, highly optimized SQL queries.",
        "endpoint": "mock", "rating": "4.8", "reviews": "215"
    },
    {
        "id": "4", "name": "Bug Hunter Pro", "dev": "QA_Master", "price": "₦15,000", 
        "desc": "Scans your Python codebase for security vulnerabilities and logic errors.",
        "endpoint": "mock", "rating": "4.6", "reviews": "56"
    },
    {
        "id": "5", "name": "Regex Wizard", "dev": "StringLord", "price": "₦2,500", 
        "desc": "Generates and perfectly explains complex Regular Expressions instantly.",
        "endpoint": "mock", "rating": "4.9", "reviews": "340"
    },
    {
        "id": "6", "name": "CopyGenius", "dev": "MarketMage", "price": "₦4,000", 
        "desc": "Writes high-converting landing page copy based on product features.",
        "endpoint": "mock", "rating": "4.5", "reviews": "12"
    },
    {
        "id": "7", "name": "Docker Dynamo", "dev": "DevOpsDan", "price": "₦9,000", 
        "desc": "Automatically generates optimized Dockerfiles and docker-compose scripts.",
        "endpoint": "mock", "rating": "4.8", "reviews": "112"
    },
    {
        "id": "8", "name": "Tailwind Titan", "dev": "CSS_Savant", "price": "₦6,000", 
        "desc": "Converts rough UI sketches into pixel-perfect Tailwind CSS code blocks.",
        "endpoint": "mock", "rating": "4.7", "reviews": "88"
    },
    {
        "id": "9", "name": "CyberGuard Pentester", "dev": "SecOpsZero", "price": "₦25,000", 
        "desc": "Simulates OWASP Top 10 attacks against your staging endpoints to find flaws.",
        "endpoint": "mock", "rating": "4.9", "reviews": "45"
    },
    {
        "id": "10", "name": "Schema Smith", "dev": "MongoMaster", "price": "₦7,500", 
        "desc": "Designs scalable NoSQL database schemas from basic app requirements.",
        "endpoint": "mock", "rating": "4.6", "reviews": "67"
    }
]
# -------------------------------------------------------------
# CORE ROUTES
# -------------------------------------------------------------
@app.route('/')
def index():
    return render_template('index.html', bots=mock_bots)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        role = request.form.get('role')
        session['role'] = role
        session['user'] = 'DemoUser'
        session['purchased_bots'] = [] 
        
        if role == 'developer':
            return redirect(url_for('developer_dashboard'))
        return redirect(url_for('employer_dashboard'))
        
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# -------------------------------------------------------------
# PURCHASE & INVENTORY FLOW
# -------------------------------------------------------------
@app.route('/bot/<bot_id>')
def bot_details(bot_id):
    bot = next((b for b in mock_bots if b['id'] == bot_id), None)
    if not bot:
        return "Bot not found", 404
        
    purchased = session.get('purchased_bots', [])
    has_purchased = bot_id in purchased
    
    return render_template('bot_details.html', bot=bot, has_purchased=has_purchased)

@app.route('/buy/<bot_id>', methods=['POST'])
def buy_bot(bot_id):
    if 'purchased_bots' not in session:
        session['purchased_bots'] = []
        
    if bot_id not in session['purchased_bots']:
        session['purchased_bots'].append(bot_id)
        session.modified = True
        
    return redirect(url_for('employer_dashboard'))

@app.route('/dashboard/employer')
def employer_dashboard():
    if session.get('role') != 'employer':
        return redirect(url_for('login'))
        
    purchased_ids = session.get('purchased_bots', [])
    my_bots = [b for b in mock_bots if b['id'] in purchased_ids]
    
    return render_template('dashboard.html', bots=my_bots, role='employer')

@app.route('/dashboard/developer')
def developer_dashboard():
    if session.get('role') != 'developer':
        return redirect(url_for('login'))
    return render_template('dashboard.html', role='developer')

# -------------------------------------------------------------
# THE MICROSERVICE PROXY
# -------------------------------------------------------------
@app.route('/chat/<bot_id>')
def chat_ui(bot_id):
    purchased = session.get('purchased_bots', [])
    if bot_id not in purchased:
        return redirect(url_for('bot_details', bot_id=bot_id))
        
    bot = next((b for b in mock_bots if b['id'] == bot_id), None)
    return render_template('chat.html', bot=bot)

@app.route('/api/chat', methods=['POST'])
def api_chat():
    data = request.json
    bot_id = str(data.get('agent_id'))
    user_message = data.get('message')
    
    bot = next((b for b in mock_bots if b['id'] == bot_id), None)
    
    if bot and bot['endpoint'] != 'mock':
        try:
            # This request reaches across from Windows into WSL!
            response = requests.post(
                bot['endpoint'], 
                json={"message": user_message},
                timeout=15
            )
            return jsonify(response.json())
        except requests.exceptions.RequestException as e:
            return jsonify({"reply": f"**Connection Error:** Make sure the WSL bot is running on port 5001. Details: {str(e)}"})
            
    return jsonify({"reply": "🔒 *Premium Agent Locked.* This is a mocked bot simulation."})

if __name__ == '__main__':
    # Runs on Windows on port 5000
    app.run(debug=True, port=5000)
import os
import json
import re
import uuid
from datetime import datetime
import mysql.connector
import google.generativeai as genai
from flask import Flask, render_template, request, jsonify, session
from werkzeug.security import generate_password_hash

print(generate_password_hash('PASTE_HASH_HERE'))

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key')

# ✅ Configure Gemini API
genai.configure(api_key="AIzaSyDSIujQ3rSjTpqpsuXCiiV82xPqswxG5jc")  # ⚠️ Replace with your real API key

# ✅ UMS Knowledge Base
UMS_KNOWLEDGE = {
    "history": "Universiti Malaysia Sabah (UMS) was established in 1994 as the ninth public university in Malaysia. It started with just 205 students and has grown into a leading institution focused on Borneo-centric research and education.",
    "campus": "UMS has two main campuses: Kota Kinabalu (main) and Labuan. The Kota Kinabalu campus spans 999 acres with modern facilities like libraries, sports complexes, and research labs.",
    "faculties": "Key faculties include Faculty of Science and Natural Resources, Faculty of Engineering, Faculty of Business, Economics and Accountancy, and Faculty of Humanities, Arts and Heritage.",
    "admissions": "Admissions are handled via UPU (Unit Pusat Universiti). Requirements vary by program but generally include STPM, Matriculation, or Diploma qualifications.",
    "student_life": "UMS offers vibrant student life with clubs, events, and international collaborations. It's known for its focus on environmental and social sciences.",
}

# ✅ System instruction for Gemini
SYSTEM_INSTRUCTION = f"""
You are SmartUMS, a friendly AI assistant for Universiti Malaysia Sabah (UMS).
Your goal is to help users with information about UMS — such as faculties, programs, admissions, and campus life.
Be polite, organized, and write like a helpful student advisor.

Formatting Rules:
- Use **bold** for key terms (faculties, programs, or years).
- Use line breaks between paragraphs.
- Use bullet points (-) or numbers (1., 2., 3.) for lists.
- Keep answers under 200 words and end with a short encouragement.
- Always respond only about UMS (politely redirect if question is unrelated).
Use this knowledge base as reference: {json.dumps(UMS_KNOWLEDGE)}
"""

# ✅ Configure Gemini model
model = genai.GenerativeModel(
    "gemini-2.0-flash",
    system_instruction=SYSTEM_INSTRUCTION,
    generation_config={
        "temperature": 0.7,
        "top_p": 0.9,
        "max_output_tokens": 700,
    }
)

# ✅ Load local JSON data with improved error handling
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

def load_json(filename):
    """Load JSON file with proper error handling"""
    path = os.path.join(DATA_DIR, filename)
    try:
        # Check if file exists
        if not os.path.exists(path):
            print(f"⚠️ File not found: {path}")
            print(f"💡 Please create the file at: {os.path.abspath(path)}")
            return []
        
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"✅ Successfully loaded {filename}: {len(data)} records")
            return data
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing error in {filename}: {e}")
        print(f"💡 Check if {filename} contains valid JSON format")
        return []
    except Exception as e:
        print(f"❌ Failed to load {filename}: {e}")
        return []

# Create data directory if it doesn't exist
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)
    print(f"📁 Created data directory at: {os.path.abspath(DATA_DIR)}")

PROGRAMS_DATABASE = load_json('programs.json')
CLASSES_DATABASE = load_json('classes.json')
CONTACTS_DATABASE = load_json('contacts.json')

# ✅ MySQL connection setup
mysql_config = {
    'user': 'root',
    'password': '',
    'host': 'localhost',
    'database': 'smartums',
    'raise_on_warnings': True
}

def create_mysql_tables():
    """Create all necessary MySQL tables"""
    try:
        conn = mysql.connector.connect(**mysql_config)
        cursor = conn.cursor()

        # Create programs table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS programs (
            id INT PRIMARY KEY,
            nama_program VARCHAR(255),
            universiti VARCHAR(255),
            fakulti VARCHAR(255),
            kod_program VARCHAR(50),
            tempoh VARCHAR(50),
            syarat_kemasukan TEXT,
            prospek_kerjaya TEXT,
            kategori VARCHAR(100)
        )
        """)
        print("✅ Table 'programs' ready")

        # Create contacts table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS contacts (
            id INT PRIMARY KEY,
            name VARCHAR(255),
            role VARCHAR(100),
            phone VARCHAR(50),
            email VARCHAR(255)
        )
        """)
        print("✅ Table 'contacts' ready")

        # Create classes table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS classes (
            id INT PRIMARY KEY,
            courseCode VARCHAR(50),
            courseName VARCHAR(255),
            instructor VARCHAR(255),
            building VARCHAR(100),
            room VARCHAR(100),
            time VARCHAR(100),
            timeType VARCHAR(50),
            day VARCHAR(100),
            capacity INT,
            enrolled INT,
            status VARCHAR(50)
        )
        """)
        print("✅ Table 'classes' ready")

        # Create chatbot_messages table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS chatbot_messages (
            id INT AUTO_INCREMENT PRIMARY KEY,
            message TEXT,
            message_date DATE,
            message_time TIME
        )
        """)
        print("✅ Table 'chatbot_messages' ready")

        # Create feedbacks table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS feedbacks (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255),
            email VARCHAR(255),
            rating INT,
            category VARCHAR(100),
            message TEXT,
            recommend VARCHAR(10),
            submitted_at DATETIME
        )
        """)
        print("✅ Table 'feedbacks' ready")

        conn.commit()
        cursor.close()
        conn.close()
        print("✅ All MySQL tables created successfully!")

    except mysql.connector.Error as e:
        print(f"❌ MySQL table creation error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error creating tables: {e}")

def import_programs_to_mysql():
    """Import programs from JSON to MySQL"""
    if not PROGRAMS_DATABASE:
        print("⚠️ No programs data to import")
        return

    try:
        conn = mysql.connector.connect(**mysql_config)
        cursor = conn.cursor()

        imported = 0
        for item in PROGRAMS_DATABASE:
            cursor.execute("""
                INSERT INTO programs (id, nama_program, universiti, fakulti, kod_program, tempoh, syarat_kemasukan, prospek_kerjaya, kategori)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    nama_program = VALUES(nama_program),
                    universiti = VALUES(universiti),
                    fakulti = VALUES(fakulti),
                    kod_program = VALUES(kod_program),
                    tempoh = VALUES(tempoh),
                    syarat_kemasukan = VALUES(syarat_kemasukan),
                    prospek_kerjaya = VALUES(prospek_kerjaya),
                    kategori = VALUES(kategori)
            """, (
                item.get("id"),
                item.get("nama_program"),
                item.get("universiti"),
                item.get("fakulti"),
                item.get("kod_program"),
                item.get("tempoh"),
                item.get("syarat_kemasukan"),
                item.get("prospek_kerjaya"),
                item.get("kategori")
            ))
            imported += 1

        conn.commit()
        print(f"✅ Imported {imported} programs into MySQL successfully!")
        cursor.close()
        conn.close()

    except mysql.connector.Error as e:
        print(f"❌ MySQL error importing programs: {e}")
    except Exception as e:
        print(f"❌ Failed to import programs: {e}")

def import_contacts_to_mysql():
    """Import contacts from JSON to MySQL"""
    if not CONTACTS_DATABASE:
        print("⚠️ No contacts data to import")
        return

    try:
        conn = mysql.connector.connect(**mysql_config)
        cursor = conn.cursor()

        imported = 0
        for item in CONTACTS_DATABASE:
            cursor.execute("""
                INSERT INTO contacts (id, name, role, phone, email)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    name = VALUES(name),
                    role = VALUES(role),
                    phone = VALUES(phone),
                    email = VALUES(email)
            """, (
                item.get("id"),
                item.get("name"),
                item.get("role"),
                item.get("phone"),
                item.get("email")
            ))
            imported += 1

        conn.commit()
        print(f"✅ Imported {imported} contacts into MySQL successfully!")
        cursor.close()
        conn.close()

    except mysql.connector.Error as e:
        print(f"❌ MySQL error importing contacts: {e}")
    except Exception as e:
        print(f"❌ Failed to import contacts: {e}")

def import_classes_to_mysql():
    """Import classes from JSON to MySQL"""
    if not CLASSES_DATABASE:
        print("⚠️ No classes data to import")
        return

    try:
        conn = mysql.connector.connect(**mysql_config)
        cursor = conn.cursor()

        imported = 0
        for item in CLASSES_DATABASE:
            cursor.execute("""
                INSERT INTO classes (id, courseCode, courseName, instructor, building, room, time, timeType, day, capacity, enrolled, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    courseCode = VALUES(courseCode),
                    courseName = VALUES(courseName),
                    instructor = VALUES(instructor),
                    building = VALUES(building),
                    room = VALUES(room),
                    time = VALUES(time),
                    timeType = VALUES(timeType),
                    day = VALUES(day),
                    capacity = VALUES(capacity),
                    enrolled = VALUES(enrolled),
                    status = VALUES(status)
            """, (
                item.get("id"),
                item.get("courseCode"),
                item.get("courseName"),
                item.get("instructor"),
                item.get("building"),
                item.get("room"),
                item.get("time"),
                item.get("timeType"),
                item.get("day"),
                item.get("capacity"),
                item.get("enrolled"),
                item.get("status")
            ))
            imported += 1

        conn.commit()
        print(f"✅ Imported {imported} classes into MySQL successfully!")
        cursor.close()
        conn.close()

    except mysql.connector.Error as e:
        print(f"❌ MySQL error importing classes: {e}")
    except Exception as e:
        print(f"❌ Failed to import classes: {e}")

# ✅ Save chat message to MySQL
def save_message_to_mysql(content):
    try:
        conn = mysql.connector.connect(**mysql_config)
        cursor = conn.cursor()
        now = datetime.now()
        message_date = now.date()
        message_time = now.time().replace(microsecond=0)
        cursor.execute(
            "INSERT INTO chatbot_messages (message, message_date, message_time) VALUES (%s, %s, %s)",
            (content, message_date, message_time)
        )
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"❌ MySQL save error: {e}")

# ✅ Save feedback to MySQL
def save_feedback_to_mysql(name, email, rating, category, message, recommend, submitted_at):
    try:
        conn = mysql.connector.connect(**mysql_config)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO feedbacks (name, email, rating, category, message, recommend, submitted_at) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (name, email, rating, category, message, recommend, submitted_at)
        )
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"❌ MySQL feedback save error: {e}")

# ✅ Flask Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/carian-program')
def carian_program():
    print("✅ Accessing program search page")
    try:
        return render_template('carian_program.html')
    except Exception as e:
        print(f"❌ Error loading template: {e}")
        return f"Template error: {e}", 500

@app.route("/syarat-kemasukan")
def syarat_page():
    return render_template("syarat.html")

@app.route('/classlocator')
def classlocator():
    return render_template('classlocator.html')

@app.route("/contact")
def contact():
    return render_template("contact.html")

@app.route('/debug')
def debug():
    return f"""
    <h1 style="color: red;">DEBUG PAGE</h1>
    <p>If you see this, Flask is working!</p>
    <h2>Data Status:</h2>
    <ul>
        <li>Programs loaded: {len(PROGRAMS_DATABASE)} records</li>
        <li>Classes loaded: {len(CLASSES_DATABASE)} records</li>
        <li>Contacts loaded: {len(CONTACTS_DATABASE)} records</li>
    </ul>
    <h2>Routes:</h2>
    <ul>
        <li><a href="/">Main Chatbot</a></li>
        <li><a href="/carian-program">Carian Program</a></li>
        <li><a href="/classlocator">Class Locator</a></li>
        <li><a href="/contact">Contact</a></li>
    </ul>
    <p>Current routes working: ✅</p>
    """

# ✅ Program Search
@app.route('/search-programs', methods=['POST'])
def search_programs():
    try:
        data = request.json
        keyword = data.get('keyword', '').lower().strip()
        kategori = data.get('kategori', '').lower().strip()

        print(f"🔍 Searching for: keyword='{keyword}', kategori='{kategori}'")

        results = []
        for program in PROGRAMS_DATABASE:
            match_keyword = (
                keyword == '' or 
                keyword in program.get('nama_program', '').lower() or
                keyword in program.get('universiti', '').lower() or
                keyword in program.get('fakulti', '').lower() or
                keyword in program.get('kod_program', '').lower() or
                keyword in program.get('prospek_kerjaya', '').lower()
            )
            match_kategori = (
                kategori == '' or 
                kategori in program.get('kategori', '').lower()
            )
            if match_keyword and match_kategori:
                results.append(program)

        print(f"✅ Found {len(results)} programs")
        return jsonify({'success': True, 'results': results, 'total': len(results)})
    except Exception as e:
        print(f"❌ Search error: {e}")
        return jsonify({'success': False, 'error': str(e)})
    
@app.route('/programs.json')
def programs_json():
    return send_from_directory('data', 'programs.json')

@app.route('/api/programs')
def api_programs():
    return jsonify({'success': True, 'programs': PROGRAMS_DATABASE})

@app.route('/api/classes')
def api_classes():
    return jsonify({'success': True, 'classes': CLASSES_DATABASE})

@app.route('/api/contacts')
def api_contacts():
    return jsonify({'success': True, 'contacts': CONTACTS_DATABASE})

@app.route('/get-program-details/<int:program_id>')
def get_program_details(program_id):
    try:
        program = next((p for p in PROGRAMS_DATABASE if p.get('id') == program_id), None)
        if program:
            return jsonify({'success': True, 'program': program})
        else:
            return jsonify({'success': False, 'error': 'Program not found'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ✅ Chatbot endpoint
@app.route('/ask', methods=['POST'])
def ask():
    user_input = request.json.get('message', '').strip()

    if not user_input:
        return jsonify({'reply': "It seems like you didn't enter anything. How can I help you with **Universiti Malaysia Sabah (UMS)** today?"})

    session_id = session.get('session_id')
    if not session_id:
        session_id = str(uuid.uuid4())
        session['session_id'] = session_id

    try:
        if 'chat_history' not in session:
            session['chat_history'] = []

        chat_history = session['chat_history']
        chat = model.start_chat(history=chat_history)

        response = chat.send_message(user_input)
        raw_text = response.text.strip() if hasattr(response, 'text') else "Sorry, I didn't understand that."

        cleaned_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', raw_text)
        cleaned_text = cleaned_text.replace("\n\n", "<br><br>").replace("\n", "<br>")

        chat_history.append({"role": "user", "parts": [user_input]})
        chat_history.append({"role": "model", "parts": [raw_text]})
        if len(chat_history) > 20:
            chat_history = chat_history[-20:]
        session['chat_history'] = chat_history

        save_message_to_mysql(user_input)
        save_message_to_mysql(raw_text)

        return jsonify({'reply': cleaned_text})
    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({'reply': f"⚠️ An error occurred: {str(e)}"})

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🚀 Starting SmartUMS Application")
    print("="*50 + "\n")
    
    # Step 1: Create all MySQL tables first
    print("📊 Step 1: Creating MySQL tables...")
    create_mysql_tables()
    
    # Step 2: Import JSON data to MySQL
    print("\n📥 Step 2: Importing JSON data to MySQL...")
    import_programs_to_mysql()
    import_contacts_to_mysql()
    import_classes_to_mysql()
    
    print("\n" + "="*50)
    print("✅ Application ready!")
    print("="*50 + "\n")
    
    app.run(debug=True)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai
import os
import sqlite3
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

system_instruction = """
You are a loyal, attentive, and charming Prince. You are speaking to your Princess.
Your goal is to listen to her talk about her day, document her life, and respond with 
warmth, curiosity, and royal elegance. Ask engaging questions about her daily adventures.
Keep your responses concise but thoughtful. Do not break character.
"""

model = genai.GenerativeModel(
    model_name="gemini-flash-lite-latest",
    system_instruction=system_instruction
)

prince_chat = model.start_chat(history=[])

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatMessage(BaseModel):
    text: str

# New Model to handle updates
class JournalUpdate(BaseModel):
    summary: str
    color: str

def init_db():
    conn = sqlite3.connect('journal.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS journal_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            summary TEXT
        )
    ''')
    # SENIOR DEV TRICK: Safely add the new color column to your existing database
    try:
        cursor.execute("ALTER TABLE journal_entries ADD COLUMN color TEXT DEFAULT '#fff8e1'")
    except sqlite3.OperationalError:
        pass # The column already exists, do nothing!
        
    conn.commit()
    conn.close()

init_db()

@app.post("/talk-to-prince")
async def talk_to_prince(message: ChatMessage):
    try:
        response = prince_chat.send_message(message.text)
        prince_reply = response.text
    except Exception as e:
        prince_reply = "Forgive me, Princess, my mind wandered for a moment."
        print(f"Error: {e}")
    return {"prince_reply": prince_reply}

@app.post("/summarize-day")
async def summarize_day():
    try:
        prompt = """
        Based on our conversation today, please write a short, elegant journal entry 
        summarizing the Princess's day. Focus on the most notable event she mentioned. 
        Write it in the third person (e.g., 'Today, the Princess...'). Keep it to one short paragraph.
        """
        response = prince_chat.send_message(prompt)
        summary = response.text
        
        conn = sqlite3.connect('journal.db')
        cursor = conn.cursor()
        current_date = datetime.now().strftime("%B %d, %Y - %I:%M %p")
        # Default new entries to a pale gold color
        cursor.execute("INSERT INTO journal_entries (date, summary, color) VALUES (?, ?, ?)", (current_date, summary, "#fff8e1"))
        conn.commit()
        conn.close()
    except Exception as e:
        summary = "The royal scribes encountered an error documenting the day."
        print(f"Error: {e}")
    return {"summary": summary}

@app.get("/get-journal")
async def get_journal():
    conn = sqlite3.connect('journal.db')
    cursor = conn.cursor()
    # We now fetch the ID and Color as well!
    cursor.execute("SELECT id, date, summary, color FROM journal_entries ORDER BY id DESC")
    entries = cursor.fetchall()
    conn.close()
    
    formatted_entries = [{"id": row[0], "date": row[1], "summary": row[2], "color": row[3]} for row in entries]
    return {"entries": formatted_entries}

# --- NEW: Delete Route ---
@app.delete("/delete-journal/{entry_id}")
async def delete_journal(entry_id: int):
    conn = sqlite3.connect('journal.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM journal_entries WHERE id = ?", (entry_id,))
    conn.commit()
    conn.close()
    return {"status": "success"}

# --- NEW: Update Route ---
@app.put("/update-journal/{entry_id}")
async def update_journal(entry_id: int, update_data: JournalUpdate):
    conn = sqlite3.connect('journal.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE journal_entries SET summary = ?, color = ? WHERE id = ?", 
                   (update_data.summary, update_data.color, entry_id))
    conn.commit()
    conn.close()
    return {"status": "success"}
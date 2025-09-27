import streamlit as st
from faster_whisper import WhisperModel
import sounddevice as sd
import soundfile as sf
import os
from datetime import datetime
import sqlite3
from google import genai
from google.genai import types
import tempfile
import numpy as np
import time

# ---------------- CONFIG ----------------
st.set_page_config(page_title="AI Meeting Buddy", layout="wide")
st.title("🤖 AI Meeting Buddy - Full Auto AI Meeting Buddy Demo")

# ---------------- DATABASE ----------------
DB_PATH = "data/meetings.db"
os.makedirs("data", exist_ok=True)

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS meeting_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    agenda TEXT,
    content TEXT,
    key_points TEXT,
    audio_file TEXT
)
""")
conn.commit()

# ---------------- GEMINI AI ----------------
client = genai.Client(api_key="AIzaSyBF_kbylhLnlTgdULfAhpKCKmBIfdMx-Yo")  # replace with your key

# ---------------- WHISPER ----------------
model = WhisperModel("small")  # small model

# ---------------- BEFORE MEETING ----------------
st.header("📝 Before Meeting")
agenda_input = st.text_area("Enter meeting topic / purpose:", "", key="agenda_input")
if st.button("Generate Agenda"):
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=f"Generate a detailed meeting agenda for: {agenda_input}",
            config=types.GenerateContentConfig(temperature=0.3, max_output_tokens=150)
        )
        st.session_state.agenda = response.text
        st.success("✅ Agenda generated!")
    except Exception as e:
        st.error(f"Error generating agenda: {e}")

if "agenda" in st.session_state:
    st.markdown(f"**Generated Agenda:**\n{st.session_state.agenda}")

# ---------------- CURRENT MEETING (Demo) ----------------
st.header("🎤 Current Meeting")

if "current_transcript" not in st.session_state:
    st.session_state.current_transcript = ""
if "current_key_points" not in st.session_state:
    st.session_state.current_key_points = ""

# --- Live mic recording ---
if st.checkbox("Enable Live Microphone Recording"):
    st.warning("⚠️ Live recording demo not fully automated. Use audio upload for now.")

# --- Audio upload ---
uploaded_file = st.file_uploader("Upload meeting audio (.wav)", type=["wav", "mp3"])

if uploaded_file:
    temp_audio_path = f"data/temp_uploaded_audio.wav"
    with open(temp_audio_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    st.success("✅ Audio uploaded!")

    # Transcribe
    segments, _ = model.transcribe(temp_audio_path)
    transcript = " ".join([s.text for s in segments])
    st.session_state.current_transcript = transcript
    st.text_area("Transcript", st.session_state.current_transcript, height=150)
    
    # Generate key points
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=f"Generate key points per speaker from this transcript:\n{transcript}",
            config=types.GenerateContentConfig(temperature=0.3, max_output_tokens=200)
        )
        st.session_state.current_key_points = response.text
        st.text_area("Key Points", st.session_state.current_key_points, height=150)
    except Exception as e:
        st.error(f"Error generating key points: {e}")

# --- Manual text input ---
manual_transcript = st.text_area("Or enter transcript manually:", "", height=150)
if manual_transcript.strip():
    st.session_state.current_transcript = manual_transcript

# Save current meeting
if st.button("Save Current Meeting"):
    if st.session_state.current_transcript.strip():
        audio_file_path = ""
        if uploaded_file:
            audio_file_path = f"data/meeting_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
            with open(audio_file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
        c.execute(
            "INSERT INTO meeting_notes (timestamp, agenda, content, key_points, audio_file) VALUES (?, ?, ?, ?, ?)",
            (
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                st.session_state.get("agenda", ""),
                st.session_state.current_transcript,
                st.session_state.current_key_points,
                audio_file_path
            )
        )
        conn.commit()
        st.success("✅ Current meeting saved!")

# ---------------- PAST MEETINGS ----------------
st.header("📚 Past Meetings (Key Points)")

c.execute("SELECT id, timestamp, agenda, content, key_points FROM meeting_notes ORDER BY id DESC LIMIT 10")
past_meetings = c.fetchall()

# Demo data if no past meetings
if not past_meetings:
    past_meetings = [
        (1, "2025-09-26 10:00", "Team Sync", "Discussed project updates and blockers.", "Alice: Update on feature X\nBob: Issue in module Y"),
        (2, "2025-09-25 15:00", "Client Call", "Reviewed client requirements and next steps.", "Client: Needs faster delivery\nTeam: Agreed on timeline")
    ]

for meeting in past_meetings:
    meeting_id, timestamp, agenda, content, key_points = meeting
    st.markdown(f"**🕒 {timestamp}**")
    st.markdown(f"**Agenda:** {agenda}")
    st.markdown(f"**Transcript (Preview):** {content[:200]}{'...' if len(content)>200 else ''}")

    if key_points:
        st.markdown(f"**Key Points:**\n{key_points}")
    else:
        st.markdown("**Key Points:** Not generated yet.")

    if st.button(f"Generate Key Points for Meeting {meeting_id}"):
        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=f"Summarize key points per speaker from this meeting:\n{content}",
                config=types.GenerateContentConfig(temperature=0.3, max_output_tokens=200)
            )
            key_points_generated = response.text
            c.execute("UPDATE meeting_notes SET key_points=? WHERE id=?", (key_points_generated, meeting_id))
            conn.commit()
            st.success("✅ Key points generated and saved!")
            st.markdown(f"**Key Points:**\n{key_points_generated}")
        except Exception as e:
            st.error(f"Error generating key points: {e}")

    st.markdown("---")

# ---------------- CALENDAR / SCHEDULE EVENT ----------------
# ---------------- SCHEDULE / REMINDERS ----------------
st.header("📅 Schedule / Reminders")

# SQLite setup for events
conn = sqlite3.connect("data/meetings.db", check_same_thread=False)
c = conn.cursor()
c.execute("""
CREATE TABLE IF NOT EXISTS schedule_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    datetime TEXT,
    notes TEXT,
    participants TEXT
)
""")
conn.commit()

# Input fields
event_title = st.text_input("Event Title")
event_date = st.date_input("Event Date")
event_time = st.time_input("Event Time")
event_notes = st.text_area("Notes / Description")
event_participants = st.text_input("Participants (comma separated emails/names)")

if st.button("Add Event"):
    if event_title.strip():
        event_datetime = datetime.combine(event_date, event_time)
        c.execute(
            "INSERT INTO schedule_events (title, datetime, notes, participants) VALUES (?, ?, ?, ?)",
            (event_title, event_datetime.strftime("%Y-%m-%d %H:%M:%S"), event_notes, event_participants)
        )
        conn.commit()
        st.success(f"✅ Event '{event_title}' added for {event_datetime.strftime('%Y-%m-%d %H:%M')}")

# Show upcoming events
st.subheader("Upcoming Events")
now = datetime.now()
c.execute("SELECT id, title, datetime, notes, participants FROM schedule_events ORDER BY datetime ASC")
events = c.fetchall()

for ev in events:
    ev_id, title, dt_str, notes, participants = ev
    ev_time = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
    highlight = ""
    # Remind if event starts within 10 minutes
    if 0 <= (ev_time - now).total_seconds() <= 600:
        highlight = "🚨 Reminder: Event starting soon!"
        st.markdown(f"**{title}** - {ev_time.strftime('%Y-%m-%d %H:%M')} {highlight}")
    else:
        st.markdown(f"**{title}** - {ev_time.strftime('%Y-%m-%d %H:%M')}")

    if notes:
        st.markdown(f"Notes: {notes}")
    if participants:
        st.markdown(f"Participants: {participants}")

    st.markdown("---")
import streamlit as st
from datetime import datetime, timedelta
import sqlite3
import os

# ---------------- CONFIG ----------------
st.set_page_config(page_title="AI Meeting Buddy", layout="wide")
st.title("🤖 AI Meeting Buddy - Dashboard & Schedule Demo")

# ---------------- DATABASE ----------------
DB_PATH = "data/meetings.db"
os.makedirs("data", exist_ok=True)
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS meetings_schedule (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT,
    date TEXT,
    time TEXT,
    participants TEXT,
    agenda TEXT
)
""")
conn.commit()

# ---------------- SCHEDULE INPUT ----------------
st.header("📅 Add New Meeting Schedule")
topic = st.text_input("Meeting Topic / Purpose")
date = st.date_input("Date")
time_input = st.time_input("Time")
participants = st.text_area("Participants (comma separated)")
agenda = st.text_area("Agenda")

if st.button("Add Meeting"):
    if topic.strip() != "":
        c.execute(
            "INSERT INTO meetings_schedule (topic, date, time, participants, agenda) VALUES (?, ?, ?, ?, ?)",
            (topic, date.strftime("%Y-%m-%d"), time_input.strftime("%H:%M"), participants, agenda)
        )
        conn.commit()
        st.success("✅ Meeting schedule added!")

# ---------------- DISPLAY SCHEDULE ----------------
st.header("📋 Upcoming Meetings")

c.execute("SELECT id, topic, date, time, participants, agenda FROM meetings_schedule ORDER BY date, time")
meetings = c.fetchall()

if not meetings:
    st.info("No scheduled meetings. Add one above!")
else:
    for m in meetings:
        m_id, m_topic, m_date, m_time, m_participants, m_agenda = m
        st.markdown(f"**🕒 {m_date} {m_time} | {m_topic}**")
        st.markdown(f"**Participants:** {m_participants}")
        st.markdown(f"**Agenda:** {m_agenda}")
        
        # Calculate reminder (15 minutes before)
        meeting_datetime = datetime.strptime(f"{m_date} {m_time}", "%Y-%m-%d %H:%M")
        reminder_time = meeting_datetime - timedelta(minutes=15)
        st.markdown(f"**Reminder:** {reminder_time.strftime('%Y-%m-%d %H:%M')} (15 min before)")

        st.markdown("---")

conn.close()

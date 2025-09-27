from fastapi import FastAPI
import json
import pandas as pd
import os

app = FastAPI(title="AI Meeting Buddy API 🚀")

# --- Get the path of the current backend folder ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- Load mock data from backend folder ---
def load_json(filename):
    with open(os.path.join(BASE_DIR, filename), "r") as f:
        return json.load(f)

def load_csv(filename):
    return pd.read_csv(os.path.join(BASE_DIR, filename))

try:
    calendar_slots = load_json("calendar_slots.json")
    past_meetings = pd.read_json(os.path.join(BASE_DIR, "past_meetings.json"))
    prep_notes = load_json("prep_notes.json")
    sales_data = load_csv("sales_records.csv")
    reminders = load_csv("reminders.csv")
except FileNotFoundError as e:
    print(f"Error: {e}")
    calendar_slots = {}
    past_meetings = pd.DataFrame()
    prep_notes = []
    sales_data = pd.DataFrame()
    reminders = pd.DataFrame()

# --- Health Check Endpoint ---
@app.get("/")
def home():
    return {"message": "AI Meeting Buddy API 🚀"}

# --- Suggest Meeting Slot ---
@app.get("/suggest_slot")
def suggest_slot():
    if "chennai" not in calendar_slots or "germany" not in calendar_slots:
        return {"message": "Calendar slots not available"}

    chennai = set(calendar_slots["chennai"])
    germany = set(calendar_slots["germany"])
    common_slots = list(chennai & germany)

    if common_slots:
        return {"suggested_slot": common_slots[0]}
    else:
        return {"message": "No common slots available"}

# --- Generate Prep Notes / Agenda ---
@app.get("/generate_agenda")
def generate_agenda():
    agenda_list = []

    # Add past meetings topics
    if not past_meetings.empty:
        for meeting in past_meetings.to_dict(orient="records"):
            agenda_list.append(f"Discuss: {meeting['topic']}")

    # Add sales data context
    if not sales_data.empty:
        for _, row in sales_data.iterrows():
            agenda_list.append(f"Review sales: {row['product']} for {row['customer']} ({row['licenses']} licenses)")

    return {"agenda": agenda_list, "prep_notes": prep_notes}

# --- Show Reminders / Follow-ups ---
@app.get("/reminders")
def get_reminders():
    if reminders.empty:
        return {"reminders": []}
    return {"reminders": reminders.to_dict(orient="records")}

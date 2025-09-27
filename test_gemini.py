import google.generativeai as genai

# Your API key
genai.configure(api_key="AIzaSyBF_kbylhLnlTgdULfAhpKCKmBIfdMx-Yo")

past_text = """
- Discussed project timeline and milestones.
- Assigned tasks to team members.
- Reviewed last sprint blockers.
"""

try:
    response = genai.TextCompletion.create(
        model="text-bison-001",
        prompt=f"Based on these past meeting notes, suggest agenda points for the next meeting:\n{past_text}",
        temperature=0.5,
        max_output_tokens=256
    )
    print("✅ Gemini AI Agenda Output:")
    print(response.result)
except Exception as e:
    print("❌ Error:", e)

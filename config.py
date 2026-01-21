import os
from dotenv import load_dotenv
load_dotenv()
api_key = os.getenv("GROQ_API_KEY")
HELPLINES = {
    "India": {"Name": "Tele-MANAS / KIRAN", "Number": "14416 / 1800-599-0019"},
    "USA": {"Name": "988 Suicide & Crisis Lifeline", "Number": "988"},
    "UK": {"Name": "National Health Service (NHS)", "Number": "111"},
    "Canada": {"Name": "Talk Suicide Canada", "Number": "1-833-456-4566"},
    "Australia": {"Name": "Lifeline", "Number": "13 11 14"},
}

INSIGHTS = [
    "Research shows that 70% of students find relief through short, consistent breaks.",
    "Studies indicate that physical activity can reduce student anxiety by up to 40%.",
    "Data suggests that students who maintain a regular sleep schedule report 25% higher focus levels.",
    "Peer support is cited as a top coping mechanism for 65% of university students.",
    "Grounding exercises (like the 5-4-3-2-1 technique) are proven to lower immediate heart rate during stress.",
]

GROQ_API_KEY = os.getenv("GROQ_API_KEY")


import json
import os
from datetime import datetime, timedelta
from json import JSONDecodeError
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq

BASE_DIR = Path(__file__).resolve().parent
DAILY_MISSION_HOURS = 24

load_dotenv(BASE_DIR / ".env")

client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

def data_path(filename):
    return BASE_DIR / filename


def now_text():
    return datetime.now().isoformat(timespec="seconds")


def parse_time(value):
    if not value:
        return None

    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def next_unlock_time(history):
    if not history:
        return None

    latest_time = None

    for mission in history:
        mission_time = parse_time(mission.get("created_at"))

        if not mission_time:
            mission_time = parse_time(mission.get("completed_at"))

        if mission_time and (latest_time is None or mission_time > latest_time):
            latest_time = mission_time

    if not latest_time:
        return None

    return latest_time + timedelta(hours=DAILY_MISSION_HOURS)


def daily_mission_ready(history):
    unlock_time = next_unlock_time(history)

    if not unlock_time:
        return True

    return datetime.now() >= unlock_time


def show_next_unlock(history):
    unlock_time = next_unlock_time(history)

    if not unlock_time:
        return

    remaining = unlock_time - datetime.now()

    if remaining.total_seconds() <= 0:
        print("\nYour next daily mission is unlocked.")
        return

    hours = remaining.seconds // 3600
    minutes = (remaining.seconds % 3600) // 60

    print("\nNo new mission yet.")
    print(f"Next daily mission unlocks at: {unlock_time.strftime('%Y-%m-%d %I:%M %p')}")
    print(f"Time left: {remaining.days * 24 + hours}h {minutes}m")


def ask_groq(prompt):
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    return response.choices[0].message.content


def extract_json(text):
    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1:
        raise ValueError("No JSON object found in AI response")

    return json.loads(text[start:end + 1])


def load_data():
    try:
        with open(data_path("user_data.json"), "r") as f:
            print("Found user_data.json")
            return json.load(f)
    except FileNotFoundError:
        print("user_data.json not found")
        return None
    except JSONDecodeError:
        print("user_data.json is empty or corrupted")
        return None


def save_data(data):
    with open(data_path("user_data.json"), "w") as f:
        json.dump(data, f, indent=4)


def load_history():
    try:
        with open(data_path("history.json"), "r") as f:
            return json.load(f)
    except:
        return []


def first_time_setup():
    print("\nFirst day setup")
    print("Tell me your interests and what you already know.")

    interests = [
        interest.strip()
        for interest in input("\nEnter interests (comma separated): ").split(",")
        if interest.strip()
    ]

    knowledge = {}

    for interest in interests:
        print(f"\nWhat do you already know in {interest}?")
        print("Example: Python, Pandas, Basics")

        topics = input("> ").split(",")

        knowledge[interest] = [
            topic.strip()
            for topic in topics
            if topic.strip()
        ]

    data = {
        "interests": interests,
        "knowledge": knowledge,
        "setup_complete": True
    }

    save_data(data)

    print("\nProfile saved.")
    print("From next run, I will tell you what to study and give you a daily mission.")

    return data


def update_knowledge(mission):
    if mission.get("type") == "crazy_break":
        print("Break mission completed. Study knowledge not changed.")
        return

    data = load_data()

    skill = mission["skill"]
    topic = mission["topic"]

    if skill not in data["knowledge"]:
        data["knowledge"][skill] = []

    if topic not in data["knowledge"][skill]:
        data["knowledge"][skill].append(topic)

        save_data(data)

        print(f"{topic} added to {skill}")


def complete_mission(mission):
    mission["status"] = "completed"
    mission["completed_at"] = now_text()

    print("\nMission Completed!")

    update_knowledge(mission)

    current_mission_path = data_path("current_mission.json")

    if current_mission_path.exists():
        current_mission_path.unlink()
    print("Current mission removed.")

    history = load_history()

    exists = False

    for item in history:
        if (
            item["topic"] == mission["topic"]
            and item["mission"] == mission["mission"]
        ):
            exists = True
            break

    if not exists:
        history.append(mission)

    with open(data_path("history.json"), "w") as f:
        json.dump(history, f, indent=4)

    show_next_unlock(history)


def show_mission(mission):
    print("\nWhat you should study:")
    print(f"{mission['skill']} - {mission['topic']}")

    if mission.get("study_reason"):
        print("\nWhy this next:")
        print(mission["study_reason"])

    if mission.get("created_at"):
        created_at = parse_time(mission["created_at"])
        if created_at:
            print("\nMission created:")
            print(created_at.strftime("%Y-%m-%d %I:%M %p"))

    print("\nMission:")
    print(mission["mission"])


def check_status():
    with open(data_path("current_mission.json"), "r") as f:
        mission = json.load(f)

    show_mission(mission)

    completed = input("\nDid you complete it? (y/n): ").lower()

    if completed == "y":
        complete_mission(mission)
    else:
        print("\nKeep working on it!")


def fallback_mission(mission_type, data, history):
    if mission_type == "crazy_break":
        return {
            "skill": "Break",
            "topic": "Focus Reset",
            "study_reason": "A short reset helps you come back with better focus.",
            "mission": "Step away from the screen, stretch for 5 minutes, then drink water",
            "type": "crazy_break"
        }

    interests = data.get("interests", []) if data else []
    skill = interests[0] if interests else "AIML"

    return {
        "skill": skill,
        "topic": "Next Practical Step",
        "study_reason": "This keeps your progress moving with a small practical task.",
        "mission": f"Complete one small practical exercise related to {skill}",
        "type": "study"
    }


def build_ai_mission_prompt(mission_type, data, history, next_mission_number):
    recent_history = history[-8:]

    if mission_type == "crazy_break":
        mission_rules = """
Create a crazy break mission.
Rules:
- It must be fun, safe, and short, around 3 to 4 Hours.
- It can be about creativity,confidence.
- It must not be a study task.
- It must not require buying anything.
- skill must be exactly "Break".
- type must be exactly "crazy_break".
"""
    else:
        mission_rules = """
Create a study recommendation and mission.
Rules:
- It must match one of the user's interests.
- Use the user's knowledge to decide what they should study next.
- The topic should be the next logical step after what they already know.
- The mission must be practical and directly related to that topic.
- Avoid repeating completed missions from history.
- skill must be one of the user's interests.
- type must be exactly "study".
"""

    prompt = f"""
You are an AI mentor that creates one daily mission at a time.

User data:
{json.dumps(data, indent=2)}

Recent completed missions:
{json.dumps(recent_history, indent=2)}

Next mission number: {next_mission_number}
Mission type needed: {mission_type}

{mission_rules}

Return only valid JSON. No markdown. No explanation.
Use exactly this shape:
{{
  "skill": "AIML or Cybersecurity or Break",
  "topic": "short topic name",
  "study_reason": "one short reason why this is the right next thing",
  "mission": "one clear mission sentence related to the topic",
  "type": "study or crazy_break"
}}
"""

    return prompt


def generate_ai_mission(mission_type, data, history, next_mission_number):
    prompt = build_ai_mission_prompt(
        mission_type,
        data,
        history,
        next_mission_number
    )

    try:
        ai_response = ask_groq(prompt)
        mission = extract_json(ai_response)

        required_keys = ["skill", "topic", "study_reason", "mission", "type"]

        for key in required_keys:
            if key not in mission or not mission[key]:
                raise ValueError(f"Mission missing {key}")

        if mission_type == "crazy_break":
            mission["skill"] = "Break"
            mission["type"] = "crazy_break"
        else:
            mission["type"] = "study"

            interests = data.get("interests", []) if data else []
            if interests and mission["skill"] not in interests:
                mission["skill"] = interests[0]

        return mission

    except Exception as error:
        print("\nAI mission failed. Using fallback mission.")
        print("Reason:", error)
        return fallback_mission(mission_type, data, history)


def generate_new_mission():
    history = load_history()
    data = load_data()

    if not daily_mission_ready(history):
        show_next_unlock(history)
        return

    next_mission_number = len(history) + 1

    if next_mission_number % 5 == 0:
        mission_type = "crazy_break"
        print("\nCrazy break mission unlocked!")
    else:
        mission_type = "study"

    mission = generate_ai_mission(
        mission_type,
        data,
        history,
        next_mission_number
    )

    mission["status"] = "pending"
    mission["created_at"] = now_text()

    with open(data_path("current_mission.json"), "w") as f:
        json.dump(mission, f, indent=4)

    print("\nNew daily mission created!")
    show_mission(mission)


def show_history():
    try:
        with open(data_path("history.json"), "r") as f:
            history = json.load(f)

        print("\n=== Completed Missions ===")

        for i, mission in enumerate(history, start=1):
            print(f"\n{i}. {mission['topic']}")
            print(f"   {mission['mission']}")

    except:
        print("No history found.")


data = load_data()

if not data:
    first_time_setup()
else:
    current_mission_path = data_path("current_mission.json")

    print("\nMission file exists:", current_mission_path.exists())

    if current_mission_path.exists():
        try:
            with open(current_mission_path, "r") as f:
                mission = json.load(f)

            print("Mission status:", mission["status"])

            check_status()

        except:
            print("Mission file is empty or corrupted.")
            generate_new_mission()
    else:
        generate_new_mission()

    show_history()

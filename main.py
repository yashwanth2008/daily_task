import json
import os
from groq import Groq
from dotenv import load_dotenv
import os

load_dotenv()


client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

def ask_groq(prompt):
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    return response.choices[0].message.content

def load_data():
    try:
        with open("user_data.json", "r") as f:
            print("Found user_data.json")
            return json.load(f)
    except FileNotFoundError:
        print("user_data.json not found")
        return None

def save_data(data):
    with open("user_data.json", "w") as f:
        json.dump(data, f, indent=4)

response = ask_groq(
    "Give me one beginner AIML task."
)

print(response)
def first_time_setup():
    interests = input(
        "Enter interests (comma separated): "
    ).split(",")

    knowledge = {}

    for interest in interests:
        interest = interest.strip()

        print(f"\nWhat do you know in {interest}?")

        topics = input("> ").split(",")

        knowledge[interest] = [
            t.strip()
            for t in topics
        ]

    data = {
        "interests": interests,
        "knowledge": knowledge
    }

    save_data(data)

    return data

def generate_prompt(data):

    prompt = f"""
You are an AI mentor.

Analyze the user's knowledge.

Knowledge:
{json.dumps(data['knowledge'], indent=2)}

Find:
1. Missing concepts
2. Next logical topic
3. One practical mission

Return concise output.
"""

    return prompt

def update_knowledge(mission):

    data = load_data()

    skill = mission["skill"]
    topic = mission["topic"]

    if topic not in data["knowledge"][skill]:

        data["knowledge"][skill].append(topic)

        save_data(data)

        print(f"{topic} added to {skill}")

def complete_mission(mission):

    mission["status"] = "completed"

    print("\nMission Completed!")

    update_knowledge(mission)

    if os.path.exists("current_mission.json"):
        os.remove("current_mission.json")
    print("Current mission removed.")

    try:
        with open("history.json", "r") as f:
            history = json.load(f)
    except:
        history = []

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

    with open("history.json", "w") as f:
        json.dump(history, f, indent=4)

    generate_new_mission()    
def check_status():

    with open("current_mission.json", "r") as f:
        mission = json.load(f)

    print("\nCurrent Mission:")
    print(mission["mission"])

    completed = input(
        "\nDid you complete it? (y/n): "
    ).lower()

    if completed == "y":
        complete_mission(mission)

    else:
        print("\nKeep working on it 💪")

def generate_new_mission():

    missions = [
        {
            "skill": "Cybersecurity",
            "topic": "Linux Basics",
            "mission": "Learn ls, cd, pwd and mkdir commands"
        },
        {
            "skill": "Cybersecurity",
            "topic": "Networking Basics",
            "mission": "Learn IP Address, DNS and HTTP"
        },
        {
            "skill": "AIML",
            "topic": "Unsupervised Learning",
            "mission": "Perform K-Means clustering on Iris dataset"
        }
    ]

    try:
        with open("history.json", "r") as f:
            history = json.load(f)
    except:
        history = []

    index = len(history) % len(missions)

    mission = missions[index]
    mission["status"] = "pending"

    with open("current_mission.json", "w") as f:
        json.dump(mission, f, indent=4)

    print("\nNew mission created!")

data = load_data()

if not data:
    data = first_time_setup()

prompt = generate_prompt(data)

print("\nPrompt to send to Claude:\n")
print(prompt)

print(
    "\nMission file exists:",
    os.path.exists("current_mission.json")
)

if os.path.exists("current_mission.json"):

    try:
        with open("current_mission.json", "r") as f:
            mission = json.load(f)

        print("Mission status:", mission["status"])

        check_status()

    except:
        print("Mission file is empty or corrupted.")
        generate_new_mission()

else:
    generate_new_mission()

def show_history():

    try:
        with open("history.json", "r") as f:
            history = json.load(f)

        print("\n=== Completed Missions ===")

        for i, mission in enumerate(history, start=1):
            print(f"\n{i}. {mission['topic']}")
            print(f"   {mission['mission']}")

    except:
        print("No history found.")

show_history()
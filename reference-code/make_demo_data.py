"""Write a made-up TODOOM task list for filming the reel (no real names or messages).

Run from the repo root:  python3 data/todoom-reel/make_demo_data.py
Output: data/todoom-reel/demo-data/tasks.json (point TASK_INBOX_DATA_DIR at that folder).
"""
import datetime
import hashlib
import json
import random
from pathlib import Path

random.seed(7)
TODAY = datetime.date(2026, 10, 29)
OUT = Path("data/todoom-reel/demo-data")

# (tab, source, from, title, why)
TASKS = [
    ("work", "slack", "Priya", "Send Priya the Q4 deck", "You said 'totally, I'll send that over' on Sep 3."),
    ("work", "email", "Marcus Chen", "Reply to Marcus about the partnership", "He followed up twice. The second one just said 'bumping this'."),
    ("work", "slack", "Dana", "Review Dana's launch doc", "She tagged you in 14 comments. You reacted with the eyes emoji."),
    ("work", "email", "Finance", "Submit August expense report", "It is now October."),
    ("work", "google-docs", "Jordan", "Answer Jordan's comment on the brand guidelines", "'Thoughts on this?' -- left 3 weeks ago."),
    ("work", "slack", "Sam", "Give Sam feedback on the homepage mocks", "You said 'will look tonight' on a Tuesday."),
    ("work", "notion", "Alex", "Fill in your section of the planning doc", "Everyone else's section is done. Yours says 'TBD'."),
    ("work", "email", "Recruiting", "Write interview feedback for the designer candidate", "The candidate has since accepted another job."),
    ("work", "slack", "Leo", "Find the logo files Leo asked for", "'Do you have the SVG?' You do. Somewhere."),
    ("work", "email", "Nina Park", "Send Nina the intro you promised", "'Of course! I'll connect you two this week.'"),
    ("work", "slack", "Ops", "Renew the font license", "Expires Friday. Fonts are not free, apparently."),
    ("work", "email", "Ben", "Confirm the photoshoot date with Ben", "He's holding three dates for you. He would like one back."),
    ("work", "slack", "Maya", "Approve Maya's social posts for next week", "They go live Monday whether you approve them or not."),
    ("work", "google-docs", "Chris", "Resolve 9 open comments on the launch copy", "Chris resolved his own. Yours remain."),
    ("work", "email", "Events", "RSVP to the offsite", "You will go. You just haven't said so."),
    ("work", "slack", "Tara", "Share the retro notes", "You took the notes. Only you have the notes."),
    ("work", "email", "Legal", "Sign the vendor contract", "DocuSign has reminded you four times, each more disappointed."),
    ("work", "slack", "Omar", "Get back to Omar about the hiring plan", "'Let me think about it' -- 23 days of thinking so far."),
    ("work", "notion", "Design team", "Update the design system changelog", "Last entry: June."),
    ("work", "email", "Ruth Alvarez", "Send Ruth the case study draft", "You called it 'basically done' in a meeting."),
    ("work", "slack", "Kenji", "Pick a name for the new feature", "Kenji listed 11 options. You liked none and said so."),
    ("work", "email", "IT", "Reset your laptop password", "It expires tomorrow. Then you will be locked out of everything, including this."),
    ("work", "slack", "Ivy", "Write the newsletter intro", "Ivy needs 100 words. You have written 0."),
    ("work", "email", "Podcast team", "Send headshot and bio for the podcast", "The episode records next week. Your bio is from 2019."),
    ("work", "slack", "Grace", "Book a 1:1 with Grace", "'Let's grab time!' -- both of you said it. Neither of you did."),
    ("work", "google-docs", "Theo", "Approve the final ad scripts", "'Waiting on you' in bold."),
    ("work", "email", "Agency", "Pay the agency invoice", "Net 30. It's been 41."),
    ("work", "slack", "Hana", "Give Hana a headcount number", "She needs it for the budget. The budget is due today."),
    ("personal", "text", "Mom", "Call Mom back", "She texted 'call me when you can, nothing bad.' Three days ago."),
    ("personal", "text", "Jess", "Venmo Jess for dinner", "$48.50. She has not mentioned it, which is worse."),
    ("personal", "whatsapp", "College group", "Reply in the college group chat", "47 unread. Someone had a baby."),
    ("personal", "email", "Dentist", "Book a dentist appointment", "Your six-month cleaning is 14 months overdue."),
    ("personal", "text", "Landlord", "Send landlord photos of the leak", "'Can you send pics?' The leak has gotten bigger."),
    ("personal", "email", "DMV", "Renew your driver's license", "Expires next month. The DMV is the DMV."),
    ("personal", "text", "Alex", "Return Alex's book", "You've had it since spring. You are on page 30."),
    ("personal", "whatsapp", "Aunt Carol", "Thank Aunt Carol for the birthday card", "Your birthday was in August."),
    ("personal", "text", "Mia", "Tell Mia if you're coming Saturday", "She's ordering food tonight."),
    ("personal", "email", "Vet", "Schedule the cat's vaccines", "The cat does not know. The cat would not care."),
    ("personal", "text", "Dad", "Send Dad the photos from the trip", "He asked in July. He asked again in September."),
    ("personal", "email", "Bank", "Update your address with the bank", "You moved in March."),
    ("personal", "text", "Sophie", "Plan Sophie's surprise party", "You volunteered. Out loud. In front of people."),
    ("personal", "whatsapp", "Book club", "Finish the book club book", "Meeting is Thursday. You are on chapter 2 of 31."),
    ("personal", "email", "Insurance", "Submit the insurance claim", "There is a form. The form has a second form."),
    ("personal", "text", "Ellie", "Text Ellie back", "She sent a long, thoughtful message. You 'loved' it and left."),
    ("personal", "email", "Gym", "Cancel the gym membership", "You've paid for 9 months. You went twice."),
    ("personal", "text", "Neighbor", "Return the neighbor's ladder", "It is still in your hallway. You walk around it daily."),
    ("personal", "email", "Wedding", "RSVP to Jordan and Kai's wedding", "The card said 'kindly reply by.' That date has passed."),
    ("personal", "text", "Rosa", "Get Rosa's kid a birthday present", "The party is Sunday. You said you'd 'grab something.'"),
    ("personal", "email", "Taxes", "Find last year's tax documents", "Your accountant says 'just checking in!' with an exclamation point that is not friendly."),
    ("personal", "whatsapp", "Family", "Pick a weekend for Thanksgiving travel", "Flights get worse every day you don't."),
    ("personal", "text", "Max", "Give Max his jacket back", "You've been wearing it. He knows."),
    ("personal", "email", "Library", "Return 3 overdue library books", "The fine is now higher than the books."),
    ("personal", "text", "Plumber", "Confirm the plumber for Tuesday", "He said 'confirm by Monday or I give the slot away.'"),
    ("personal", "email", "Doctor", "Fill out the new patient forms", "Seven pages. One asks how you manage stress."),
    ("personal", "text", "Lily", "Send Lily that recipe", "'OMG yes send it!' -- you, in May."),
    ("personal", "email", "Car", "Get the car inspected", "The sticker is a different color than everyone else's now."),
    ("personal", "text", "Nora", "Reschedule coffee with Nora", "You've rescheduled four times. She's started saying 'no worries' in a tone."),
    ("personal", "email", "Subscription", "Cancel the streaming service you forgot about", "$15.99 a month for something you have never opened."),
]

SOURCE_KEYS = {"email": "gmail", "slack": "slack", "text": "imessage", "whatsapp": "whatsapp",
               "google-docs": "google-docs", "notion": "notion"}
URLS = {"email": "https://mail.google.com/", "slack": "https://slack.com/", "text": "",
        "whatsapp": "https://web.whatsapp.com/", "google-docs": "https://docs.google.com/",
        "notion": "https://notion.so/"}


def main() -> None:
    tasks = []
    for i, (tab, source, sender, title, why) in enumerate(TASKS):
        task_id = f"demo-{hashlib.sha1(title.encode()).hexdigest()[:10]}"
        sent = TODAY - datetime.timedelta(days=random.randint(1, 60))
        due = random.choice([None, None, TODAY + datetime.timedelta(days=random.randint(-20, 14))])
        tasks.append({
            "id": task_id, "tab": tab, "source": source, "source_key": SOURCE_KEYS[source],
            "title": title, "why": why, "url": URLS[source], "source_url": URLS[source],
            "due": due.isoformat() if due else None,
            "date": f"{sent.isoformat()}T{random.randint(8, 22):02d}:{random.randint(0, 59):02d}:00Z",
            "from": sender, "stale": False, "merged_ids": [], "also_from": [],
            "raw": {"source_key": SOURCE_KEYS[source], "text": why},
        })
    OUT.mkdir(parents=True, exist_ok=True)
    data = {"generated": f"{TODAY.isoformat()}T09:00:00Z", "window_days": 30, "dismissed_hidden": 0,
            "tasks": tasks, "skipped": [], "gaps": [], "sources": {}}
    (OUT / "tasks.json").write_text(json.dumps(data, indent=1))
    print(f"{len(tasks)} made-up tasks written to {OUT / 'tasks.json'}")


if __name__ == "__main__":
    main()

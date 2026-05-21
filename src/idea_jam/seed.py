"""Populate the DB with fake participants and ideas for rehearsal."""
import random
from idea_jam.db import init_db
from idea_jam import repo


SAMPLE_IDEAS = [
    "summarise my unread emails every morning",
    "watch my GitHub PRs and auto-rebase when main updates",
    "answer my mom's tech questions for me",
    "find me cheap flights to lisbon every week",
    "write weekly status updates from my calendar + commits",
    "scrape job listings from local company sites",
    "translate documents my wife sends me",
    "respond to my Airbnb guests in my voice",
    "monitor my electricity bill and warn me before peak",
    "plan a week of meals from what's in my fridge",
    "draft replies to LinkedIn recruiters",
    "track my book reading and recommend next ones",
    "summarise the city council meeting minutes",
    "find me a contractor when my furnace dies",
    "compile a weekly digest of new arxiv papers in my field",
    "build a meme out of every git commit message",
    "negotiate with my ISP when my bill goes up",
    "remind me about birthdays the day before, not the morning of",
    "find typos on my company's marketing site",
    "send me one cool thing happening in St. John's tonight",
]


def main(n: int = 20) -> None:
    init_db()
    rng = random.Random(42)
    for i in range(n):
        p = repo.create_participant()
        for text in rng.sample(SAMPLE_IDEAS, k=rng.randint(1, 3)):
            repo.add_idea(p["id"], text)
    print(f"seeded {n} participants")


if __name__ == "__main__":
    main()

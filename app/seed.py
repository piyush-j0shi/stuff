import json

from .db import db, init_db

ITEMS = [
    ("anime", "Sousou no Frieren", 2023, "Fall 2023", "finished", 28, 9.26, 980000, 4200, 18000,
     "An elf mage who outlives her party reflects on the human lives she once took for granted.",
     [("Crunchyroll", "https://crunchyroll.com"), ("Netflix", "https://netflix.com")],
     [("Atsumi Tanezaki", "Frieren"), ("Kana Ichinose", "Fern")], 0),
    ("anime", "Fullmetal Alchemist: Brotherhood", 2009, "Spring 2009", "finished", 64, 9.11, 3200000, 3100, 14000,
     "Two brothers search for the Philosopher's Stone to restore their bodies after a failed alchemy ritual.",
     [("Crunchyroll", "https://crunchyroll.com"), ("Hulu", "https://hulu.com")],
     [("Romi Park", "Edward Elric"), ("Rie Kugimiya", "Alphonse Elric")], 0),
    ("anime", "Steins;Gate", 2011, "Spring 2011", "finished", 24, 9.07, 2400000, 2600, 9000,
     "A self-proclaimed mad scientist discovers a way to send messages to the past, with grave consequences.",
     [("Crunchyroll", "https://crunchyroll.com")],
     [("Mamoru Miyano", "Rintarou Okabe"), ("Asami Imai", "Kurisu Makise")], 0),
    ("anime", "Re:Zero 4th Season", 2026, "Spring 2026", "airing", 19, 9.20, 271000, 9800, 30000,
     "Subaru returns by death again, facing a new arc of loss and resolve.",
     [("Crunchyroll", "https://crunchyroll.com")],
     [("Yusuke Kobayashi", "Subaru"), ("Rie Takahashi", "Emilia")], 0),
    ("anime", "One Piece", 1999, "Fall 1999", "airing", 0, 8.73, 2698000, 12000, 41000,
     "Monkey D. Luffy sails to become King of the Pirates and find the legendary One Piece.",
     [("Crunchyroll", "https://crunchyroll.com"), ("Netflix", "https://netflix.com")],
     [("Mayumi Tanaka", "Luffy")], 0),
    ("anime", "Youjo Senki II", 2026, "Summer 2026", "upcoming", 0, 0, 214000, 7100, 21000,
     "Tanya von Degurechaff returns to the front in the second season of the imperial war saga.",
     [("Crunchyroll", "https://crunchyroll.com")],
     [("Aoi Yuuki", "Tanya")], 0),
    ("anime", "Chiikawa", 2022, "Spring 2022", "airing", 0, 8.60, 22000, 3300, 8000,
     "Tiny cute creatures live small, heartwarming, occasionally harrowing daily lives.",
     [("YouTube", "https://youtube.com")], [], 0),

    ("movie", "Spirited Away", 2001, None, "finished", 125, 8.78, 1900000, 2100, 8800,
     "A girl wanders into a spirit world and must work in a bathhouse to free her parents.",
     [("Max", "https://max.com"), ("Netflix", "https://netflix.com")],
     [("Rumi Hiiragi", "Chihiro")], 0),
    ("movie", "Your Name", 2016, None, "finished", 106, 8.83, 2200000, 4000, 15000,
     "Two teenagers mysteriously swap bodies across distance and time.",
     [("Crunchyroll", "https://crunchyroll.com")],
     [("Ryunosuke Kamiki", "Taki"), ("Mone Kamishiraishi", "Mitsuha")], 0),
    ("movie", "Parasite", 2019, None, "finished", 132, 8.50, 1500000, 1900, 6000,
     "A poor family schemes to become employed by a wealthy household.",
     [("Hulu", "https://hulu.com")],
     [("Song Kang-ho", "Ki-taek")], 0),
    ("movie", "Interstellar", 2014, None, "finished", 169, 8.60, 2600000, 5200, 17000,
     "Explorers travel through a wormhole in search of a new home for humanity.",
     [("Paramount+", "https://paramountplus.com")],
     [("Matthew McConaughey", "Cooper")], 0),

    ("drama", "Crash Landing on You", 2019, None, "finished", 16, 8.70, 320000, 2400, 9100,
     "A South Korean heiress paraglides into North Korea and into the life of an army officer.",
     [("Netflix", "https://netflix.com")],
     [("Hyun Bin", "Ri Jeong-hyeok"), ("Son Ye-jin", "Yoon Se-ri")], 0),
    ("drama", "Reply 1988", 2015, None, "finished", 20, 9.00, 210000, 1500, 6200,
     "Five families in a Seoul neighborhood share warmth, growing pains, and nostalgia.",
     [("Netflix", "https://netflix.com")], [], 0),
    ("drama", "Alchemy of Souls", 2022, None, "finished", 20, 8.40, 140000, 2600, 7400,
     "A powerful sorceress trapped in a blind woman's body trains a noble heir.",
     [("Netflix", "https://netflix.com")], [], 0),

    ("manga", "Berserk", 1989, None, "airing", 0, 9.40, 640000, 3300, 12000,
     "A lone mercenary's brutal quest for vengeance in a dark medieval world.",
     [("MangaPlus", "https://mangaplus.shueisha.co.jp")],
     [], 0),
    ("manga", "One Piece (Manga)", 1997, None, "airing", 0, 9.21, 520000, 4100, 13000,
     "The original pirate epic in serialized manga form.",
     [("MangaPlus", "https://mangaplus.shueisha.co.jp")], [], 0),
    ("manga", "Vagabond", 1998, None, "on_hold", 0, 9.25, 300000, 1200, 5400,
     "A retelling of swordsman Miyamoto Musashi's path to mastery.",
     [], [], 0),

    ("manhwa", "Solo Leveling", 2018, None, "finished", 0, 8.90, 410000, 6200, 22000,
     "The weakest hunter awakens a system that lets him level up without limit.",
     [("Tappytoon", "https://tappytoon.com")], [], 0),
    ("manhwa", "Tower of God", 2010, None, "airing", 0, 8.30, 280000, 2900, 9700,
     "A boy enters a mysterious tower to chase the girl who left him behind.",
     [("Webtoon", "https://webtoons.com")], [], 0),
    ("manhwa", "Omniscient Reader", 2020, None, "airing", 0, 9.10, 230000, 3400, 11000,
     "A reader becomes the sole person who knows how the world's apocalypse novel ends.",
     [("Webtoon", "https://webtoons.com")], [], 0),

    ("webseries", "Arcane", 2021, None, "finished", 18, 9.00, 700000, 8100, 26000,
     "Two sisters fall on opposite sides of a war between twin cities.",
     [("Netflix", "https://netflix.com")],
     [("Hailee Steinfeld", "Vi"), ("Ella Purnell", "Jinx")], 0),
    ("webseries", "Stranger Things", 2016, None, "airing", 34, 8.60, 1200000, 9400, 31000,
     "Kids in a small town confront supernatural forces and secret experiments.",
     [("Netflix", "https://netflix.com")], [], 0),
    ("webseries", "The Boys", 2019, None, "airing", 32, 8.50, 900000, 7700, 24000,
     "Vigilantes take on corrupt celebrity superheroes.",
     [("Prime Video", "https://primevideo.com")], [], 0),

    ("sports", "FIFA World Cup 2026", 2026, "Summer 2026", "upcoming", 104, 0, 88000, 14000, 38000,
     "The expanded 48-team World Cup across North America.",
     [("FOX", "https://fox.com"), ("FIFA+", "https://fifa.com")], [], 0),
    ("sports", "UEFA Champions League 2025/26", 2025, None, "airing", 0, 8.20, 64000, 9000, 27000,
     "Europe's elite club football competition.",
     [("Paramount+", "https://paramountplus.com")], [], 0),
    ("sports", "NBA Finals 2025", 2025, None, "finished", 7, 8.00, 41000, 1200, 4400,
     "The championship series of the NBA season.",
     [("ESPN", "https://espn.com")], [], 0),

    ("hentai", "Sample Hentai Title", 2021, None, "finished", 2, 7.10, 30000, 800, 2600,
     "Adult animated title. Placeholder seed entry, gated behind age verification.",
     [], [], 1),
    ("adultvideo", "Sample Adult Title", 2022, None, "finished", 0, 6.80, 18000, 600, 1900,
     "Adult video catalog placeholder, gated behind age verification.",
     [], [], 1),
]

REVIEWS = {
    "Sousou no Frieren": [
        ("mira", 10, "A quiet masterpiece about time and memory. The pacing is perfect."),
        ("ken", 9, "Gorgeous animation, deeply moving without ever being loud."),
    ],
    "Solo Leveling": [
        ("hunterX", 9, "Peak power-fantasy art. The boss fights are unreal."),
    ],
    "Arcane": [
        ("vi_fan", 10, "Best video-game adaptation ever made, full stop."),
    ],
}

def run():
    init_db()
    with db() as conn:
        conn.execute("DELETE FROM review WHERE media_item_id IN "
                     "(SELECT id FROM media_item WHERE source='seed')")
        conn.execute("DELETE FROM media_cast WHERE media_item_id IN "
                     "(SELECT id FROM media_item WHERE source='seed')")
        conn.execute("DELETE FROM media_item WHERE source='seed'")

        title_to_id = {}
        for i, it in enumerate(ITEMS):
            (type_, title, year, season, air_status, units, score, members,
             tw, tm, synopsis, watch, cast, is_adult) = it
            cur = conn.execute(
                """INSERT INTO media_item
                   (type,title,year,season,air_status,units_total,score,members,
                    trend_week,trend_month,synopsis,where_to_watch,extra_json,
                    is_adult,source,source_id)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?, 'seed', ?)""",
                (type_, title, year, season, air_status, units, score, members,
                 tw, tm, synopsis, json.dumps([{"name": n, "url": u} for n, u in watch]),
                 json.dumps({}), is_adult, f"seed-{i}"),
            )
            mid = cur.lastrowid
            title_to_id[title] = mid
            for name, role in cast:
                conn.execute("INSERT OR IGNORE INTO person(name) VALUES (?)", (name,))
                pid = conn.execute("SELECT id FROM person WHERE name=?", (name,)).fetchone()[0]
                conn.execute(
                    "INSERT OR IGNORE INTO media_cast(media_item_id,person_id,role) VALUES (?,?,?)",
                    (mid, pid, role))

        for title, revs in REVIEWS.items():
            mid = title_to_id.get(title)
            if not mid:
                continue
            for author, rating, body in revs:
                conn.execute(
                    "INSERT INTO review(media_item_id,author,rating,body) VALUES (?,?,?,?)",
                    (mid, author, rating, body))

    print(f"Seeded {len(ITEMS)} media items.")

if __name__ == "__main__":
    run()

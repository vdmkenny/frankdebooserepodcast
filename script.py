import requests
import re
import sqlite3
import datetime
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

BASE_URL = "https://www.frankdeboosere.be"
DAILY_PAGE_URL = "https://www.frankdeboosere.be/home.php"
EXTRA_PAGE_URL = "https://www.frankdeboosere.be/extrapodcast/podcastalgemeen.php"
IMAGE_URL = "https://www.frankdeboosere.be/images/emoji.png"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def get_mp3_url_and_html():
    try:
        response = requests.get(DAILY_PAGE_URL, headers=HEADERS)
        response.raise_for_status()
    except Exception as e:
        print("Error fetching daily page:", e)
        return None, None
    html = response.text
    fallback_match = re.search(r'var\s+fallback\s*=\s*"([^"]+)"', html)
    fallback = fallback_match.group(1) if fallback_match else None
    now = datetime.datetime.now()
    cachekill = (
        f"{now.day}{now.hour}{now.minute}{now.second}{int(now.microsecond/1000)}"
    )
    dynamic_link = f"/alert/Alert.mp3?cachekill={cachekill}"
    dynamic_url = BASE_URL + dynamic_link
    try:
        head_resp = requests.head(dynamic_url, headers=HEADERS)
        if head_resp.status_code == 200:
            return dynamic_url, html
    except Exception as e:
        print("Error checking daily dynamic URL:", e)
    if fallback:
        fallback_url = BASE_URL + fallback
        try:
            head_resp = requests.head(fallback_url, headers=HEADERS)
            if head_resp.status_code == 200:
                return fallback_url, html
        except Exception as e:
            print("Error checking daily fallback URL:", e)
    return None, html


def get_daily_values(html):
    soup = BeautifulSoup(html, "html.parser")
    notes = ""
    normal_anchor = soup.find("a", href=lambda h: h and "gemtempNEW.php" in h)
    if normal_anchor:
        anchor_text = normal_anchor.get_text(strip=True)
        spans = normal_anchor.find_all_next("span")
        if spans and len(spans) >= 2:
            temps = " / ".join(span.get_text(strip=True) for span in spans[:2])
            notes = f"{anchor_text} {temps}"
    italic = soup.find("i")
    if italic:
        notes += "\n" + italic.get_text(" ", strip=True)
    return notes


def get_special_podcasts(html):
    soup = BeautifulSoup(html, "html.parser")
    episodes = []
    for audio in soup.find_all("audio"):
        mp3 = audio.get("src")
        prev_text = ""
        for elem in audio.previous_siblings:
            if isinstance(elem, str):
                text = elem.strip()
                if text:
                    prev_text = text
                    break
            elif elem.name == "br":
                continue
            else:
                text = elem.get_text(strip=True)
                if text:
                    prev_text = text
                    break
        if mp3 and prev_text:
            episodes.append((mp3, prev_text))
    return episodes


def init_db(db_path="episodes.db"):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS episodes (
            id INTEGER PRIMARY KEY,
            url TEXT UNIQUE,
            pub_date TEXT,
            title TEXT,
            notes TEXT
        )
    """
    )
    conn.commit()
    return conn


def add_episode(conn, url, title, pub_date, notes):
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO episodes (url, pub_date, title, notes) VALUES (?, ?, ?, ?)",
            (url, pub_date, title, notes),
        )
        conn.commit()
        print("Episode added:", title)
    except sqlite3.IntegrityError:
        print("Episode already exists, skipping:", title)


def generate_rss(conn, rss_path="podcast.xml"):
    cur = conn.cursor()
    cur.execute(
        "SELECT url, pub_date, title, notes FROM episodes ORDER BY pub_date DESC"
    )
    episodes = cur.fetchall()
    rss = ET.Element(
        "rss",
        version="2.0",
        **{"xmlns:itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd"},
    )
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = "Meer Weer Podcast met Frank Deboosere"
    ET.SubElement(channel, "link").text = BASE_URL
    ET.SubElement(channel, "description").text = (
        "Dagelijkse weer-update met Frank Deboosere"
    )

    image = ET.SubElement(channel, "image")
    ET.SubElement(image, "url").text = IMAGE_URL
    ET.SubElement(image, "title").text = "Meer Weer Podcast met Frank Deboosere"
    ET.SubElement(image, "link").text = BASE_URL
    itunes_image = ET.SubElement(channel, "itunes:image")
    itunes_image.set("href", IMAGE_URL)

    for ep in episodes:
        ep_url, ep_date, ep_title, ep_notes = ep
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = ep_title
        ET.SubElement(item, "link").text = BASE_URL
        ET.SubElement(item, "guid").text = ep_url
        ET.SubElement(item, "pubDate").text = ep_date
        try:
            dt = datetime.datetime.strptime(ep_date, "%a, %d %b %Y %H:%M:%S GMT")
            month_names = {
                1: "Januari",
                2: "Februari",
                3: "Maart",
                4: "April",
                5: "Mei",
                6: "Juni",
                7: "Juli",
                8: "Augustus",
                9: "September",
                10: "Oktober",
                11: "November",
                12: "December",
            }
            human_date = f"{dt.day} {month_names[dt.month]} {dt.year}"
        except Exception:
            human_date = ep_date
        description_text = f"Aflevering uitgezonden op {human_date}\n\n{ep_notes}"
        ET.SubElement(item, "description").text = description_text
        enclosure = ET.SubElement(item, "enclosure")
        enclosure.set("url", ep_url)
        enclosure.set("type", "audio/mpeg")
        itunes_item_image = ET.SubElement(item, "itunes:image")
        itunes_item_image.set("href", IMAGE_URL)
    tree = ET.ElementTree(rss)
    tree.write(rss_path, encoding="utf-8", xml_declaration=True)
    print(f"RSS feed generated at {rss_path}.")


def main():
    conn = init_db()

    # Process daily podcast
    daily_mp3, daily_html = get_mp3_url_and_html()
    if daily_mp3:
        daily_notes = get_daily_values(daily_html) if daily_html else ""
        now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=1)))
        pub_date = now.strftime("%a, %d %b %Y %H:%M:%S GMT")
        month_names = {
            1: "Januari",
            2: "Februari",
            3: "Maart",
            4: "April",
            5: "Mei",
            6: "Juni",
            7: "Juli",
            8: "Augustus",
            9: "September",
            10: "Oktober",
            11: "November",
            12: "December",
        }
        human_date = f"{now.day} {month_names[now.month]} {now.year}"
        daily_title = "Meer Weer " + human_date
        add_episode(conn, daily_mp3, daily_title, pub_date, daily_notes)
    else:
        print("No daily podcast MP3 found.")

    # Process special podcasts
    try:
        response = requests.get(EXTRA_PAGE_URL, headers=HEADERS)
        response.raise_for_status()
        extra_html = response.text
        extra_episodes = get_special_podcasts(extra_html)
        for mp3_url, raw_title in extra_episodes:
            # Try to extract date from title in the format "(DD maand YYYY)"
            m = re.search(r"\((\d{1,2})\s+([A-Za-z]+)\s+(\d{4})\)", raw_title)
            if m:
                day, month_str, year = m.groups()
                dutch_months = {
                    "januari": 1,
                    "februari": 2,
                    "maart": 3,
                    "april": 4,
                    "mei": 5,
                    "juni": 6,
                    "juli": 7,
                    "augustus": 8,
                    "september": 9,
                    "oktober": 10,
                    "november": 11,
                    "december": 12,
                }
                month = dutch_months.get(month_str.lower(), 1)
                dt = datetime.datetime(
                    int(year),
                    month,
                    int(day),
                    0,
                    0,
                    0,
                    tzinfo=datetime.timezone(datetime.timedelta(hours=1)),
                )
                pub_date_extra = dt.strftime("%a, %d %b %Y %H:%M:%S GMT")
            else:
                now = datetime.datetime.now(
                    datetime.timezone(datetime.timedelta(hours=1))
                )
                pub_date_extra = now.strftime("%a, %d %b %Y %H:%M:%S GMT")
            # Remove the date part from the title
            extra_title = re.sub(
                r"\s*\(\d{1,2}\s+[A-Za-z]+\s+\d{4}\)", "", raw_title
            ).strip()
            extra_notes = ""  # No additional notes for special podcasts
            add_episode(conn, mp3_url, extra_title, pub_date_extra, extra_notes)
    except Exception as e:
        print("Error processing special podcasts:", e)

    generate_rss(conn)
    conn.close()


if __name__ == "__main__":
    main()

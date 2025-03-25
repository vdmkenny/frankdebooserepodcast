import requests
import re
import sqlite3
import datetime
import xml.etree.ElementTree as ET

BASE_URL = 'https://www.frankdeboosere.be'
PAGE_URL = 'https://www.frankdeboosere.be/home.php'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
}

def get_mp3_url():
    try:
        response = requests.get(PAGE_URL, headers=HEADERS)
        response.raise_for_status()
    except Exception as e:
        print("Error fetching page:", e)
        return None

    html = response.text
    fallback_match = re.search(r'var\s+fallback\s*=\s*"([^"]+)"', html)
    fallback = fallback_match.group(1) if fallback_match else None
    now = datetime.datetime.now()
    cachekill = f"{now.day}{now.hour}{now.minute}{now.second}{int(now.microsecond/1000)}"
    dynamic_link = f"/alert/Alert.mp3?cachekill={cachekill}"
    dynamic_url = BASE_URL + dynamic_link
    try:
        head_resp = requests.head(dynamic_url, headers=HEADERS)
        if head_resp.status_code == 200:
            return dynamic_url
    except Exception as e:
        print("Error checking dynamic URL:", e)
    if fallback:
        fallback_url = BASE_URL + fallback
        try:
            head_resp = requests.head(fallback_url, headers=HEADERS)
            if head_resp.status_code == 200:
                return fallback_url
        except Exception as e:
            print("Error checking fallback URL:", e)
    return None

def init_db(db_path='episodes.db'):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS episodes (
            id INTEGER PRIMARY KEY,
            url TEXT UNIQUE,
            pub_date TEXT,
            title TEXT
        )
    ''')
    conn.commit()
    return conn

def add_episode(conn, url, title, pub_date):
    cur = conn.cursor()
    try:
        cur.execute('INSERT INTO episodes (url, pub_date, title) VALUES (?, ?, ?)', (url, pub_date, title))
        conn.commit()
        print("Aflevering toegevoegd.")
    except sqlite3.IntegrityError:
        print("Aflevering bestaat al, overslaan.")

def generate_rss(conn, rss_path='podcast.xml'):
    cur = conn.cursor()
    cur.execute('SELECT url, pub_date, title FROM episodes ORDER BY pub_date DESC')
    episodes = cur.fetchall()
    rss = ET.Element('rss', version="2.0")
    channel = ET.SubElement(rss, 'channel')
    ET.SubElement(channel, 'title').text = "Meer Weer Podcast met Frank Deboosere"
    ET.SubElement(channel, 'link').text = BASE_URL
    ET.SubElement(channel, 'description').text = "Dagelijkse weer-update met Frank Deboosere"
    for ep in episodes:
        ep_url, ep_date, ep_title = ep
        item = ET.SubElement(channel, 'item')
        ET.SubElement(item, 'title').text = ep_title
        ET.SubElement(item, 'link').text = ep_url
        ET.SubElement(item, 'guid').text = ep_url
        ET.SubElement(item, 'pubDate').text = ep_date
        ET.SubElement(item, 'description').text = f"Aflevering uitgezonden op {ep_date}"
    tree = ET.ElementTree(rss)
    tree.write(rss_path, encoding='utf-8', xml_declaration=True)
    print(f"RSS-feed gegenereerd op {rss_path}.")

def main():
    mp3_url = get_mp3_url()
    if not mp3_url:
        print("Geen MP3-bestand gevonden.")
        return
    print("Gevonden MP3 URL:", mp3_url)
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=1)))
    pub_date = now.strftime("%a, %d %b %Y %H:%M:%S GMT")
    title = "Podcast Aflevering " + now.strftime("%Y-%m-%d")
    conn = init_db()
    add_episode(conn, mp3_url, title, pub_date)
    generate_rss(conn)
    conn.close()

if __name__ == '__main__':
    main()


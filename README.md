# Meer Weer Podcast with Frank Deboosere

# TL;DR

To add this podcast to your podcast player app of choice, simply add the following rss feed:
```
 https://vdmkenny.github.io/frankdebooserepodcast/podcast.xml
```


# Project Info

Frank Deboosere publishes a short daily podcast on his website. However, there is no browsable archive of episodes, nor is there an rss feed to subscribe to. 

This project fetches the latest MP3 URL from the website daily and stores its metadata (MP3 URL, publication date, and title) in a SQLite database. An updated RSS feed is then generated and can be served via GitHub Pages.

**Important:** We do not rehost the MP3 files. The repository only stores metadata so you can add the podcast to a podcast app without visiting the website.

The only reason this project exists is for easier mobile access to the podcast, and archival.

Some older episodes were backfilled using archive.org snapshots.

## How It Works

- **script.py**: Fetches the MP3 URL, updates the SQLite database (`episodes.db`) with episode metadata, and generates an RSS feed (`podcast.xml`).
- **GitHub Actions**: The workflow defined in `.github/workflows/daily.yml` runs the script daily at 8:00 UTC and allows manual triggers.
- **GitHub Pages**: Configure GitHub Pages to serve the generated `podcast.xml` file, making it accessible to podcast apps.

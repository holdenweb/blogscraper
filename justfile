# justfile

export BLOG_ID := "496482"

scrape:
    uv run drop.py
    uv run scraper.py
    mongodump -d blogscraper

refresh:
    uv run drop.py
    mongorestore --nsInclude=blogscraper.blog_post

create: refresh
    uv run adhoc1.py
    uv run adhoc2.py
    uv run adhoc3.py
    uv run adhoc6.py
    uv run adhoc7.py
    uv run adhoc8.py
    uv run adhoc9.py
    uv run adhoc10.py
    uv run adhoc11.py
    uv run adhoc12.py
    uv run adhoc13.py

dump:
    uv run scraper.py
    mongodump -d blogscraper

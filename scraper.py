# Original code from https://medium.com/@sandyshah1990/extracting-posts-article-texts-from-blogger-blogspot-a1fc0b788f75
import requests
import dataclasses
import json
from xml.etree import ElementTree as ET
import html
from bs4 import BeautifulSoup
import os
import re
from time import sleep

from typing import Any

from db import BlogPost

# Manifest constants
BLOG_ID = os.environ["BLOG_ID"]
MAX_RESULTS = 15  # Number of posts to retrieve per page request
MAX_PAGES = 0  # Number of pages to process - zero for all pages
TAG_PAT = re.compile(r"\{(?P<prefix>.*)\}(?P<tag>.*)")  # Assists tag simplification

class DummyException(Exception):
    pass

@dataclasses.dataclass
class XMLItem:

    tag: str
    attrib: dict[str, str]
    text: str

    def __repr__(self) -> str:
        return f"<{self.short_tag} {self.attrib}>"

    @property
    def short_tag(self):
        return m['tag'] if (m := TAG_PAT.match(self.tag)) else None

    def to_dict(self) -> dict[str, Any]:
        return dict(tag=self.short_tag, attrib=self.attrib, text=self.text)


def create_entry(entry) -> dict[str, str | list[str]]:
    result = dict(links=[], categories=[])
    for e in entry:
        item = XMLItem(tag=e.tag, attrib=e.attrib, text=e.text)
        tag = item.short_tag
        item_dict = item.to_dict()  # inefficient but OK for now
        if tag == "link":
            result['links'].append(item_dict)
        elif tag == "category":
            result['categories'].append(item_dict)
        elif tag == "id":
            result['post_id'] = item_dict['text']
        else:
            result[tag] = item_dict
    return result

def fetch_posts(current_url, max_pages=MAX_PAGES):

    page_count = 0

    while current_url:
        # Define the Blogger API URL to retrieve posts with pagination

        # Send an HTTP GET request to fetch the posts
        response = requests.get(current_url)

        # Check if the request was successful
        if response.status_code == 200:
            # Parse the response as XML
            posts_xml = response.text

            # Parse the XML and extract post titles and content
            root = ET.fromstring(posts_xml)

            for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):
                entry_dict = create_entry(entry)
                yield entry_dict

            # Check if there are more pages
            current_url = None
            for el in  root.findall('{http://www.w3.org/2005/Atom}link'):
                if el.attrib['rel'] == 'next':
                    current_url = el.attrib['href']
                    break
        else:
            raise ValueError(f"Failed to retrieve posts from {current_url}.\n"
                             "Status Code: {response.status_code}")
        page_count += 1
        if max_pages and page_count >= max_pages:  # Limit for testing.
            break
        sleep(0.05)

if __name__ == '__main__':
    starting_url = f'https://www.blogger.com/feeds/{BLOG_ID}/posts/default?max-results={MAX_RESULTS}&start-index=1'

    for post_dict in fetch_posts(starting_url):
        bp = BlogPost(**post_dict)
        bp.save()

# Original code from https://medium.com/@sandyshah1990/extracting-posts-article-texts-from-blogger-blogspot-a1fc0b788f75
import requests
import dataclasses
import json
from xml.etree import ElementTree as ET
import html
from bs4 import BeautifulSoup
import os
import re

# Manifest constants
BLOG_ID = os.environ["BLOG_ID"]
MAX_RESULTS = 15  # Number of posts to retrieve per page request
MAX_PAGES = 2  # Number of pages to process - zero for all pages
TAG_PAT = re.compile(r"\{(?P<prefix>.*)\}(?P<tag>.*)")  # Allows tag simplification

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

def handle_entry(entry: ET.Element, all_posts: list[dict]):

    def efind(tag):
        return entry.find("{http://www.w3.org/2005/Atom}"+tag)

    def text_of(tag):
        return t.text if (t := efind(tag)) is not None else None

    categories = []
    links = []
    post_title = text_of("title")
    print("Post Title:", {post_title})
    for e in entry:
        if (t := e.short_tag) == 'link':
            print(t, e.attrib, e.text)

    #content_element = entry.find("{http://www.w3.org/2005/Atom}content")
    #if content_element is not None:
        ## Use BeautifulSoup to remove HTML tags and get plain text
        #soup = BeautifulSoup(content_element.text, 'html.parser')
        #post_content = soup.get_text()
        #post_content = re.sub(r'\n{2,}', '\n', post_content)
        #all_posts.append((post_title, post_content))

def save_query(query_url, status, text):
    pass

# Initialize variables
page_token = None
all_posts = []
page_count = 0

current_url = f'https://www.blogger.com/feeds/{BLOG_ID}/posts/default?max-results={MAX_RESULTS}&start-index=1'

while current_url:
    # Define the Blogger API URL to retrieve posts with pagination

    # Send an HTTP GET request to fetch the posts
    response = requests.get(current_url)
    save_query(current_url, response.status_code, response.text)

    # Check if the request was successful
    if response.status_code == 200:
        # Parse the response as XML
        posts_xml = response.text

        try:
            # Parse the XML and extract post titles and content
            root = ET.fromstring(posts_xml)

            for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):
                #handle_entry(entry, all_posts)
                links = []
                categories = []
                result = {}
                for e in entry:
                    item = XMLItem(tag=e.tag, attrib=e.attrib, text=e.text)
                    tag = item.short_tag
                    if tag == "link":
                        links.append(item)
                    elif tag == "category":
                        categories.append(item)
                    else:
                        result[tag] = item
                result['links'] = links
                result['categories'] = categories

                print(result)

            # Check if there are more pages
            current_url = None
            for el in  root.findall('{http://www.w3.org/2005/Atom}link'):
                if el.attrib['rel'] == 'next':
                    current_url = el.attrib['href']
                    break

        except DummyException as e:
            # Code to handle the exception
            print(f"An exception occurred: {e}")

    else:
        print(f"Failed to retrieve posts. Status Code: {response.status_code}")
        break
    page_count += 1
    if MAX_PAGES and page_count >= MAX_PAGES:
        break

## Save the content of each post as a text file
#for post_title, post_content in all_posts:

    #try:
        #filename = f"{post_title}.txt"
        #with open(filename, 'w', encoding='utf-8') as file:
            #file.write(post_content)
            #print(f"Saved content for '{post_title}' to {filename}")

    #except Exception as e:
            ## Code to handle the exception
            #print(f"An exception occurred: {e}")






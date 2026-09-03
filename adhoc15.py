# adhoc15.py: Attempt tp parse content with Beautiful Soup
from bs4 import BeautifulSoup
import requests

import sys
from uuid import uuid4

from db import BlogPost, PhotoImage

def fix_dashes(d):
    return {
        k.replace("-", "_"): v
        for (k, v) in d.items()
        if k not in {"title", "border", "style", "id"}
    }

count = 0

for record in BlogPost.objects.all():
    soup = BeautifulSoup(record.content_text, 'html.parser')
    for img in soup.find_all('img'):
        try:
            res = requests.get(src := img.get('src'))
            pi = PhotoImage(
                **fix_dashes(img.attrs)
            )
            pi.content_type = res.headers['content-type']
            pi.image.write(res.content)
            pi.image.close()
            pi.save()
        except Exception as e:
            print(f"post {record.id}: cannot process {src}")
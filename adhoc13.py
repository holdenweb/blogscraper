# adhoc13.py: Normalise links
import sys

from db import BlogPost

safe_to_proceed = True
for record in BlogPost.objects.all():
    if any(lk['text'] != None for lk in record.links):
        print(f"{record.id} has text in a link:\nlk.text")
        safe_to_proceed = False

# Silence is golden!
if not safe_to_proceed:
    sys.exit("Incorrect assumption: links may have text, and at least one does.")

for record in BlogPost.objects.all():
    if record.links:
        record.link_list = [lk['attrib'] for lk in record.links]
        record.links = None
        record.save()

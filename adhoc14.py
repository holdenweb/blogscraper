# adhoc14.py: Locate replies, if any, and extract them into the Replies collection
import sys

from db import BlogPost

count = 0

safe_to_proceed = True
for record in BlogPost.objects.all():
    if (rl := record.replies_link()) is None:
        print(f"Record {record.id} has no Atom replies entry.")
        safe_to_proceed = False
        count += 1

print("Items with no replies entry", count)

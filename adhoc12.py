# adhoc112.py: Normalise thumbnail field

import sys

from db import BlogPost

safe_to_proceed = True
for record in BlogPost.objects.all():
    if record.thumbnail:
        attrib = record.thumbnail['attrib']
        if (
            attrib['height'] != '72'
            or attrib['width'] != '72'
            or record.thumbnail['text'] is not None
        ):
            print(f"{record.id} has invalid attributes or text\nheight={attrib['height']}, width={attrib['width']}")
            safe_to_proceed = False
    if 'text' in record.thumbnail and record.thumbnail['text'] is not None:
        print("thumbnail has an actual value:", record.thumbnail['text'])

# Silence is golden!
if not safe_to_proceed:
    sys.exit("Incorrect assumption: thumbnail may have attributes, and at least one does.")

for record in BlogPost.objects.all():
    if record.thumbnail:
        record.thumbnail_url = attrib['url']
        record.thumbnail_text = record.thumbnail['text'] if 'text' in record.thumbnail else None
        record.thumbnail = None
        record.save()

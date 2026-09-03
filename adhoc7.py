# adhoc7.py: replace content field with simple text only
# if all documents have content of type html.
import sys

from db import BlogPost

safe_to_proceed = True

for record in BlogPost.objects.all():
    if (c := record.content) and (c['attrib'] == {'type': 'html'}):
        continue
    print(f"Document {c.id} has attrib {c['attrib']}")
    safe_to_proceed = False

if not safe_to_proceed:
    sys.exit("Halt the migration process until attributes are properly handled")

for record in BlogPost.objects.all():
    if record.content is not None:
        record.content_text = record.content['text']
        record.content = None
        record.save()

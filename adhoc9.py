# adhoc9.py: verify "title" never has attributes,
# and if so replace it with a text field.
import sys

from db import BlogPost

safe_to_proceed = True
for record in BlogPost.objects.all():
    if (t := record.title) and t['attrib'] != {'type': 'text'}:
        print(record.id, "has attributes:", t['attrib'])
        safe_to_proceed = False

# Silence is golden!
if not safe_to_proceed:
    sys.exit("Incorrect assumption: title may have attributes, and at least one does.")

for record in BlogPost.objects.all():
    if record.title:
        record.title_text = record.title['text']  # Eventually to become a DateTimeField?
        record.title = None
        record.save()

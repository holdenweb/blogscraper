# adhoc10.py: verify "published" never has attributes,
# and if so replace it with a text field.
import sys

from db import BlogPost

safe_to_proceed = True
for record in BlogPost.objects.all():
    if record.published and record.published['attrib'] != {}:
        print(record.id, "has attributes:", record.published['attrib'])
        safe_to_proceed = False

# Silence is golden!
if not safe_to_proceed:
    sys.exit("Incorrect assumption: published may have attributes, and at least one does.")

for record in BlogPost.objects.all():
    if record.published:
        record.published_date = record.published['text']  # Eventually to become a DateTimeField?
        record.published = None
        record.save()

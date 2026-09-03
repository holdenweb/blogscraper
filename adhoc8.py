# adhoc8.py: verify "total" never has attributes,
# and if so replace it with a text field.
import sys

from db import BlogPost

safe_to_proceed = True
for record in BlogPost.objects.all():
    if (t := record.total) and t['attrib'] != {}:
        print(record.id, "has attributes:", t['attrib'])
        safe_to_proceed = False

# Silence is golden!
if not safe_to_proceed:
    sys.exit("Incorrect assumption: total may have attributes, and at least one does.")

for record in BlogPost.objects.all():
    if record.total:
        record.total_text = record.total['text']  # Eventually to become a DateTimeField?
        record.total = None
        record.save()

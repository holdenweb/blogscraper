# adhoc6.py: verify "updated" never has attributes,
# and if so replace it with a text field.
import sys

from db import BlogPost

safe_to_proceed = True
for record in BlogPost.objects.all():
    if record.updated is not None and record.updated['attrib'] != {}:
        print(record.id, "has attributes:", record.updated['attrib'])
        safe_to_proceed = False

# Silence is golden!
if not safe_to_proceed:
    sys.exit("Incorrect assumption: updated may have attributes, and at least one does.")

for record in BlogPost.objects.all():
    if record.updated:
        record.updated_date = record.updated['text']  # Eventually to become a DateTimeField?
        record.updated = None
        record.save()

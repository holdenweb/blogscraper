# adhoc11.py: verify "author" never has attributes,
# and if so replace it with a text field or remove it.

import sys

from db import BlogPost

safe_to_proceed = True
for record in BlogPost.objects.all():
    if record.author and record.author['attrib'] != {}:
        print(record.id, "has attributes:", record.author['attrib'])
        safe_to_proceed = False
    if 'text' in record.author and record.author['text'] is not None:
        print("Author has an actual value!")

# Silence is golden!
if not safe_to_proceed:
    sys.exit("Incorrect assumption: author may have attributes, and at least one does.")

for record in BlogPost.objects.all():
    if record.author:
        record.author_text = record.author['text'] if 'text' in record.author else None
        record.author = None
        record.save()

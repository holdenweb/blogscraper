# Remove the categories attribute after creating cats.
# Now elided into adhoc3.

from db import BlogPost

for record in BlogPost.objects.all():
    record.categories = None
    record.save()


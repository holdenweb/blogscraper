# no_attribs.py: establish canonical post_id & remove @id,
# NOT IDEMPOTENT (like many of these scripts)
# In other words - don't run it more than once in a
# pipeline, or you'll lose the post ids!.

from db import BlogPost

tags = set()
a_tags = set()

FIELD_NAMES = [
    'updated', 'title', 'content', 'author', 'total',
]
for record in BlogPost.objects.all():
    for e in FIELD_NAMES:
            element = getattr(record, e)
                      #, record.links, record.categories:
            if element:
                tags.add(element['tag'])
                if element['attrib'] != {}:
                    a_tags.add(element['tag'])

print("All tags:", tags)
print("Tags with attributes:", a_tags)

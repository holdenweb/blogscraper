# adhoc3.py - simplify category data.

from db import BlogPost

from collections import defaultdict

counts = defaultdict(int)

for record in BlogPost.objects.all():
    if record.categories is not None:
        cats = []
        for category in record.categories:
            cat = category['attrib']['term']
            counts[cat] += 1
            cats.append(cat)
        record['cat_list'] = cats
        record.categories = None
        record.save()

print(len(counts), "terms\n")
for k in sorted(counts.keys()):
    print(f"{k}: {counts[k]}")
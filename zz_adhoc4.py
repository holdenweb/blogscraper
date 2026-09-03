# adhoc4.py: Collect categories in a simple list

from db import BlogPost

from collections import defaultdict

counts = defaultdict(int)

for record in BlogPost.objects.all():
    cats = []
    for category in record.categories:
        cat = category['attrib']['term']
        counts[cat] += 1
        cats.append(cat)

    record['cats'] = cats
    record.save()

print(len(counts), "terms\n")
for k in sorted(counts.keys()):
    print(f"{k}: {counts[k]}")
# adhoc2.py: summarise the link attribute distribution.

from db import BlogPost

from collections import defaultdict

counts = defaultdict(int)

for record in BlogPost.objects():
    for link in record.links:
        a = link['attrib']
        counts[f"{a['rel']}: {a['type']}"] += 1

print("Link analysis:")
for k, v in counts.items():
    print(f"{k}: {v}")

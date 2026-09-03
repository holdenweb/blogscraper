# adhoc1.py: ensure we can iterate over the posts.S


from db import BlogPost

count = 0
for record in BlogPost.objects():
    count += 1

print(count, "documents in all")
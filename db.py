from mongoengine import (connect, Document, DynamicDocument, DictField, IntField,
                         ListField, StringField, ObjectIdField, URLField, FileField)

connect(db="blogscraper")

class BlogPost(DynamicDocument):

    links = ListField()
    categories = ListField()
    published = DictField()
    updated = DictField()
    title = DictField()
    content = DictField()
    author = DictField()
    total = DictField()
    post_id = StringField()
    thumbnail = DictField()

    def replies_link(self):
        for link in self.link_list:
            if link['rel'] == 'replies' and link['type'] == 'application/atom+xml':
                return link

class PhotoImage(Document):
    alt = StringField()
    data_original_width = IntField()
    data_original_height = IntField()
    width = IntField()
    height = IntField()
    src = URLField()
    content_type = StringField()
    image = FileField()


if __name__ == '__main__':
    assert fix_dashes({"a-b-c": 123}) == {"a_b_c": 123,}
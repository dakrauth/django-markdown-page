from django.contrib.syndication.feeds import Feed
from django.utils.feedgenerator import Atom1Feed

from .models import MarkdownPageArchive


class AtomMarkdownPageFeed(Feed):
    feed_type = Atom1Feed
    title = 'Markdown Page RSS'
    description = 'Latest page changes'
    subtitle = description
    link = ''

    def item_title(self, item):
        return item.page.title

    def item_pubdate(self, item):
        return item.created

    def item_link(self, item):
        return item.page.get_absolute_url()

    def items(self):
        return MarkdownPageArchive.objects.all()[:25]

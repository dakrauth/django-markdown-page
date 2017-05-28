from django.conf import settings
from django.core.management.base import BaseCommand
from mdpage.models import MarkdownPageType


class Command(BaseCommand):
    help = 'Add MarkdownPageType.'
    
    def handle(self, prefix, description='', **options):
        mdpt = MarkdownPageType.objects.create(prefix=prefix, description=description)
        print(mdpt, 'created')

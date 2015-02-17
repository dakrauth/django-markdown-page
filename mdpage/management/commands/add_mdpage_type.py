from django.conf import settings
from django.core.management.base import BaseCommand
from mdpage.models import MarkdownPageType

#===============================================================================
class Command(BaseCommand):
    help = 'Add MarkdownPageType.'
    
    #---------------------------------------------------------------------------
    def handle(self, abbr, description='', **options):
        mdpt = MarkdownPageType.objects.create(abbr=abbr, description=description)
        print mdpt, 'created'
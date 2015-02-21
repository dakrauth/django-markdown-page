import re
import os
import operator
import mimetypes
from collections import defaultdict
from datetime import datetime, timedelta

from django.db import models
from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils.safestring import SafeUnicode
from django.contrib.auth.models import User

from choice_enum import ChoiceEnumeration
from taggit.managers import TaggableManager
from taggit.models import Tag, TaggedItem
from mdpage import utils


#===============================================================================
class PublishedManager(models.Manager):
    
    #---------------------------------------------------------------------------
    def get_queryset(self):
        now = datetime.now()
        return super(PublishedManager, self).get_queryset().filter(
            (models.Q(end_date__isnull=True) | models.Q(end_date__gt=now)) &
            (models.Q(pub_date__isnull=True) | models.Q(pub_date__lte=now)),
            status=self.model.Status.PUBLISHED
        )


#===============================================================================
class MarkdownPageBase(models.Model):
    
    #===========================================================================
    class Status(ChoiceEnumeration):
        PENDING   = ChoiceEnumeration.Option('PEND', 'Pending', default=True)
        PUBLISHED = ChoiceEnumeration.Option('PUB',  'Published')
        WITHDRAWN = ChoiceEnumeration.Option('GONE', 'Withdrawn')

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    pub_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(choices=Status.CHOICES, default=Status.DEFAULT, max_length=4, db_index=True)

    objects = models.Manager()
    published = PublishedManager()
    
    #===========================================================================
    class Meta:
        abstract = True


#===============================================================================
class MarkdownPageType(MarkdownPageBase):
    prefix      = models.SlugField(max_length=50, unique=True, blank=True)
    description = models.CharField(max_length=100, blank=True)
    
    #---------------------------------------------------------------------------
    def __unicode__(self):
        return self.prefix
    
    #---------------------------------------------------------------------------
    def get_absolute_url(self):
        return reverse('mdpage-listing', kwargs={'prefix': self.prefix})

    #---------------------------------------------------------------------------
    def tags(self):
        return (
            TaggedItem.tags_for(MarkdownPage)
                      .filter(markdownpage__type=self)
                      .annotate(counter=models.Count('name'))
                      .values('name', 'slug', 'counter')
        )
        
    #---------------------------------------------------------------------------
    def tagged_by(self, tag):
        return self.markdownpage_set.filter(tags__name=tag)

    #---------------------------------------------------------------------------
    def listing(self, by_tag=None):
        pages = self.tagged_by(tag) if by_tag else self.markdownpage_set.order_by('title')
        count = len(pages)
        listing = defaultdict(list)
        for page in pages:
            listing[page.title[0].upper()].append(page)

        return count, sorted(listing.items())


#===============================================================================
class MarkdownPageManager(models.Manager):
    
    use_for_related_fields = True
    
    #---------------------------------------------------------------------------
    def find(self, title):
        slug = utils.slugify(title)
        try:
            return self.get(models.Q(title=title) | models.Q(slug=slug))
        except self.model.DoesNotExist:
            return None
    
    #---------------------------------------------------------------------------
    def search(self, text):
        words = text.split()
        criteria = []
        for word in words:
            criteria.extend([
                models.Q(title__icontains=word),
                models.Q(text__icontains=word)
            ])

        criteria = [
            (models.Q(title__icontains=word) | models.Q(text__icontains=word))
            for word in words
        ]
            
        if criteria:
            return self.filter(reduce(operator.or_, criteria))
            
        return self.none()


#===============================================================================
class MarkdownPage(MarkdownPageBase):
    type    = models.ForeignKey(MarkdownPageType)
    slug    = models.SlugField(max_length=100)
    title   = models.CharField(max_length=100)
    text    = models.TextField(blank=True)
    summary = models.TextField(blank=True)
    html    = models.TextField(blank=True)
    version = models.IntegerField(default=0)
    locked  = models.DateTimeField(blank=True, null=True)

    objects = MarkdownPageManager()
    published = PublishedManager()
    tags = TaggableManager(blank=True)
    
    #===========================================================================
    class Meta:
        ordering = ('title',)
        unique_together = (('type', 'slug'), ('type', 'title'))

    #---------------------------------------------------------------------------
    def __unicode__(self):
        slug = '{}:'.format(self.type.prefix) if self.type.prefix else ''
        return '{}{}'.format(slug, self.title)

    #---------------------------------------------------------------------------
    def _reverse(self, name):
        return reverse(name, kwargs={'slug': self.slug, 'prefix': self.type.prefix})
        
    #---------------------------------------------------------------------------
    def get_absolute_url(self):
        return self._reverse('mdpage-view')
        
    #---------------------------------------------------------------------------
    def history_url(self): return self._reverse('mdpage-history')
    def text_url(self): return self._reverse('mdpage-text')
    def edit_url(self): return self._reverse('mdpage-edit')
    
    #---------------------------------------------------------------------------
    @property
    def session_key(self):
        return 'mdpage:{}'.format(self.pk)
        
    #---------------------------------------------------------------------------
    def _set_lock(self, request):
        self.locked = datetime.now() + timedelta(seconds=60*30)
        super(MarkdownPage, self).save()
        request.session[self.session_key] = self.locked.timetuple()[:6]

    #---------------------------------------------------------------------------
    def unlock(self, request):
        self.locked = None
        super(MarkdownPage, self).save()
        request.session[self.session_key] = ''
        
    #---------------------------------------------------------------------------
    def lock(self, request):
        if not self.locked:
            # if not locked, we can go ahead and lock
            self._set_lock(request)
            return False
            
        session_lock = request.session.get(self.session_key, '')
        expires = self.locked.timetuple()[:6]
        if session_lock == expires:
            # must be the original lock owner, let them pass
            return False

        now = datetime.now().timetuple()[:6]
        if now > expires:
            # uh-oh, this previous owner's lock has expired.
            self._set_lock(request)
            return False
            
        return True
        
    #---------------------------------------------------------------------------
    @property
    def safe_html(self):
        return SafeUnicode(self.html)
    
    #---------------------------------------------------------------------------
    def make_mdpage_link(self, title):
        slug = utils.slugify(title)
        return reverse('mdpage_page', kwargs={'prefix': self.type.prefix, 'slug': slug})
        
    #---------------------------------------------------------------------------
    def save(self, *args, **kws):
        if not self.slug:
            self.slug = utils.slugify(self.title)
            
        self.html = utils.mdpage_markdown(self.text, self.make_mdpage_link)
        self.version = (self.version + 1 if self.version else 1)
        self.locked = None
        user = kws.pop('user', None)
        archive = kws.pop('archive', True)
        super(MarkdownPage,self).save(*args, **kws)
        if archive:
            arc = MarkdownPageArchive.objects.create(
                page=self,
                version=self.version,
                created=self.updated,
                text=self.text,
                user_id=user.id if user else None,
            )

    #---------------------------------------------------------------------------
    @property
    def tags_str(self):
        return ', '.join([t.name for t in self.tags])
        
    #---------------------------------------------------------------------------
    @property
    def latest_archive(self):
        try:
            return self.markdownpagearchive_set.latest()
        except models.ObjectDoesNotExist:
            return None


#===============================================================================
class MarkdownPageArchive(models.Model):
    page    = models.ForeignKey(MarkdownPage)
    version = models.IntegerField()
    created = models.DateTimeField()
    text    = models.TextField(blank=True)
    user_id = models.IntegerField(blank=True, null=True)
    
    #===========================================================================
    class Meta:
        ordering = ('-created', )
        get_latest_by = 'created'

    #---------------------------------------------------------------------------
    def __unicode__(self):
        return '{} version {}'.format(self.page.title, self.version)

    #---------------------------------------------------------------------------
    def get_absolute_url(self):
        return reverse('mdpage-history', kwargs={
            'prefix': self.page.type.prefix,
            'slug': self.page.slug,
            'version': self.version
        })
        
    #---------------------------------------------------------------------------
    @property
    def safe_html(self):
        return SafeUnicode(utils.mdpage_markdown(self.text))


#-------------------------------------------------------------------------------
def upload_static_content_to(instance, filename):
    typ, enc = mimetypes.guess_type(filename)
    if typ:
        instance.type, instance.subtype = typ.split('/')
        
    if not instance.label:
        instance.label = '-'.join(filename.lower().split())

    _, ext = os.path.splitext(filename)
    if not ext:
        if typ:
            ext = mimetypes.guess_all_extensions(typ)
        else:
            ext = 'bin'
    
    if ext.startswith('.'):
        ext = ext[1:]
        
    return os.path.join('mdpage', '{}.{}'.format(instance.label, ext))


#===============================================================================
class StaticContent(models.Model):
    page        = models.ForeignKey(MarkdownPage)
    label       = models.SlugField(unique=True)
    description = models.CharField(blank=True, max_length=255)
    media       = models.FileField(upload_to=upload_static_content_to)
    type        = models.CharField(max_length=20, default='application')
    subtype     = models.CharField(max_length=50, default='octet-stream')
    created     = models.DateTimeField(auto_now_add=True)
    updated     = models.DateTimeField(auto_now=True)
    
    #---------------------------------------------------------------------------
    def __unicode__(self):
        return self.path
        
    #---------------------------------------------------------------------------
    @property
    def path(self):
        return self.media.url
        
    #---------------------------------------------------------------------------
    @property
    def mimetype(self):
        return '{}/{}'.format(self.type, self.subtype)


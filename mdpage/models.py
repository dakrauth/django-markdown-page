import os
import operator
import mimetypes
from functools import reduce
from functools import partialmethod

from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model

from choice_enum import ChoiceEnumeration
from taggit.managers import TaggableManager
from taggit.models import Tag

from .utils import slugify, mdpage_markdown
from .conf import get_settings

Q = models.Q
User = get_user_model()


class PublishedMixin:

    def published(self, **kwargs):
        now = timezone.now()
        return super().filter(
            (Q(end_date__isnull=True) | Q(end_date__gt=now)) &
            (Q(pub_date__isnull=True) | Q(pub_date__lte=now)),
            status=self.model.Status.PUBLISHED,
            **kwargs
        )

    def unpublished(self, **kwargs):
        now = timezone.now()
        query = Q(status=self.model.Status.PENDING) | (
            Q(status=self.model.Status.PUBLISHED) & (
                Q(pub_date__isnull=False, pub_date__gte=now) |
                Q(end_date__isnull=False, end_date__lte=now)
            )
        )

        return super().filter(query, **kwargs)


class PublishedQuerySet(PublishedMixin, models.QuerySet):
    pass


class MarkdownPageBase(models.Model):

    class Status(ChoiceEnumeration):
        PENDING = ChoiceEnumeration.Option('PEND', 'Pending', default=True)
        PUBLISHED = ChoiceEnumeration.Option('PUB', 'Published')
        WITHDRAWN = ChoiceEnumeration.Option('GONE', 'Withdrawn')

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    pub_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        choices=Status.CHOICES,
        default=Status.DEFAULT,
        max_length=4,
        db_index=True
    )

    class Meta:
        abstract = True

    @property
    def available(self):
        return self.pub_date or self.updated

    @property
    def is_pending(self):
        return self.status == self.Status.PENDING

    @property
    def is_withdrawn(self):
        return self.status == self.Status.WITHDRAWN

    @property
    def is_published(self):
        now = timezone.now()
        return (self.status == self.Status.PUBLISHED and (
            (self.end_date is None or self.end_date > now) and
            (self.pub_date is None or self.pub_date <= now)
        ))


class MarkdownPageType(MarkdownPageBase):
    prefix = models.SlugField(max_length=50, unique=True, blank=True)
    description = models.CharField(max_length=100, blank=True)
    show_history = models.BooleanField(default=True)
    show_recent = models.BooleanField(default=True)
    show_text = models.BooleanField(default=True)
    show_topics = models.BooleanField(default=True)

    objects = PublishedQuerySet.as_manager()

    def __str__(self):
        return self.prefix

    def _reverse(self, name):
        return reverse(f'{self.prefix}:{name}')

    get_absolute_url = partialmethod(_reverse, 'home')
    create_url = partialmethod(_reverse, 'create')

    def tags(self):
        return Tag.objects.filter(
            markdownpage__type=self
        ).annotate(count=models.Count('name')).values('name', 'slug', 'count')

    def tagged_by(self, tag):
        return self.markdownpage_set.filter(tags__name=tag)

    @property
    def settings(self):
        return get_settings(self.prefix)

    def get_setting(self, key, default=None):
        return self.settings.get(key, default)

    def listing_layout(self):
        return 'listing-{}.html'.format(self.get_setting('listing_layout'))


class PageQuerySetMixin(PublishedMixin):

    def find(self, title):
        slug = slugify(title)
        try:
            return self.get(models.Q(title=title) | models.Q(slug=slug))
        except self.model.DoesNotExist:
            return None

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


class PageQuerySet(PageQuerySetMixin, models.QuerySet):
    pass


class MarkdownPage(MarkdownPageBase):
    type = models.ForeignKey(MarkdownPageType, on_delete=models.CASCADE)
    slug = models.SlugField(max_length=100)
    title = models.CharField(max_length=100)
    text = models.TextField(blank=True)
    summary = models.TextField(blank=True)
    html = models.TextField(blank=True)

    objects = PageQuerySet.as_manager()
    tags = TaggableManager(blank=True)

    class Meta:
        ordering = ('title', )
        unique_together = (('type', 'slug'), ('type', 'title'))

    def __str__(self):
        slug = '{}:'.format(self.type.prefix) if self.type.prefix else ''
        return '{}{}'.format(slug, self.title)

    def _reverse(self, name):
        return reverse(f'{self.type.prefix}:{name}', kwargs={'slug': self.slug})

    get_absolute_url = partialmethod(_reverse, 'view')
    history_url = partialmethod(_reverse, 'history')
    text_url = partialmethod(_reverse, 'text')
    edit_url = partialmethod(_reverse, 'edit')
    upload_url = partialmethod(_reverse, 'upload')

    @property
    def session_key(self):
        return 'mdpage:{}'.format(self.pk)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)

        archive = kwargs.pop('archive', True)
        user = kwargs.pop('user', None)
        if self.pk and archive:
            MarkdownPageArchive.objects.create(
                page=self,
                user_id=user.id if user else None,
                **dict(MarkdownPage.objects.values('text').annotate(
                    created=models.F('updated')
                ).get(pk=self.pk))
            )

        self.html = mdpage_markdown(self.text, self.type)
        super().save(*args, **kwargs)

    @property
    def tags_str(self):
        return ', '.join([t.name for t in self.tags])

    @property
    def latest_archive(self):
        try:
            return self.markdownpagearchive_set.latest()
        except models.ObjectDoesNotExist:
            return None


class MarkdownPageArchive(models.Model):
    page = models.ForeignKey(MarkdownPage, on_delete=models.CASCADE)
    created = models.DateTimeField()
    text = models.TextField(blank=True)
    user_id = models.IntegerField(blank=True, null=True)

    class Meta:
        ordering = ('-created', )
        get_latest_by = 'created'

    def __str__(self):
        return '{:%b %d, %y %H:%M %Z}'.format(self.created)

    @property
    def author(self):
        return User.objects.get(pk=self.user_id) if self.user_id else None

    def get_absolute_url(self):
        return reverse(f'{self.page.type.prefix}:history-version', kwargs={
            'slug': self.page.slug,
            'version': self.pk
        })


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


class StaticContent(models.Model):
    page = models.ForeignKey(MarkdownPage, on_delete=models.CASCADE)
    label = models.SlugField(unique=True)
    description = models.CharField(blank=True, max_length=255)
    media = models.FileField(upload_to=upload_static_content_to)
    type = models.CharField(max_length=20, default='application')
    subtype = models.CharField(max_length=50, default='octet-stream')
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.path

    @property
    def path(self):
        return self.media.url

    @property
    def mimetype(self):
        return '{}/{}'.format(self.type, self.subtype)

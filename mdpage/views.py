from django import http
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils.functional import cached_property
from django.core.exceptions import ImproperlyConfigured
from django.views.generic import ListView, CreateView, DetailView, UpdateView
from django.contrib.auth.mixins import UserPassesTestMixin

from . import utils
from .forms import MarkdownPageForm
from .models import MarkdownPage, MarkdownPageType, MarkdownPageArchive
from .diffpatch import DiffPatch


class Permissions:
    SUPERUSER = 4
    STAFF = 3
    AUTHENTICATED = 2
    ANONYMOUS = 1

    READ = 'read'
    WRITE = 'write'
    EXTRAS = 'extras'

    DEFAULT_LEVEL = ANONYMOUS
    LEVELS = {SUPERUSER, STAFF, AUTHENTICATED, ANONYMOUS}
    ACTIONS = {READ, WRITE, EXTRAS}

    def __init__(self, read, write=None, extras=None):
        self.read = read
        self.extras = extras or read
        self.write = write
        if self.write is None:
            self.write = self.read if self.read is self.SUPERUSER else self.read + 1

    def __str__(self):
        return f'Auth(read={self.read}, write={self.write}, extras={self.extras})'

    def check(self, user, perm):
        if user.is_superuser:
            user_level = self.SUPERUSER
        elif user.is_staff:
            user_level = self.STAFF
        elif user.is_authenticated:
            user_level = self.AUTHENTICATED
        else:
            user_level = self.ANONYMOUS

        return user_level >= getattr(self, perm, self.SUPERUSER)


class PermissionMixin(UserPassesTestMixin):
    permission_type = None
    perm_class = Permissions

    def get_perm_class(self):
        return self.perm_class

    def get_permission_type(self):
        if self.permission_type not in self.get_perm_class().ACTIONS:
            raise ImproperlyConfigured("Missing definition of 'permission_type'")

        return self.permission_type

    @cached_property
    def perms(self):
        perm_class = self.get_perm_class()
        perms = self.kwargs.get('perms', perm_class.DEFAULT_LEVEL)
        return perm_class(perms) if isinstance(perms, int) else perm_class(**perms)

    def test_func(self):
        return self.perms.check(self.request.user, self.get_permission_type())


class TemplateNameMixin:

    def get_template_names(self):
        if self.template_name is None:
            raise ImproperlyConfigured("Missing definition of 'template_name'")

        return utils.get_mdp_type_template_list(
            self.template_name,
            self.kwargs['prefix'],
        )


class BasePageMixin(PermissionMixin, TemplateNameMixin):
    pass


class LandingView(BasePageMixin, ListView):
    template_name = 'listing.html'
    permission_type = 'read'
    context_object_name = 'pages'

    def get_queryset(self):
        return MarkdownPage.objects.published(type__prefix=self.kwargs['prefix'])

    def get_context_data(self, **kwargs):
        mdp_type = get_object_or_404(
            MarkdownPageType.objects.published(),
            prefix=self.kwargs['prefix']
        )

        pages = self.object_list
        search = self.request.GET.get('search', '')
        if search:
            pages = pages.search(search)

        topic = self.request.GET.get('topic')
        if topic:
            pages = pages.filter(tags__name=topic)

        if self.perms.check(self.request.user, 'write'):
            pending = MarkdownPage.objects.unpublished(type__prefix=self.kwargs['prefix'])
        else:
            pending = []

        return super().get_context_data(
            object_list=pages.order_by('title'),
            mdp_type=mdp_type,
            title='Page Listing',
            search=search,
            topic=topic,
            pending=pending,
            **kwargs
        )

class PageViewMixin(BasePageMixin):

    @property
    def slug(self):
        return self.kwargs.get('slug', None)

    @cached_property
    def page(self):
        slug = self.slug
        if slug is None:
            return None

        page = get_object_or_404(
            MarkdownPage.objects.select_related('type'),
            type__prefix=self.kwargs['prefix'],
            slug=slug
        )

        if page.is_published or self.perms.check(self.request.user, 'write'):
            return page

        raise http.Http404('Page is unavailable')

    def get_object(self):
        return self.page


class PageView(PageViewMixin, DetailView):
    template_name = 'page.html'
    as_text = False
    permission_type = 'read'

    def get_context_data(self, **kwargs):
        page = self.page
        return super().get_context_data(
            mdp_type=page.type,
            title=page.title,
            page=page,
            **kwargs
        )

    def render_to_response(self, *args, **kwargs):
        if self.as_text:
            return http.HttpResponse(
                self.page.text,
                content_type="text/plain; charset=utf8"
            )

        return super().render_to_response(*args, **kwargs)


class PageHistoryView(PageView):
    template_name = 'history.html'
    permission_type = 'extras'

    def get_context_data(self, **kwargs):
        version = self.kwargs.get('version')
        if version:
            page = self.page
            archive = get_object_or_404(MarkdownPageArchive, page=page, pk=version)
            diff = DiffPatch.diff(
                archive.text, page.text,
                their_filename=f'archive-{archive.pk}', our_filename='current',
                their_ts=archive.created, our_ts=page.updated,
                context=3
            )
            kwargs.update(archive=archive, diff=diff)

        return super().get_context_data(**kwargs)


class PageFormViewMixin(PageViewMixin):
    model = MarkdownPage
    form_class = MarkdownPageForm
    context_object_name = 'page'
    permission_type = 'write'

    def get_form_kwargs(self):
        mdp_type = get_object_or_404(
            MarkdownPageType.objects.published(),
            prefix=self.kwargs['prefix']
        )
        kwargs = super().get_form_kwargs()
        kwargs.update(request=self.request, mdp_type=mdp_type)
        return kwargs


class NewPageView(PageFormViewMixin, CreateView):
    template_name = 'edit.html'


class PageEditView(PageFormViewMixin, UpdateView):
    template_name = 'edit.html'



def view(request, *args, **kwargs):
    return http.JsonResponse({
        'title': 'needs work',
        'url': request.path,
        'args': args,
        'kwargs': kwargs,
    })

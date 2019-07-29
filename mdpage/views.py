from django import http
from django.conf import settings
from django.utils.functional import cached_property
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required

from .models import MarkdownPage, MarkdownPageType
from .forms import MarkdownPageForm, ContentForm
from .utils import get_mdp_type_template_list

@login_required
def _mdpage_new_page(request, vh, title):
    vh.page = MarkdownPage(type=vh.mdp_type, title=title)
    if request.POST:
        form = MarkdownPageForm(request.POST, instance=vh.page)
        if form.is_valid():
            page = form.save(request)
            return http.HttpResponseRedirect(self.page.get_absolute_url())
    else:
        form = MarkdownPageForm(instance=vh.page)

    return vh.render('edit.html', form=form)


class ViewHandler(object):

    def __init__(self, request, prefix, slug=None, raise_404=True):
        self.request = request
        self.mdp_type = get_object_or_404(MarkdownPageType.published, prefix=prefix)
        self.slug = slug
        self.raise_404 = raise_404

    @cached_property
    def page(self):
        if self.slug:
            try:
                return MarkdownPage.published.get(type=self.mdp_type, slug=self.slug)
            except MarkdownPage.DoesNotExist:
                if self.raise_404:
                    raise http.Http404

        return None

    def render(self, tmpl_part, **kws):
        kws.update(
            mdp_type=self.mdp_type,
            page=self.page,
            DEBUG=settings.DEBUG
        )

        template_list = get_mdp_type_template_list(self.mdp_type, tmpl_part)
        return render(self.request, template_list, kws)

    def redirect(self):
        return http.HttpResponseRedirect(self.page.get_absolute_url())

    def home_new(self, title):
        title = title or ''
        self.page = self.mdp_type.markdownpage_set.find(title)
        if self.page:
            return self.redirect()

        return _mdpage_new_page(self.request, self, title)

    def home_search(self, search):
        return self.render('search.html',
            pages=self.mdp_type.markdownpage_set.search(search),
            search=search
        )

    def home_listing(self, *args):
        return self.render('home/base.html',
            pages=self.mdp_type.markdownpage_set.order_by('title'),
            title='Page Listing'
        )

    def home_topic(self, tag):
        return self.render('home/base.html',
            pages=self.mdp_type.tagged_by(tag).order_by('title') if tag else [],
            title='Pages for topic "{}"'.format(tag),
            tag=tag
        )


################################################################################


def mdpage_home(request, prefix):
    vh = ViewHandler(request, prefix)
    for key in ('search', 'new', 'topic', 'listing'):
        if key in request.GET:
            func = getattr(vh, 'home_{}'.format(key))
            return func(request.GET.get(key))

    home_slug = vh.mdp_type.get_setting('home_slug')
    if home_slug is not None:
        if vh.page:
            return vh.render('page.html')

    return vh.home_listing(None)


def mdpage_history(request, prefix, slug, version=None):
    vh = ViewHandler(request, prefix, slug)
    arc = None if version is None else vh.page.markdownpagearchive_set.get(version=version)
    return vh.render('history.html', archive=arc)


def mdpage_view(request, prefix, slug):
    vh = ViewHandler(request, prefix, slug)
    if vh.page:
        return vh.render('page.html')

    if not request.user.is_authenticated:
        raise http.Http404('Page not found')

    return _mdpage_new_page(request, vh, slug.capitalize())


def mdpage_text(request, prefix, slug):
    vh = ViewHandler(request, prefix, slug)
    return http.HttpResponse(vh.page.text, content_type="text/plain; charset=utf8")


def mdpage_attach(request, prefix, slug):
    vh = ViewHandler(request, prefix, slug)
    if request.method == 'POST':
        form = ContentForm(request.POST, request.FILES)
        if form.is_valid():
            form.save(vh.page)
            return vh.redirect()
    else:
        form =  ContentForm()

    return vh.render('attach.html', form=form)


def mdpage_edit(request, prefix, slug):
    vh = ViewHandler(request, prefix, slug)
    if request.method == 'POST':
        if 'cancel' in request.POST:
            vh.page.unlock(request)
            return vh.redirect()

        form = MarkdownPageForm(request.POST, instance=vh.page)
        if form.is_valid():
            form.save(request)
            return vh.redirect()
    else:
        if vh.page.lock(request):
            vh.page.unlock(request)
            # return mdpage_render(request, 'locked.html', mdp_type, data)

        form = MarkdownPageForm(instance=vh.page)

    return vh.render('edit.html', form=form)



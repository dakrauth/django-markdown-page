from functools import wraps
from collections import defaultdict
from django import http
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from taggit.utils import parse_tags

from .settings import get_mdpage_setting
from .models import MarkdownPage, MarkdownPageType
from .forms import MarkdownPageForm, ContentForm


#-------------------------------------------------------------------------------
def get_page(prefix, slug, raise_404=True):
    mdp_type = get_object_or_404(MarkdownPageType.published, prefix=prefix)
    try:
        page = MarkdownPage.published.get(type=mdp_type, slug=slug)
    except MarkdownPage.DoesNotExist:
        if raise_404:
            raise http.Http404
        
        page = None
        
    return mdp_type, page


#-------------------------------------------------------------------------------
def mdpage_render(request, tmpl_part, mdp_type, **kws):
    kws.update(mdp_type=mdp_type)
    template_list = [
        'mdpage/types/{}/{}'.format(mdp_type.prefix or '__root__', tmpl_part),
        'mdpage/{}'.format(tmpl_part)
    ]
    return render(request, template_list, kws)


#-------------------------------------------------------------------------------
def page_redirect(page):
    return http.HttpResponseRedirect(page.get_absolute_url())


#-------------------------------------------------------------------------------
def _listing(pages):
    count = len(pages)
    listing = defaultdict(list)
    for page in pages:
        listing[page.title[0].upper()].append(page)
    
    return count, sorted(listing.items())


#-------------------------------------------------------------------------------
def _mdpage_list_tags(request, mdp_type, **opts):
    tag = opts.get('tag')
    if tag:
        count, listing = _listing(mdp_type.tagged_by(tag))
    else:
        count, listing = 0, []

    return mdpage_render(request, 'home.html', mdp_type,
        listing=listing,
        count=count,
        title='Pages for topic "{}"'.format(tag)
    )


#-------------------------------------------------------------------------------
def mdpage_edit(request, prefix, slug):
    mdp_type, page = get_page(prefix, slug)
    if request.method == 'POST':
        if 'cancel' in request.POST:
            page.unlock(request)
            return page_redirect(page)
            
        form =  MarkdownPageForm(request.POST, instance=page)
        if form.is_valid():
            return page_redirect(form.save(request))
    else:
        if page.lock(request):
            page.unlock(request)
            # return mdpage_render(request, 'locked.html', mdp_type, data)
            
        form = MarkdownPageForm(instance=page)

    return mdpage_render(request, 'edit.html', mdp_type, page=page, form=form)


#-------------------------------------------------------------------------------
@login_required
def _mdpage_new_page(request, mdp_type, title):
    page = MarkdownPage(type=mdp_type, title=title)
    if request.POST:
        form = MarkdownPageForm(request.POST, instance=page)
        if form.is_valid():
            return page_redirect(form.save(request))
    else:
        form = MarkdownPageForm(instance=page)
    
    return mdpage_render(request, 'edit.html', mdp_type, page=page, form=form)


#-------------------------------------------------------------------------------
def _mdpage_get_or_create_page(request, mdp_type, **opts):
    title = opts.get('new', '')
    page = mdp_type.markdownpage_set.find(title)
    if page:
        return page_redirect(page)

    return _mdpage_new_page(request, mdp_type, title)


#-------------------------------------------------------------------------------
def _mdpage_page_listing(request, mdp_type, **opts):
    count, listing = _listing(mdp_type.markdownpage_set.order_by('title'))
    return mdpage_render(request, 'home.html', mdp_type,
        listing=listing,
        count=count,
        title='Page Listing'
    )


#-------------------------------------------------------------------------------
def _mdpage_search(request, mdp_type, **opts):
    search = request.GET.get('search')
    words = search.split()
    return mdpage_render(request, 'search.html', mdp_type,
        pages=mdp_type.markdownpage_set.search(words),
        words=words,
        search=search
    )


#-------------------------------------------------------------------------------
def _mdpage_recent_updates(request, mdp_type, **opts):
    return mdpage_render(request, 'recent.html', mdp_type,
        pages=mdp_type.markdownpage_set.order_by('-updated')
    )


HOME_OPTIONS = (
    ('search',   _mdpage_search),
    ('new',      _mdpage_get_or_create_page),
    ('recent',   _mdpage_recent_updates),
    ('tag',      _mdpage_list_tags),
)

################################################################################


#-------------------------------------------------------------------------------
def mdpage_listing(request, prefix):
    mdp_type = get_object_or_404(MarkdownPageType.published, prefix=prefix)
    for key,func in HOME_OPTIONS:
        if key in request.GET:
            return func(request, **{'mdp_type': mdp_type, key : request.GET.get(key)})

    mdp_type, page = get_page(prefix, get_mdpage_setting('home_title'), False)
    if not page:
        return _mdpage_page_listing(request, mdp_type)

    return mdpage_render(request, 'page.html', mdp_type, page=page)


#-------------------------------------------------------------------------------
def mdpage_history(request, prefix, slug, version=None):
    mdp_type, page = get_page(prefix, slug)
    archive = page.markdownpagearchive_set.get(version=version) if version is not None else None
    
    return mdpage_render(request, 'history.html', mdp_type, page=page, archive=archive)


#-------------------------------------------------------------------------------
def mdpage_view(request, prefix, slug):
    mdp_type, page = get_page(prefix, slug, False)
    if page:
        return mdpage_render(request, 'page.html', mdp_type, page=page)

    if not mdp_type or not request.user.is_authenticated():
        raise http.Http404('Page not found')
    
    return _mdpage_new_page(request, mdp_type, slug.capitalize())


#-------------------------------------------------------------------------------
def mdpage_text(request, prefix, slug):
    mdp_type, page = get_page(prefix, slug)
    return http.HttpResponse(page.text, content_type="text/plain; charset=utf8")


#-------------------------------------------------------------------------------
def mdpage_attach(request, prefix, slug):
    mdp_type, page = get_page(prefix, slug)
    if request.method == 'POST':
        form =  ContentForm(request.POST, request.FILES)
        if form.is_valid():
            form.save(page)
            return page_redirect(page)
    else:
        form =  ContentForm()

    return mdpage_render(request, 'attach.html', mdp_type, page=page, form=form)


from functools import wraps
from collections import defaultdict
from django import http
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404, render
from django.core.exceptions import PermissionDenied
from django.contrib.auth.views import login
from django.contrib.auth.decorators import login_required
from mdpage.models import MarkdownPage, MarkdownPageType, mdpage_conf
from mdpage import forms
from mdpage.auth_utils import login_user


#-------------------------------------------------------------------------------
def get_page(prefix, slug, raise_404=True):
    mdp_type = get_object_or_404(MarkdownPageType.published, prefix=prefix)
    try:
        page = MarkdownPage.published.get(type=mdp_type, slug=slug)
    except MarkdownPage.DoesNotExist:
        if raise_404:
            raise
        
        page = None
        
    return mdp_type, page


#-------------------------------------------------------------------------------
def mdpage_render(request, mdp_type, tmpl, data=None):
    return render(request, tmpl, dict(data or {}, mdp_type=mdp_type))


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
        return mdpage_render(request, mdp_type, 'mdpage/home.html', {
            'listing': listing,
            'count': count,
            'title': 'Pages for topic "{}"'.format(tag)
        })
        
    else:
        return mdpage_render(request, mdp_type, 'mdpage/tags.html', {'mdp_type': mdp_type})


#-------------------------------------------------------------------------------
def _mdpage_edit_tags(request, mdp_type, **opts):
    pages = mdp_type.markdownpage_set.order_by('title')
    if request.method == 'POST':
        pages_dict = dict([('page_%s' % p.pk, p) for p in pages])
        for key, value in request.POST.items():
            page = pages_dict[key]
            page.tags = value
        return http.HttpResponseRedirect('%s?tag-edit' % (reverse('mdpage_home'),))
            
    data = dict(pages=pages)
    return mdpage_render(request, mdp_type, 'mdpage/edit_tags.html', data)


#-------------------------------------------------------------------------------
def mdpage_edit(request, prefix, slug):
    mdp_type, page = get_page(prefix, slug)
    
    data = {'page': page}
    if request.method == 'POST':
        if 'cancel' in request.POST:
            page.unlock(request)
            return page_redirect(page)
            
        form =  forms.MarkdownPageForm(request.POST, instance=page)
        if form.is_valid():
            return page_redirect(form.save(request))
    else:
        if page.lock(request):
            page.unlock(request)
            # return mdpage_render(request, mdp_type, 'mdpage/locked.html', data)
            
        form = forms.MarkdownPageForm(instance=page)
    data['form'] = form
    return mdpage_render(request, mdp_type, 'mdpage/edit.html', data)


#-------------------------------------------------------------------------------
@login_required
def _mdpage_new_page(request, mdp_type, title):
    page = MarkdownPage(type=mdp_type, title=title)
    data = {'page': page}
    
    if request.POST:
        form = forms.MarkdownPageForm(request.POST, instance=page)
        if form.is_valid():
            return page_redirect(form.save(request))
    else:
        form = forms.MarkdownPageForm(instance=page)
    
    data['form'] = form
    return mdpage_render(request, mdp_type, 'mdpage/edit.html', data)


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
    return mdpage_render(request, mdp_type, 'mdpage/home.html', {
        'listing': listing,
        'count': count,
        'title': 'Page Listing'
    })


#-------------------------------------------------------------------------------
def _mdpage_search(request, mdp_type, **opts):
    words = request.GET['search'].split()
    return mdpage_render(request, mdp_type, 'mdpage/search.html', {
        'pages': mdp_type.markdownpage_set.search(words),
        'words': words
    })


#-------------------------------------------------------------------------------
def _mdpage_recent_updates(request, mdp_type, **opts):
    return mdpage_render(request, mdp_type, 'mdpage/recent.html', {
        'pages': mdp_type.markdownpage_set.order_by('-updated')
    })


HOME_OPTIONS = (
    ('search',   _mdpage_search),
    ('new',      _mdpage_get_or_create_page),
    ('recent',   _mdpage_recent_updates),
    ('tag',      _mdpage_list_tags),
    ('tag-edit', _mdpage_edit_tags),
    ('list',     _mdpage_page_listing),
)

################################################################################


#-------------------------------------------------------------------------------
def mdpage_listing(request, prefix):
    mdp_type = get_object_or_404(MarkdownPageType.published, prefix=prefix)
    for key,func in HOME_OPTIONS:
        if key in request.GET:
            return func(request, **{'mdp_type': mdp_type, key : request.GET.get(key)})

    mdp_type, page = get_page(prefix, mdpage_conf.home_title, False)
    if not page:
        return _mdpage_page_listing(request, mdp_type)

    return mdpage_render(request, mdp_type, 'mdpage/page.html', {
        'page': page,
        'mdp_type': mdp_type
    })


#-------------------------------------------------------------------------------
def mdpage_history(request, prefix, slug):
    mdp_type, page = get_page(prefix, slug)
    return mdpage_render(request, mdp_type, 'mdpage/history.html', {'page': page})


#-------------------------------------------------------------------------------
def mdpage_version(request, prefix, slug, version):
    mdp_type, page = get_page(prefix, slug)
    archive = page.markdownpagearchive_set.get(id=version)
    return mdpage_render(request, mdp_type, 'mdpage/history.html', {'page': page, 'archive': archive})


#-------------------------------------------------------------------------------
def mdpage_view(request, prefix, slug):
    mdp_type, page = get_page(prefix, slug, False)
    if page:
        return mdpage_render(request, mdp_type, 'mdpage/page.html', {
            'page': page,
            'mdp_type': mdp_type
        })

    if not mdp_type or not request.user.is_authenticated():
        raise http.Http404('Page not found')
    
    return _mdpage_new_page(
        request,
        get_object_or_404(MarkdownPageType, slug=prefix),
        new=slug.capitalize()
    )


#-------------------------------------------------------------------------------
def mdpage_text(request, prefix, slug):
    mdp_type, page = get_page(prefix, slug)
    return http.HttpResponse(page.text, content_type="text/plain; charset=utf8")


#-------------------------------------------------------------------------------
def mdpage_attach(request, prefix, slug):
    mdp_type, page = get_page(prefix, slug)
    if request.method == 'POST':
        form =  forms.ContentForm(request.POST, request.FILES)
        if form.is_valid():
            form.save(page)
            return page_redirect(page)
    else:
        form =  forms.ContentForm()
        
    return mdpage_render(request, mdp_type, 'mdpage/attach.html', {'page': page, 'form': form})


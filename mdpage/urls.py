from django.conf.urls import *
from mdpage import views
from mdpage.utils import superuser_required, staff_required, login_required

read_page_patterns = (
    (r'^$', views.mdpage_view, 'mdpage-view'),
)

write_page_patterns = (
    (r'^edit/$',   views.mdpage_edit,   'mdpage-edit'),
    (r'^attach/$', views.mdpage_attach, 'mdpage-attach'),
)

extra_page_patterns = (
    (r'^text/$',    views.mdpage_text,    'mdpage-text'),
    (r'^history/$', views.mdpage_history, 'mdpage-history'),
    (r'^history/(?P<version>\d+)/$', views.mdpage_history,  'mdpage-history'),
)

all_page_patterns = read_page_patterns + write_page_patterns + extra_page_patterns


#-------------------------------------------------------------------------------
def make_url(decorator, regex, func, name):
    return url(regex, decorator(func) if decorator else func, name=name)


#-------------------------------------------------------------------------------
def make_urlpatterns(read, write=None, extras=None):
    inc = []
    write = read if write is None else write
    extras = read if extras is None else extras
    for deco, patts in (
        (read,   read_page_patterns),
        (extras, extra_page_patterns),
        (write,  write_page_patterns),
    ):
        if deco:
            inc.extend([make_url(deco if callable(deco) else None, *item) for item in patts])
    
    return patterns('',
        make_url(read if callable(read) else None, r'^$', views.mdpage_listing, 'mdpage-listing'),
        url(r'^(?P<slug>[^/]+)/', include(inc)),
    )


#-------------------------------------------------------------------------------
def default_urlpatterns():
    return make_urlpatterns(read=True, write=login_required, extras=login_required)


urlpatterns = default_urlpatterns()


from django.conf.urls import *
from mdpage import views
from mdpage import utils

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
    (r'^history/(?P<version>\d+)/$', views.mdpage_version,  'mdpage-version'),
)

all_page_patterns = read_page_patterns + write_page_patterns + extra_page_patterns


#-------------------------------------------------------------------------------
def make_url(decorator, regex, func, name):
    return url(regex, decorator(func) if decorator else func, name=name)


#-------------------------------------------------------------------------------
def make_urlpatterns(decorator=None, page_patterns=None):
    page_patterns = page_patterns or all_page_patterns
    inc = [make_url(decorator, *item) for item in page_patterns]
    return patterns('',
        make_url(decorator, r'^$', views.mdpage_listing, 'mdpage-listing'),
        url(r'^(?P<slug>[^/]+)/', include(inc)),
    )


#-------------------------------------------------------------------------------
def superuser_urlpatterns(page_patterns=None):
    return make_urlpatterns(utils.superuser_required, page_patterns)


#-------------------------------------------------------------------------------
def staff_urlpatterns(page_patterns=None):
    return make_urlpatterns(utils.staff_required, page_patterns)


#-------------------------------------------------------------------------------
def authenicated_urlpatterns(page_patterns=None):
    return make_urlpatterns(utils.login_required, page_patterns)


urlpatterns = make_urlpatterns()


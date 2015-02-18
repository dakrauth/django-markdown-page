from django.conf.urls import *
from django.contrib.auth.decorators import user_passes_test
from mdpage import views


superuser_required = user_passes_test(lambda u: u.is_authenticated() and u.is_active and u.is_superuser)
staff_required = user_passes_test(lambda u: u.is_authenticated() and u.is_active and u.is_staff)


default_page_patterns = (
    (r'^$',         views.mdpage_view,     'mdpage-view'),
    (r'^edit/$',    views.mdpage_edit,     'mdpage-edit'),
    (r'^text/$',    views.mdpage_text,     'mdpage-text'),
    (r'^attach/$',  views.mdpage_attach,   'mdpage-attach'),
    (r'^history/$', views.mdpage_history,  'mdpage-history'),
    (r'^history/(?P<version>\d+)/$', views.mdpage_version,  'mdpage-version'),
)

#-------------------------------------------------------------------------------
def make_url(decorator, regex, func, name):
    return url(regex, decorator(func) if decorator else func, name=name)


#-------------------------------------------------------------------------------
def make_urls(decorator, items):
    return 


#-------------------------------------------------------------------------------
def make_urlpatterns(decorator=None, page_patterns=None):
    page_patterns = page_patterns or default_page_patterns
    inc = [make_url(decorator, *item) for item in page_patterns]
    return patterns('',
        make_url(decorator, r'^$', views.mdpage_listing, 'mdpage-listing'),
        url(r'^(?P<slug>[^/]+)/', include(inc)),
    )


#-------------------------------------------------------------------------------
def superuser_urlpatterns(page_patterns=None):
    return make_urlpatterns(superuser_required, page_patterns)


#-------------------------------------------------------------------------------
def staff_urlpatterns(page_patterns=None):
    return make_urlpatterns(staff_required, page_patterns)


urlpatterns = make_urlpatterns()


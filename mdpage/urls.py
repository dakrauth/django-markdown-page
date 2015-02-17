from django.conf.urls import *
from mdpage import views

mdpage_urlpatterns = patterns('',
    url(r'^$',         views.mdpage_view,     name='mdpage-view'),
    url(r'^edit/$',    views.mdpage_edit,     name='mdpage-edit'),
    url(r'^text/$',    views.mdpage_text,     name='mdpage-text'),
    url(r'^attach/$',  views.mdpage_attach,   name='mdpage-attach'),
    url(r'^history/$', views.mdpage_history,  name='mdpage-history'),
    url(r'^history/(?P<version>\d+)/$', views.mdpage_version,  name='mdpage-version'),
)

urlpatterns = patterns('',
    url(r'^$', views.mdpage_listing, name='mdpage-listing'),
    url(r'^(?P<slug>[^/]+)/', include(mdpage_urlpatterns)),
)

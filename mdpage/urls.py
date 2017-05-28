from django.conf.urls import *
from mdpage import views
from mdpage.utils import superuser_required, staff_required, login_required

item_url_formats = {
    'simple': r'^(?P<slug>[^/]+)/',
    'date': r'^\d{4}/\d\d?+/\d\d?/(?P<slug>[^/]+)/',
}

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

decorator_mapping = {
    'superuser': superuser_required,
    'staff':     staff_required,
    'login':     login_required,
}


#-------------------------------------------------------------------------------
def make_url(decorator, regex, func, name):
    return url(regex, decorator(func) if decorator else func, name=name)


#-------------------------------------------------------------------------------
def make_urlpatterns(read, write=None, extras=None, url_format='simple'):
    inc = []
    write = read if write is None else write
    extras = read if extras is None else extras
    
    for decorator, patts in (
        (read,   read_page_patterns),
        (extras, extra_page_patterns),
        (write,  write_page_patterns),
    ):
        if decorator:
            if decorator in decorator_mapping:
                decorator = decorator_mapping[decorator]
                
            inc.extend([
                make_url(decorator if callable(decorator) else None, *item)
                for item in patts
            ])
    
    return [
        make_url(read if callable(read) else None, r'^$', views.mdpage_home, 'mdpage-home'),
        url(item_url_formats[url_format], include(inc)),
    ]


urlpatterns = make_urlpatterns(read=True, write='login', extras='login')


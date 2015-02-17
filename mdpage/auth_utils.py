from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.utils.six.moves.urllib.parse import urlparse
from django.shortcuts import resolve_url
from django.contrib.auth.views import redirect_to_login
from django.contrib.auth import REDIRECT_FIELD_NAME

#-------------------------------------------------------------------------------
def login_user(request):
    path = request.build_absolute_uri()
    login_url = resolve_url(settings.LOGIN_URL)
    scheme, netloc = urlparse(login_url)[:2]
    current_scheme, current_netloc = urlparse(path)[:2]
    if((not scheme or scheme == current_scheme) and
       (not netloc or netloc == current_netloc)
    ):
        path = request.get_full_path()
    
    return redirect_to_login(path, login_url, REDIRECT_FIELD_NAME)

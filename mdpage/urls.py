from django.urls import path, include as include

from . import views


page_patterns = [
    # read perm required
    path('', views.PageView.as_view(), name='mdpage-view'),
    path('text/', views.PageView.as_view(as_text=True), name='mdpage-text'),

    # write perm required
    path('edit/', views.PageEditView.as_view(), name='mdpage-edit'),
    path('attach/', views.view, name='mdpage-attach'),

    # extras perm required
    path('history/', views.PageHistoryView.as_view(), name='mdpage-history'),
    path('history/<int:version>/', views.PageHistoryView.as_view(), name='mdpage-history-version'),
]


urlpatterns = [
    path('', views.LandingView.as_view(), name='mdpage-home'),
    path('_add/', views.NewPageView.as_view(), name='mdpage-create'),
    path('<slug:slug>/', include(page_patterns))
]

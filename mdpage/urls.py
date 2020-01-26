from django.urls import path, include as include

from . import views

app_name = 'mdpage'

page_patterns = [
    # read perm required
    path('', views.PageView.as_view(), name='view'),
    path('text/', views.PageView.as_view(as_text=True), name='text'),

    # write perm required
    path('edit/', views.PageEditView.as_view(), name='edit'),
    path('upload/', views.view, name='upload'),

    # extras perm required
    path('history/', views.PageHistoryView.as_view(), name='history'),
    path('history/<int:version>/', views.PageHistoryView.as_view(), name='history-version'),
]


urlpatterns = [
    path('', views.LandingView.as_view(), name='home'),
    path('_add/', views.NewPageView.as_view(), name='create'),
    path('<slug:slug>/', include(page_patterns))
]

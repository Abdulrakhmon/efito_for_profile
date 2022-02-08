from django.conf.global_settings import STATIC_ROOT
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from core.settings import STATIC_URL, MEDIA_URL, MEDIA_ROOT, DEBUG
from django.conf import urls
import debug_toolbar
from invoice.api.didox.views import DidoxLoginView, DidoxProfileView

urls.handler404 = 'administration.views.error_404_handler'
admin.site.site_header = "eFito Administration"
admin.site.site_title = "eFito Administration Portal"
admin.site.index_title = "Database management"
API_TITLE = 'API title'
API_DESCRIPTION = '...'

urlpatterns = [
    path('admin/', admin.site.urls, name='admin'),
    path('ppp/', include(('ppp.urls', 'ppp'), namespace='ppp')),
    path('didox/login/', DidoxLoginView.as_view(), name='didox_login'),
    path('didox/<slug:tin>/profile/', DidoxProfileView.as_view(), name='didox_profile'),
]

if DEBUG:
    urlpatterns += path('stats/', include(debug_toolbar.urls)),
    urlpatterns += static(MEDIA_URL, document_root=MEDIA_ROOT)
    urlpatterns += static(STATIC_URL, document_root=STATIC_ROOT)

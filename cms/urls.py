from django.conf import settings
from django.conf.urls import include
from django.contrib import admin
from django.urls import path, re_path
from django.views.generic.base import TemplateView
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework.permissions import AllowAny
from tinymce import views as tinymce_views

schema_view = get_schema_view(
    openapi.Info(title="MediaCMS API", default_version='v1', contact=openapi.Contact(url="https://mediacms.io"), x_logo={"url": "../../static/images/logo_dark.svg"}),
    public=True,
    permission_classes=(AllowAny,),
)

# refactor seriously

urlpatterns = [
    path(
        "robots.txt",
        TemplateView.as_view(template_name="robots.txt", content_type="text/plain"),
    ),
    re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    re_path(r'^swagger/$', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('docs/api/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

# When USE_IDENTITY_PROVIDERS is enabled, intercept /accounts/login/ before allauth
if getattr(settings, 'USE_IDENTITY_PROVIDERS', False):
    from files.views.auth import custom_login_view
    urlpatterns += [
        re_path(r"^accounts/login/?$", custom_login_view, name='login'),
    ]

urlpatterns += [
    re_path(r"^accounts/", include("allauth.urls")),
    re_path(r"^lti/", include("lti.urls")),
    re_path(r"^api-auth/", include("rest_framework.urls")),
    path(settings.DJANGO_ADMIN_URL, admin.site.urls),
    # Only the compressor is usable: tinymce.urls also registers filebrowser and
    # flatpages_link_list, which need django-filebrowser / flatpages (not installed).
    path("tinymce/compressor/", tinymce_views.compressor, name="tinymce-compressor"),
    re_path(r"^", include("migrationservice.urls")),
    re_path(r"^", include("users.urls")),
    re_path(r"^", include("files.urls")),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns.insert(0, re_path(r"^__debug__/", include(debug_toolbar.urls)))

admin.site.site_header = "MediaCMS Admin"
admin.site.site_title = "MediaCMS"
admin.site.index_title = "Admin"

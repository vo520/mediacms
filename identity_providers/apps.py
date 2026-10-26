from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class IdentityProvidersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'identity_providers'
    verbose_name = _("Identity Providers")

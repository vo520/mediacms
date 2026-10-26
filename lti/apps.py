from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class LtiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'lti'
    verbose_name = _("LTI 1.3 Integration")

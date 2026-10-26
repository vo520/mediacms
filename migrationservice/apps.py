from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class MigrationServiceConfig(AppConfig):
    default_auto_field = "django.db.models.AutoField"
    name = "migrationservice"
    verbose_name = _("Migration Service")

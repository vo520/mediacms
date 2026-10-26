from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _


class Page(models.Model):
    slug = models.SlugField(max_length=200, unique=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    add_date = models.DateTimeField(auto_now_add=True)
    edit_date = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Page")
        verbose_name_plural = _("Pages")

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("get_page", args=[str(self.slug)])


class TinyMCEMedia(models.Model):
    file = models.FileField(upload_to='tinymce_media/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    file_type = models.CharField(
        max_length=10,
        choices=(
            ('image', 'Image'),
            ('media', 'Media'),
        ),
    )
    original_filename = models.CharField(max_length=255)
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        verbose_name = _('TinyMCE Media')
        verbose_name_plural = _('TinyMCE Media')
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.original_filename} ({self.file_type})"

    @property
    def url(self):
        return self.file.url

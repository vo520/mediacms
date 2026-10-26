from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.forms import ImageField
from django.http import JsonResponse

from .models import TinyMCEMedia

ALLOWED_IMAGE_EXTENSIONS = ("gif", "jpeg", "jpg", "png", "webp")
MAX_IMAGE_SIZE = 5 * 1024 * 1024


def upload_image(request):
    if not (request.user.is_authenticated and request.user.is_active and request.user.is_staff and request.user.is_superuser):
        return JsonResponse({'error': 'Admin access required'}, status=403)

    if request.method == "POST":
        file_obj = request.FILES.get('file')
        if file_obj:
            if file_obj.size > getattr(settings, "TINYMCE_UPLOAD_MAX_SIZE", MAX_IMAGE_SIZE):
                return JsonResponse({'error': 'Image file too large ( > 5mb )'}, status=400)
            try:
                FileExtensionValidator(ALLOWED_IMAGE_EXTENSIONS)(file_obj)
                ImageField().clean(file_obj)
            except ValidationError:
                return JsonResponse({'error': 'Invalid image type'}, status=400)

            media = TinyMCEMedia(file=file_obj, file_type='image', original_filename=file_obj.name, user=request.user)
            media.save()

            return JsonResponse({'location': media.url})
    return JsonResponse({'error': 'Invalid request'}, status=400)

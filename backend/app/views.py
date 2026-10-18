from django.http import HttpResponse
import os
from django.conf import settings

def frontend_index(request):
    """
    Serve the frontend index.html file.
    """
    # Path to the frontend index.html
    frontend_path = os.path.join(settings.BASE_DIR, 'frontend', 'index.html')
    try:
        with open(frontend_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return HttpResponse(content, content_type='text/html')
    except FileNotFoundError:
        return HttpResponse("Frontend not found", status=404)
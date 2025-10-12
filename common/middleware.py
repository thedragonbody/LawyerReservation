import logging
import traceback
import json

from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger("common")

class GlobalRequestLoggingMiddleware(MiddlewareMixin):
    """
    Middleware برای لاگ کامل request و exception
    """

    def process_request(self, request):
        try:
            user_email = getattr(request.user, "email", "Anonymous")
            logger.info(json.dumps({
                "type": "request_start",
                "user": user_email,
                "method": request.method,
                "path": request.path,
                "query_params": request.GET.dict(),
                "body": self._get_body(request)
            }))
        except Exception as e:
            logger.error(f"Error logging request start: {e}")

    def process_response(self, request, response):
        try:
            user_email = getattr(request.user, "email", "Anonymous")
            logger.info(json.dumps({
                "type": "request_end",
                "user": user_email,
                "method": request.method,
                "path": request.path,
                "status_code": response.status_code
            }))
        except Exception as e:
            logger.error(f"Error logging request end: {e}")
        return response

    def process_exception(self, request, exception):
        try:
            user_email = getattr(request.user, "email", "Anonymous")
            logger.error(json.dumps({
                "type": "exception",
                "user": user_email,
                "method": request.method,
                "path": request.path,
                "query_params": request.GET.dict(),
                "body": self._get_body(request),
                "exception": str(exception),
                "traceback": traceback.format_exc()
            }))
        except Exception as e:
            logger.error(f"Error logging exception: {e}")
        return None

    def _get_body(self, request):
        try:
            if request.body:
                return json.loads(request.body.decode("utf-8"))
        except Exception:
            return "<unreadable body>"
        return {}
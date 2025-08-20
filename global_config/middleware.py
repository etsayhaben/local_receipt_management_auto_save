# global_config/middleware.py
from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
from core.services.ReceiptService import ReceiptService

# global_config/middleware.py
from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
from core.services.ReceiptService import ReceiptService


class JwtAuthMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # Skip OPTIONS (CORS preflight)
        if request.method == "OPTIONS":
            return None

        # Public paths
        public_paths = ["/swagger/", "/redoc/", "/api/docs/"]
        if any(request.path.startswith(path) for path in public_paths):
            return None

        # Extract Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JsonResponse(
                {"error": "Authorization header missing or invalid"}, status=401
            )

        token = auth_header.split(" ")[1]  # Extract JWT

        try:
            # Decode token
            payload = ReceiptService.decode_jwt(token)
            user_info = ReceiptService.get_user_info_from_payload(payload)
            #attaching from payload to contacts database
            request.address=payload.get("Region","")
            # ✅ Attach to request
            request.user_info = user_info
            request.company_name=payload.get("company_name", "")
            request.company_tin = payload["tin_number"]  # ← Critical: company TIN
            

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=401)

        return None
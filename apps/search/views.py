from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema
from elasticsearch import exceptions as es_exceptions
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .serializers import SearchResponseSerializer


@extend_schema(
    tags=["Search"],
    parameters=[
        OpenApiParameter("q", str, description="Terme recherché"),
        OpenApiParameter("type", str, required=False, description="Limiter à un type de contenu"),
        OpenApiParameter("page", int, required=False),
        OpenApiParameter("page_size", int, required=False),
    ],
    responses=SearchResponseSerializer,
    examples=[
        OpenApiExample(
            "Résultats mixtes",
            value={
                "count": 2,
                "page": 1,
                "page_size": 20,
                "results": [
                    {
                        "type": "artists",
                        "id": 4,
                        "slug": "aline-mwamba",
                        "title": "Aline Mwamba",
                        "image_url": "https://res.cloudinary.com/artdukivu/image/upload/v1/artists/photos/aline.jpg",
                        "score": 8.2,
                    },
                    {
                        "type": "articles",
                        "id": 12,
                        "slug": "scene-goma-2026",
                        "title": "La scène musicale de Goma en 2026",
                        "image_url": None,
                        "score": 5.1,
                    },
                ],
            },
            response_only=True,
        )
    ],
)
class SearchView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        query = request.query_params.get("q", "").strip()
        if not query:
            return Response({"count": 0, "page": 1, "page_size": 20, "results": []})

        try:
            page = int(request.query_params.get("page", 1))
            page_size = int(request.query_params.get("page_size", 20))
        except ValueError:
            return Response(
                {"detail": "Les paramètres page et page_size doivent être des nombres entiers."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        content_type = request.query_params.get("type")
        try:
            return Response(services.unified_search(query, content_type, page, page_size))
        except es_exceptions.ConnectionError:
            return Response(
                {"detail": "Le service de recherche est momentanément indisponible."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

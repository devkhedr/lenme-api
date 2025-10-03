from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
    openapi.Info(
        title="Lenme API Documentation",
        default_version="v1",
        description="Welcome to the Lenme API Documentation!",
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/lending/", include("lending.urls")),
    path("api/payment/", include("payment.urls")),
    path("docs/", schema_view.with_ui("swagger"), name="swagger-docs"),
    path("", RedirectView.as_view(pattern_name="swagger-docs", permanent=False)),
]

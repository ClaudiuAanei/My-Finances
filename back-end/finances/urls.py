from django.urls import include, path
from finances.api.views import dashboard, transactions, upload, categories
from rest_framework import routers

router = routers.DefaultRouter()
router.register(r"dashboard", dashboard.DashboardView, basename="dashboard")
router.register(r"budgets", dashboard.MonthlyBudgetSetTargetView, basename="budgets")
router.register(r"transactions", transactions.TransactionsView, basename="transactions")
router.register(r"categories", categories.CategoryViewSet, basename="categories")
router.register(r"upload", upload.UploadView, basename="upload")

urlpatterns = [
    path("", include(router.urls)),
    path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),
    path("categories/<int:pk>/limits/", categories.CategoryLimitViewSet.as_view({"get": "list", "post": "create"}), name="category-limits-list"),
    path("categories/<int:pk>/limits/<int:limit_pk>/", categories.CategoryLimitViewSet.as_view({"get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"}), name="category-limits-detail"),
]
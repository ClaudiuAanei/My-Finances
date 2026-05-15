from datetime import datetime
from rest_framework import viewsets, permissions

from finances.api.serializers.categories import CategorySerializer, CategoryLimitSerializer
from finances.selectors.categories import CategoriesSelector, CategoryLimitsSelector


class CategoryViewSet(viewsets.ModelViewSet):
    
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        selector = CategoriesSelector(user)
        year = self.request.query_params.get("year") or datetime.now().year
        month = self.request.query_params.get("month") or datetime.now().month

        try:
            selected_date = datetime(int(year), int(month), 1)
        except (TypeError, ValueError):
            selected_date = datetime.now().replace(day=1)

        return selector.get_categories_info(selected_date)
    

class CategoryLimitViewSet(viewsets.ModelViewSet):
    serializer_class = CategoryLimitSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_url_kwarg = "limit_pk"

    def get_queryset(self):
        user = self.request.user
        selector = CategoryLimitsSelector(user)

        return selector.get_category_limits(self.kwargs["pk"], self.kwargs.get("limit_pk"))
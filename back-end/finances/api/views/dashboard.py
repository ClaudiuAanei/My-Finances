from datetime import datetime
from rest_framework import mixins, permissions, viewsets
from rest_framework.response import Response
from finances.models.budget import MonthlyBudget
from finances.selectors.dashboard import DashboardSelector
from finances.api.serializers.dashboard import DashboardResponseSerializer, MonthlyBudgetTargetSerializer


class DashboardView(viewsets.ViewSet):
    queryset = MonthlyBudget.objects.all()
    serializer_class = DashboardResponseSerializer
    permission_classes = [permissions.IsAuthenticated] 

    def list(self, request):
        # Extract query parameters
        user = request.user
        transaction_type = request.query_params.get("type", "actual")
        year = request.query_params.get("year") or datetime.now().year
        month = request.query_params.get("month") or datetime.now().month

        # Validate and parse year and month
        if year and month:
            try:
                date = datetime(int(year), int(month), 1)
            except ValueError:
                return Response({"error": "Invalid year or month."}, status=400)
        else:
            date = datetime.now().replace(day=1)

        # Persist selected dashboard month in session for transactions scoping.
        request.session["selected_dashboard_date"] = date.date().isoformat()

        # Get dashboard data using the selector
        dashboard_selector = DashboardSelector(user, date)
        dashboard_data = dashboard_selector.get_dashboard_data(transaction_type=transaction_type)

        # Serialize and return the response
        serializer = DashboardResponseSerializer(dashboard_data)

        return Response(serializer.data)
    

class MonthlyBudgetSetTargetView(mixins.UpdateModelMixin, mixins.DestroyModelMixin, viewsets.ReadOnlyModelViewSet):
    queryset = MonthlyBudget.objects.all()
    serializer_class = MonthlyBudgetTargetSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "put", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return MonthlyBudget.objects.filter(user=self.request.user).order_by("-date")


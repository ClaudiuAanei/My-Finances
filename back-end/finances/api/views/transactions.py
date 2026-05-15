from rest_framework import viewsets, permissions
from rest_framework.response import Response
from finances.api.serializers.transactions import TransactionSerializer
from finances.selectors.transactions import TransactionsSelector


class TransactionsView(viewsets.ModelViewSet):
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        transactions = TransactionsSelector(user)

        # Determine if a single object is being requested by lookup key (pk).
        lookup_key = self.lookup_url_kwarg or self.lookup_field

        # If a single object is being requested by lookup key (pk), skip list filters.
        if self.kwargs.get(lookup_key) is not None:
            return transactions.get_transactions(apply_selected_budget_scope=False)

        # For list view, apply filters for date, category, and name.
        name = self.request.query_params.get("name", None) # Partial match for transaction name
        start_date = self.request.query_params.get("start_date", None) # Expected format: YYYY-MM-DD
        end_date = self.request.query_params.get("end_date", None) # Expected format: YYYY-MM-DD
        type = self.request.query_params.get("type", None) # actual or planned
        categories = self.request.query_params.getlist("categories", None) # List of category names
        category_type = self.request.query_params.get("category_type", None) # income or expense

        selected_dashboard_date = self.request.session.get("selected_dashboard_date")

        return transactions.get_transactions(
            selected_date=selected_dashboard_date,
            start_date=start_date, 
            end_date=end_date, 
            type=type, 
            categories=categories, 
            category_type=category_type,
            name=name
            )


    def list(self, request):
        transactions = self.get_queryset()
        serializer = self.serializer_class(transactions, many=True)

        return Response(serializer.data) if serializer.data else Response({"message": f"No transactions found"}, status=200)
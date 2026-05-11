from datetime import datetime
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
            return transactions.get_transactions(date=None)

        # For list view, apply filters for date, category, and name.
        year = self.request.query_params.get("year") or datetime.now().year
        month = self.request.query_params.get("month") or datetime.now().month
        category = self.request.query_params.getlist("category")
        name = self.request.query_params.get("name", None)

        try:
            date = datetime(int(year), int(month), 1)
        except (TypeError, ValueError):
            date = datetime.now()
        
        return transactions.get_transactions(date, category, name)


    def list(self, request):
        transactions = self.get_queryset()
        serializer = self.serializer_class(transactions, many=True)

        year = self.request.query_params.get("year") or datetime.now().year
        month = self.request.query_params.get("month") or datetime.now().month

        return Response(serializer.data) if serializer.data else Response({"message": f"No transactions found for {month}/{year}"}, status=200)
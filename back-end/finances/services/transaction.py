from finances.models.transactions import Transaction
from finances.models.categories import Category
from finances.services.monthly import MonthlyBudgetService
from django.db import IntegrityError

class TransactionService:
    def __init__(self, user):
        self.user = user

    def _get_or_create_monthly_budget(self, date):
        """Get or create monthly budget for the user on a given date."""
        monthly_budget, _ = MonthlyBudgetService(self.user, date).get_or_create_monthly_budget()
        return monthly_budget

    def _get_category(self, category):
        """Ensure category is a Category instance assigned to the current user."""
        if not isinstance(category, Category):
            raise ValueError("Category must be a Category object.")
        if not category.users.filter(id=self.user.id).exists():
            raise ValueError("Category must belong to the authenticated user.")
        return category

    def _normalize_field(self, value, default=""):
        """Normalize and strip a field value."""
        return (value.strip() if value else default) if isinstance(value, str) else default

    def _build_duplicate_item(self, data):
        """Build a JSON-safe duplicate item with a stable response schema."""
        category = data.get("category")
        amount = data.get("amount")

        try:
            amount_value = f"{abs(amount):.2f}" if amount is not None else None
        except (TypeError, ValueError):
            amount_value = str(amount) if amount is not None else None

        return {
            "name": self._normalize_field(data.get("name"), default="No name"),
            "type": data.get("type", "actual"),
            "amount": amount_value,
            "currency": data.get("currency"),
            "category_id": category.id if category else None,
            "category_name": category.name if category else None,
            "date": data.get("date").isoformat() if data.get("date") else None,
            "description": self._normalize_field(data.get("description"), default=""),
        }

    def create_transaction(self, validated_data):
        """Create a single transaction for the user."""
        monthly_budget = self._get_or_create_monthly_budget(validated_data["date"])
        category = self._get_category(validated_data.get("category"))
        name = self._normalize_field(validated_data.get("name"), default="No name")
        description = self._normalize_field(validated_data.get("description"), default="")

        transaction = Transaction.objects.create(
            user=self.user,
            name=name,
            amount=abs(validated_data["amount"]),
            date=validated_data["date"],
            category=category,
            type=validated_data.get("type", "actual"),
            monthly_budget=monthly_budget,
            description=description,
        )
        return transaction


    def create_many_transactions(self, transactions_data, raw_transactions_data=None):
        """
        Create multiple transactions for the user. Returns a consistent dict with
        processed_count, duplicates_count, and duplicates_data (failed rows).
        """
        created_transactions = []
        duplicates_data = []

        for index, data in enumerate(transactions_data):
            try:
                transaction = self.create_transaction(data)
                created_transactions.append(transaction)
            except IntegrityError:
                duplicates_data.append(self._build_duplicate_item(data))

        return {
            "processed_count": len(created_transactions),
            "duplicates_count": len(duplicates_data),
            "duplicates_data": duplicates_data,
        }


    def get_transactions(self, date):
        """Get all transactions for the user and the specified month."""
        transactions = Transaction.objects.filter(
            user=self.user,
            date__year=date.year,
            date__month=date.month
        ).select_related("category")
        return transactions

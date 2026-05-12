from finances.models.transactions import Transaction
from django.db import models

class TransactionsSelector:
    def __init__(self, user):
        self.user = user

    def _get_total(self, date, type=None, category_id=None, category_type=None):
        transactions = Transaction.objects.filter(user=self.user, date__year=date.year, date__month=date.month)

        if type:
            transactions = transactions.filter(type=type)
        if category_id:
            transactions = transactions.filter(category_id=category_id)
        if category_type:
            transactions = transactions.filter(category__type=category_type)

        total = transactions.aggregate(total=models.Sum("amount"))["total"] or 0
        return total

    def get_transactions(self, date, category: list | None = None, name=None):
        transactions = Transaction.objects.filter(user=self.user).select_related("category")

        if date:
            transactions = transactions.filter(date__year=date.year, date__month=date.month)

        if category:
            if isinstance(category, list):
                category = [cat.strip().lower() for cat in category]
                transactions = transactions.filter(category__name__in=category)

        if name:
            transactions = transactions.filter(name__icontains=name)

        return transactions
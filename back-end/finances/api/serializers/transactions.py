from rest_framework import serializers
from finances.models.transactions import Transaction
from finances.services.transaction import TransactionService
from finances.models.categories import Category

class TransactionSerializer(serializers.ModelSerializer):
    """
    Serializer for the Transaction model, used for creating and listing transactions.
    It includes fields for the transaction's type, amount, currency, category, date, and description.
    The create method is overridden to use the TransactionService for creating transactions, which handles
    the logic for associating transactions with monthly budgets, categories, and descriptions.
    """
    
    description = serializers.CharField(required=False, allow_blank=True)
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.none(), write_only=True)
    category_id = serializers.IntegerField(source="category.id", read_only=True)
    category_name = serializers.CharField(source="category.name", required=False, allow_null=True, read_only=True)

    class Meta:
        model = Transaction
        fields = ["id", "name", "type", "amount", "currency", "category","category_id", "category_name", "date", "description"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")

        if request and getattr(request, "user", None) and request.user.is_authenticated:
            self.fields["category"].queryset = Category.objects.filter(users=request.user)

    def validate_category(self, value):
        user = self.context["request"].user
        if not value.users.filter(id=user.id).exists():
            raise serializers.ValidationError("Selected category is not assigned to this user.")
        return value

    def create(self, validated_data):
        user = self.context["request"].user

        transaction_service = TransactionService(user)
        try:
            transaction = transaction_service.create_transaction(validated_data)
        except ValueError as exc:
            raise serializers.ValidationError({"category": str(exc)})

        return transaction
    

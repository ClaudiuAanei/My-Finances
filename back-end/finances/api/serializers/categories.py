from rest_framework import serializers
from finances.models.categories import Category, CategoryLimit
from finances.models.budget import MonthlyBudget
from finances.services.categories import CategoryService



class CategorySerializer(serializers.ModelSerializer):
    """
    Serializer for the Category model, used for creating and listing categories.
    It includes fields for the category's name, type, and associated limit information. 
    The create method is overridden to use the CategoryService for creating categories, 
    which handles the logic for associating categories with users.
    """

    limit_id = serializers.IntegerField(read_only=True)
    limit_amount = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True, read_only=True)
    limit_date = serializers.DateField(allow_null=True, read_only=True)

    class Meta:
        model = Category
        validators = []
        fields = [
            "id",
            "name",
            "type",
            "limit_id",
            "limit_amount",
            "limit_date",
        ]

    def validate_name(self, value):
        return value.strip().lower()


    def create(self, validated_data):

        user = self.context["request"].user

        category_service = CategoryService(user)
        category = category_service.create_category(**validated_data)

        return category
    

class CategoryLimitSerializer(serializers.ModelSerializer):
    """
    Serializer for the CategoryLimit model, used for creating and listing category limits.
    It includes fields for the category, monthly budget, and limit amount. The create method is
    overridden to use the CategoryService for setting category limits, which handles the logic for associating
    limits with categories and monthly budgets.
    """

    category_name = serializers.CharField(source="category.name", read_only=True)
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.none(), write_only=True)
    monthly_budget = serializers.PrimaryKeyRelatedField(queryset=MonthlyBudget.objects.none(), write_only=True)
    budget = serializers.CharField(source="monthly_budget", read_only=True)
    limit = serializers.DecimalField(source="limit_amount", max_digits=10, decimal_places=2)

    class Meta:
        model = CategoryLimit
        validators = []
        fields = [
            "id",
            "category",
            "monthly_budget",
            "category_name",
            "budget",
            "limit",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")

        if request and getattr(request, "user", None) and request.user.is_authenticated:
            self.fields["category"].queryset = Category.objects.filter(users=request.user)
            self.fields["monthly_budget"].queryset = MonthlyBudget.objects.filter(user=request.user)

    def validate_category(self, value):
        user = self.context["request"].user
        if not value.users.filter(id=user.id).exists():
            raise serializers.ValidationError("Selected category is not assigned to this user.")
        return value

    def validate_monthly_budget(self, value):
        user = self.context["request"].user
        if value.user_id != user.id:
            raise serializers.ValidationError("Selected monthly budget does not belong to this user.")
        return value


    def create(self, validated_data):
        user = self.context["request"].user
        category_id = validated_data.pop("category").id
        monthly_budget_id = validated_data.pop("monthly_budget").id
        limit = validated_data["limit_amount"]

        category_service = CategoryService(user)
        category_limit = category_service.set_category_limit(category_id, monthly_budget_id, limit)

        return category_limit

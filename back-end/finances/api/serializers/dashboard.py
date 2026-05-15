from rest_framework import serializers
from finances.models.transactions import Transaction
from finances.models.budget import MonthlyBudget


class DashboardSummarySerializer(serializers.Serializer):
    income = serializers.DecimalField(max_digits=12, decimal_places=2)
    expense = serializers.DecimalField(max_digits=12, decimal_places=2)
    balance = serializers.DecimalField(max_digits=12, decimal_places=2)


class DashboardMonthlyTargetSerializer(serializers.Serializer):
    saving_target = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True)
    current_saved = serializers.DecimalField(max_digits=12, decimal_places=2)
    remaining_to_target = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True)
    progress_percentage = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True)


class DashboardCategorySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    type = serializers.ChoiceField(choices=["income", "expense"])
    spent_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    limit_id = serializers.IntegerField(allow_null=True)
    limit_amount = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True)
    remaining = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True)
    percentage_used = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True)


class DashboardResponseSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=[choice[0] for choice in Transaction.TYPE_CHOICES])
    info = serializers.CharField()
    available_years = serializers.ListField(child=serializers.IntegerField())
    available_months = serializers.ListField(child=serializers.IntegerField())
    summary = DashboardSummarySerializer()
    monthly_status = DashboardMonthlyTargetSerializer(allow_null=True)
    categories = DashboardCategorySerializer(many=True)


class MonthlyBudgetTargetSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="date", read_only=True)
    saving_goal = serializers.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        model = MonthlyBudget
        fields = ["id", "name", "saving_goal"]

    def update(self, instance, validated_data):
        instance.saving_goal = validated_data.get("saving_goal", instance.saving_goal)
        instance.save(update_fields=["saving_goal"])
        return instance

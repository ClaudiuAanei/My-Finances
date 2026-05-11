from datetime import date
from django.contrib import admin
from finances.models.budget import MonthlyBudget
from finances.models.transactions import Transaction
from finances.models.categories import Category, CategoryLimit

# Register your models here.
class MonthlyBudgetAdmin(admin.ModelAdmin):
    list_display = ("date", "saving_goal")

    def save_model(self, request, obj, form, change):
        date = obj.date.replace(day=1)
        obj.date = date
        super().save_model(request, obj, form, change)

class TransactionAdmin(admin.ModelAdmin):
    list_display = ("user", "date", "type", "description", "amount", "currency", "category", "category__type", "monthly_budget")
    exclude = ("monthly_budget",)

    def save_model(self, request, obj, form, change):
        # Derive the first day of the transaction's month
        budget_date = date(obj.date.year, obj.date.month, 1)
        # Get or create a MonthlyBudget for this user/month
        monthly_budget, _ = MonthlyBudget.objects.get_or_create(
            user=obj.user,
            date=budget_date,
            defaults={"saving_goal": 0},
        )
        obj.monthly_budget = monthly_budget
        super().save_model(request, obj, form, change)

class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "type")
    filter_horizontal = ("users",)

    def save_model(self, request, obj, form, change):
        existing = Category.objects.filter(name__iexact=obj.name.strip(), type=obj.type).exclude(pk=obj.pk).first()
        if existing:
            # Reuse existing category and attach the selected users.
            obj.pk = existing.pk
            obj.name = existing.name
            obj.type = existing.type
            obj._state.adding = False
            obj._merge_existing = True
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        if getattr(form.instance, "_merge_existing", False):
            selected_users = form.cleaned_data.get("users")
            if selected_users:
                form.instance.users.add(*selected_users)
            if request.user.is_authenticated:
                form.instance.users.add(request.user)
            return

        super().save_related(request, form, formsets, change)
        if request.user.is_authenticated:
            form.instance.users.add(request.user)

class CategoryLimitAdmin(admin.ModelAdmin):
    list_display = ("category", "limit_amount", "monthly_budget")


admin.site.register(MonthlyBudget, MonthlyBudgetAdmin)
admin.site.register(Transaction, TransactionAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(CategoryLimit, CategoryLimitAdmin)

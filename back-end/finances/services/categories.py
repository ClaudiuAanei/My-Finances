from finances.models.categories import Category, CategoryLimit

class CategoryService:
    def __init__(self, user):
        self.user = user

    def create_category(self, name, type):
        """Create a new category for the user."""
        return Category.get_or_create_for_user(user=self.user, name=name, type=type)
        

    def set_category_limit(self, category_id, monthly_budget_id, limit_amount):
        """Set or update the limit for a category in a specific monthly budget."""
        category = Category.objects.get(id=category_id)
        category_limit, created = CategoryLimit.objects.update_or_create(
            user=self.user,
            category=category,
            monthly_budget_id=monthly_budget_id,
            defaults={"limit_amount": limit_amount},
        )
        return category_limit
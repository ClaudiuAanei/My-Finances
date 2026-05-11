from finances.models.budget import MonthlyBudget

class MonthlyBudgetService:
    def __init__(self, user, date):
        self.user = user
        self.date = date.replace(day=1)  # Ensure the date is set to the first of the month for consistency


    def get_or_create_monthly_budget(self):
        return MonthlyBudget.objects.get_or_create(
            user=self.user, 
            date__month=self.date.month, 
            date__year=self.date.year,
            date=self.date,  # Store the date as the first of the month for consistency
            defaults={"saving_goal": 0}
        )
    
    
    def update_saving_goal(self, saving_goal):
        monthly_budget = self.get_or_create_monthly_budget()[0]
        monthly_budget.saving_goal = saving_goal
        monthly_budget.save()
        return monthly_budget
    

    def get_monthly_budget(self):
        return MonthlyBudget.objects.filter(
            user=self.user, 
            date__month=self.date.month, 
            date__year=self.date.year
        ).first()

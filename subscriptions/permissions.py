from rest_framework.permissions import BasePermission


class HasActiveSubscription(BasePermission):
    message = "You need an active subscription to access this resource."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        sub = getattr(request.user, "subscription", None)
        if sub is None:
            return False
        if not sub.is_active_subscription:
            return False
        # Trial users who exhausted their free videos must upgrade
        if sub.trial_exhausted:
            self.message = (
                "Your free trial is over. You've used all 3 free video generations. "
                "Please subscribe to a paid plan to continue."
            )
            return False
        return True


class CanGenerateVideo(BasePermission):
    message = "Monthly video generation limit reached. Please upgrade your plan."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        sub = getattr(request.user, "subscription", None)
        if sub is None:
            return False
        if sub.trial_exhausted:
            self.message = (
                "Your free trial is over. You've used all 3 free video generations. "
                "Please subscribe to a paid plan to continue."
            )
            return False
        return sub.can_generate_video()


class CanGenerateScript(BasePermission):
    message = "Monthly script generation limit reached. Please upgrade your plan."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        sub = getattr(request.user, "subscription", None)
        if sub is None:
            return False
        if sub.trial_exhausted:
            self.message = (
                "Your free trial is over. Please subscribe to a paid plan to continue."
            )
            return False
        return sub.can_generate_script()


class CanRegenerateVideo(BasePermission):
    message = "Monthly regeneration limit reached. Please upgrade your plan."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        sub = getattr(request.user, "subscription", None)
        if sub is None:
            return False
        if not sub.is_active_subscription:
            self.message = "You need an active subscription to regenerate videos."
            return False
        if not sub.can_regenerate_video():
            plan_name = sub.plan.name
            limit = sub.plan.max_regenerations_per_month
            if sub.is_trial:
                self.message = (
                    f"You have used your {limit} lifetime regeneration(s) on the {plan_name} plan. "
                    "Please upgrade to a paid plan for more regenerations."
                )
            else:
                self.message = (
                    f"You have used all {limit} regeneration(s) allowed this month on the {plan_name} plan. "
                    "Regenerations reset on the 1st of each month."
                )
            return False
        return True
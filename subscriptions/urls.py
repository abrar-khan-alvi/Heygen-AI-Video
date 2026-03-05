from django.urls import path
from . import views

app_name = "subscriptions"

urlpatterns = [
    path("plans/", views.SubscriptionPlanListView.as_view(), name="plan-list"),
    path("me/", views.MySubscriptionView.as_view(), name="my-subscription"),
    path("verify-purchase/", views.VerifyIAPPurchaseView.as_view(), name="verify-purchase"),
    path("cancel/", views.CancelSubscriptionView.as_view(), name="cancel"),
]
from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import SubscriptionPlan, UserSubscription
from .serializers import (
    SubscriptionPlanSerializer,
    UserSubscriptionSerializer,
    IAPPurchaseSerializer,
)


class SubscriptionPlanListView(generics.ListAPIView):
    """
    GET /plans/ — List all plans.

    Returns free trial + paid plans with Apple/Google product IDs.
    Frontend uses apple_product_id or google_product_id to initiate IAP.
    """
    queryset = SubscriptionPlan.objects.filter(is_active=True)
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [IsAuthenticated]


class MySubscriptionView(APIView):
    """
    GET /me/ — Current subscription + usage.

    Key fields for frontend:
    - is_trial: true if on free trial
    - trial_videos_used: how many of the 3 free videos used
    - trial_exhausted: true if all 3 used (show upgrade prompt)
    - videos_remaining: videos left this month (or trial remaining)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        sub = getattr(request.user, "subscription", None)

        # Auto-assign free trial if no subscription exists
        if not sub:
            sub = _auto_assign_trial(request.user)
            if not sub:
                return Response(
                    {"detail": "No subscription found and free trial is unavailable."},
                    status=status.HTTP_404_NOT_FOUND,
                )

        return Response(UserSubscriptionSerializer(sub).data)


class VerifyIAPPurchaseView(APIView):
    """
    POST /verify-purchase/ — Frontend sends this AFTER a successful IAP.

    Flow:
    1. Frontend fetches GET /plans/ → gets apple_product_id / google_product_id
    2. Frontend initiates purchase via StoreKit / BillingClient
    3. Apple/Google processes payment → returns receipt/token
    4. Frontend sends receipt here
    5. Backend matches product_id → activates paid plan

    Body:
    {
        "platform": "apple" | "google",
        "product_id": "com.yourapp.starter_monthly",
        "purchase_token": "<receipt_data_or_token>",
        "transaction_id": "<original_transaction_id_or_order_id>"
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = IAPPurchaseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        platform = data["platform"]
        product_id = data["product_id"]
        purchase_token = data["purchase_token"]
        transaction_id = data["transaction_id"]

        # ── Match product_id to plan ────────────────────────────────────
        if platform == "apple":
            plan = SubscriptionPlan.objects.filter(
                apple_product_id=product_id, is_active=True
            ).first()
        else:
            plan = SubscriptionPlan.objects.filter(
                google_product_id=product_id, is_active=True
            ).first()

        if not plan:
            return Response(
                {"detail": f"No plan found for product_id '{product_id}' on {platform}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── TODO: Server-side receipt verification ──────────────────────
        # Apple: verify via App Store Server API
        # Google: verify via Google Play Developer API
        # ────────────────────────────────────────────────────────────────

        # ── Prevent duplicate transactions ──────────────────────────────
        existing = UserSubscription.objects.filter(
            transaction_id=transaction_id
        ).exclude(user=request.user).first()

        if existing:
            return Response(
                {"detail": "This transaction has already been used by another account."},
                status=status.HTTP_409_CONFLICT,
            )

        # ── Activate paid subscription ──────────────────────────────────
        sub, created = UserSubscription.objects.update_or_create(
            user=request.user,
            defaults={
                "plan": plan,
                "status": UserSubscription.Status.ACTIVE,
                "platform": platform,
                "product_id": product_id,
                "purchase_token": purchase_token,
                "transaction_id": transaction_id,
                # Reset monthly usage on upgrade
                "videos_generated_this_month": 0,
                "scripts_generated_this_month": 0,
            },
        )

        return Response(
            UserSubscriptionSerializer(sub).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class CancelSubscriptionView(APIView):
    """
    POST /cancel/ — Mark subscription as cancelled on backend.

    The actual IAP cancellation happens on Apple/Google side.
    Frontend cancels with store first, then calls this.
    User falls back to exhausted trial (no more videos).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        sub = getattr(request.user, "subscription", None)
        if not sub:
            return Response(
                {"detail": "No active subscription to cancel."},
                status=status.HTTP_404_NOT_FOUND,
            )
        sub.status = UserSubscription.Status.CANCELLED
        sub.save(update_fields=["status"])
        return Response({"detail": "Subscription cancelled successfully."})


# ── Helper: Auto-assign free trial to new users ─────────────────────────────

def _auto_assign_trial(user):
    """
    Automatically assigns the free trial plan to a new user.
    Called on first GET /me/ if no subscription exists.
    """
    trial_plan = SubscriptionPlan.objects.filter(
        plan_type=SubscriptionPlan.PlanType.FREE_TRIAL, is_active=True
    ).first()

    if not trial_plan:
        return None

    sub = UserSubscription.objects.create(
        user=user,
        plan=trial_plan,
        status=UserSubscription.Status.TRIAL,
        platform=UserSubscription.Platform.NONE,
    )
    return sub
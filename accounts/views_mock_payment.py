
# =============================================================================
# MOCK PAYMENT SYSTEM (For Flutter Dev)
# =============================================================================

class MockPaymentView(APIView):
    """
    Simulate a payment/upgrade.
    
    POST /api/v1/auth/mock-payment/
    
    Request body:
    {
        "tier": "Standard"  // or "Premium"
    }
    
    Logic:
    - Updates user tier
    - Adds credits based on tier
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        tier_name = request.data.get('tier')
        
        if tier_name not in ['Standard', 'Premium']:
            return Response(
                {'error': 'Invalid tier. Choose Standard or Premium.'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        user = request.user
        
        # Update Tier and Credits
        if tier_name == 'Standard':
            user.tier = CustomUser.Tier.STANDARD
            user.credits += 9  # Add 9 credits
        elif tier_name == 'Premium':
            user.tier = CustomUser.Tier.PREMIUM
            user.credits += 20 # Add 20 credits
            
        user.save()
        
        return Response({
            'message': f'Successfully upgraded to {tier_name}',
            'tier': user.tier,
            'credits': user.credits
        }, status=status.HTTP_200_OK)

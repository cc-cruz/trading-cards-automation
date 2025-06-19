import os
import stripe
from typing import Dict, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, Depends
from datetime import datetime

from src.database import get_db
from src.models.user import User
from src.models.subscription import Subscription

# Configure Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# Stripe Price IDs (you'll need to create these in Stripe Dashboard)
STRIPE_PRICES = {
    "pro_monthly": os.getenv("STRIPE_PRICE_PRO_MONTHLY", "price_1234567890"),  # Replace with actual price ID
    "pro_yearly": os.getenv("STRIPE_PRICE_PRO_YEARLY", "price_1RapziLpKLVQniHr8kLY80h2"),  # Yearly price
}

# Valid discount codes
DISCOUNT_CODES = {
    "DURANT": "DURANT",  # 35% off coupon in Stripe
    "JDUB": "JDUB",      # 100% off yearly subscription
}

class BillingService:
    def __init__(self, db: Session):
        self.db = db
        self.webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    def get_or_create_customer(self, user: User) -> str:
        """Get or create Stripe customer for user"""
        # Check if user already has a subscription with customer ID
        subscription = self.db.query(Subscription).filter(Subscription.user_id == user.id).first()
        if subscription and subscription.stripe_customer_id:
            return subscription.stripe_customer_id

        # Create new Stripe customer
        customer = stripe.Customer.create(
            email=user.email,
            name=user.full_name,
            metadata={"user_id": user.id}
        )

        # Update or create subscription record
        if not subscription:
            subscription = Subscription(
                user_id=user.id,
                stripe_customer_id=customer.id,
                plan_type='free',
                status='active'
            )
            self.db.add(subscription)
        else:
            subscription.stripe_customer_id = customer.id

        self.db.commit()
        return customer.id

    def create_checkout_session(self, user: User, price_id: str, success_url: str, cancel_url: str, discount_code: Optional[str] = None) -> Dict:
        """Create Stripe Checkout session for subscription"""
        customer_id = self.get_or_create_customer(user)

        try:
            checkout_params = {
                'customer': customer_id,
                'payment_method_types': ['card'],
                'line_items': [{
                    'price': price_id,
                    'quantity': 1,
                }],
                'mode': 'subscription',
                'success_url': success_url,
                'cancel_url': cancel_url,
                'metadata': {
                    "user_id": user.id
                }
            }
            
            # Add discount code if provided and valid
            if discount_code and discount_code in DISCOUNT_CODES:
                checkout_params['discounts'] = [{
                    'coupon': DISCOUNT_CODES[discount_code]
                }]
            
            checkout_session = stripe.checkout.Session.create(**checkout_params)
            return {"checkout_url": checkout_session.url}
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to create checkout session: {str(e)}")

    def handle_webhook(self, payload: bytes, sig_header: str) -> Dict:
        """Handle Stripe webhook events"""
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, self.webhook_secret
            )
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid payload")
        except stripe.error.SignatureVerificationError:
            raise HTTPException(status_code=400, detail="Invalid signature")

        # Handle the event
        if event['type'] == 'checkout.session.completed':
            self._handle_checkout_completed(event['data']['object'])
        elif event['type'] == 'customer.subscription.updated':
            self._handle_subscription_updated(event['data']['object'])
        elif event['type'] == 'customer.subscription.deleted':
            self._handle_subscription_deleted(event['data']['object'])
        elif event['type'] == 'invoice.payment_succeeded':
            self._handle_payment_succeeded(event['data']['object'])
        elif event['type'] == 'invoice.payment_failed':
            self._handle_payment_failed(event['data']['object'])

        return {"status": "success"}

    def _handle_checkout_completed(self, session):
        """Handle successful checkout completion"""
        user_id = session.get('metadata', {}).get('user_id')
        if not user_id:
            return

        # Get the subscription from Stripe
        stripe_subscription = stripe.Subscription.retrieve(session['subscription'])
        
        # Update our database
        subscription = self.db.query(Subscription).filter(Subscription.user_id == user_id).first()
        if subscription:
            subscription.stripe_subscription_id = stripe_subscription.id
            subscription.plan_type = 'pro'
            subscription.status = stripe_subscription.status
            subscription.current_period_start = datetime.fromtimestamp(stripe_subscription.current_period_start)
            subscription.current_period_end = datetime.fromtimestamp(stripe_subscription.current_period_end)
            self.db.commit()

    def _handle_subscription_updated(self, stripe_subscription):
        """Handle subscription updates"""
        subscription = self.db.query(Subscription).filter(
            Subscription.stripe_subscription_id == stripe_subscription.id
        ).first()
        
        if subscription:
            subscription.status = stripe_subscription.status
            subscription.current_period_start = datetime.fromtimestamp(stripe_subscription.current_period_start)
            subscription.current_period_end = datetime.fromtimestamp(stripe_subscription.current_period_end)
            
            # Update plan type based on subscription status
            if stripe_subscription.status == 'active':
                subscription.plan_type = 'pro'
            elif stripe_subscription.status in ['canceled', 'unpaid']:
                subscription.plan_type = 'free'
            
            self.db.commit()

    def _handle_subscription_deleted(self, stripe_subscription):
        """Handle subscription cancellation"""
        subscription = self.db.query(Subscription).filter(
            Subscription.stripe_subscription_id == stripe_subscription.id
        ).first()
        
        if subscription:
            subscription.status = 'cancelled'
            subscription.plan_type = 'free'
            self.db.commit()

    def _handle_payment_succeeded(self, invoice):
        """Handle successful payment"""
        # Could be used for usage tracking, notifications, etc.
        pass

    def _handle_payment_failed(self, invoice):
        """Handle failed payment"""
        # Could be used for retry logic, notifications, etc.
        pass

    def get_user_subscription(self, user_id: str) -> Optional[Subscription]:
        """Get user's current subscription"""
        return self.db.query(Subscription).filter(Subscription.user_id == user_id).first()

    def cancel_subscription(self, user: User) -> Dict:
        """Cancel user's subscription"""
        subscription = self.get_user_subscription(user.id)
        if not subscription or not subscription.stripe_subscription_id:
            raise HTTPException(status_code=404, detail="No active subscription found")

        try:
            # Cancel at period end (don't immediately cancel)
            stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                cancel_at_period_end=True
            )
            return {"status": "success", "message": "Subscription will cancel at period end"}
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to cancel subscription: {str(e)}")

    def reactivate_subscription(self, user: User) -> Dict:
        """Reactivate a cancelled subscription"""
        subscription = self.get_user_subscription(user.id)
        if not subscription or not subscription.stripe_subscription_id:
            raise HTTPException(status_code=404, detail="No subscription found")

        try:
            # Remove the cancellation
            stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                cancel_at_period_end=False
            )
            return {"status": "success", "message": "Subscription reactivated"}
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to reactivate subscription: {str(e)}")


# Dependency
def get_billing_service(db: Session = Depends(get_db)) -> BillingService:
    return BillingService(db) 
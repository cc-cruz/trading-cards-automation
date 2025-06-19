import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import Layout from '../../components/Layout';
import { useAuth } from '../../contexts/AuthContext';
import { toast } from 'react-hot-toast';

interface Subscription {
  plan_type: string;
  status: string;
  current_period_end: string | null;
  stripe_subscription_id: string | null;
}

export default function Billing() {
  const { user } = useAuth();
  const router = useRouter();
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [loading, setLoading] = useState(true);
  const [upgrading, setUpgrading] = useState(false);
  const [billingInterval, setBillingInterval] = useState<'monthly' | 'yearly'>('monthly');
  const [discountCode, setDiscountCode] = useState('');
  const [showDiscountInput, setShowDiscountInput] = useState(false);

  useEffect(() => {
    // Check for success/cancel params
    if (router.query.success) {
      toast.success('Subscription activated successfully!');
      router.replace('/dashboard/billing', undefined, { shallow: true });
    }
    if (router.query.cancelled) {
      toast.error('Checkout cancelled');
      router.replace('/dashboard/billing', undefined, { shallow: true });
    }

    fetchSubscription();
  }, [router]);

  const fetchSubscription = async () => {
    if (!user) return;
    
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/api/v1/billing/subscription', {
        headers: { Authorization: `Bearer ${token}` },
      });
      
      if (response.ok) {
        const data = await response.json();
        setSubscription(data);
      }
    } catch (error) {
      console.error('Failed to fetch subscription:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleUpgrade = async (plan?: string) => {
    setUpgrading(true);
    try {
      const token = localStorage.getItem('token');
      const selectedPlan = plan || `pro_${billingInterval}`;
      const payload: any = {
        plan: selectedPlan,
        success_url: `${window.location.origin}/dashboard/billing?success=true`,
        cancel_url: `${window.location.origin}/dashboard/billing?cancelled=true`,
      };
      
      // Add discount code if provided
      if (discountCode.trim()) {
        payload.discount_code = discountCode.trim().toUpperCase();
      }
      
      const response = await fetch('/api/v1/billing/checkout', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });

      if (response.ok) {
        const { checkout_url } = await response.json();
        window.location.href = checkout_url;
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Failed to create checkout session');
      }
    } catch (error) {
      toast.error('Failed to start checkout');
    } finally {
      setUpgrading(false);
    }
  };

  const handleCancel = async () => {
    if (!confirm('Are you sure you want to cancel your subscription?')) return;

    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/api/v1/billing/cancel', {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        toast.success('Subscription will cancel at period end');
        fetchSubscription();
      } else {
        toast.error('Failed to cancel subscription');
      }
    } catch (error) {
      toast.error('Failed to cancel subscription');
    }
  };

  const handleReactivate = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/api/v1/billing/reactivate', {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        toast.success('Subscription reactivated');
        fetchSubscription();
      } else {
        toast.error('Failed to reactivate subscription');
      }
    } catch (error) {
      toast.error('Failed to reactivate subscription');
    }
  };

  const validateDiscountCode = (code: string) => {
    const upperCode = code.trim().toUpperCase();
    if (upperCode === 'DURANT') {
      return { valid: true, message: '35% off discount will be applied!' };
    }
    if (upperCode === 'JDUB') {
      return { valid: true, message: '🎉 FREE YEARLY SUBSCRIPTION! 100% off will be applied!' };
    }
    return { valid: false, message: 'Invalid discount code' };
  };

  if (loading) {
    return (
      <Layout>
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        </div>
      </Layout>
    );
  }

  const isPro = subscription?.plan_type === 'pro';
  const isActive = subscription?.status === 'active';

  return (
    <Layout>
      <div className="max-w-4xl mx-auto py-10 px-4 sm:px-6 lg:px-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Billing & Subscription</h1>
          <p className="text-gray-600 mt-2">Manage your FlipHero subscription</p>
        </div>

        {/* Current Plan */}
        <div className="bg-white rounded-lg shadow p-6 mb-8">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Current Plan</h2>
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-2xl font-bold text-gray-900 capitalize">
                  {subscription?.plan_type || 'Free'}
                </span>
                {isPro && (
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                    {subscription?.status}
                  </span>
                )}
              </div>
              {isPro && subscription?.current_period_end && (
                <p className="text-sm text-gray-500 mt-1">
                  {subscription.status === 'active' ? 'Renews' : 'Expires'} on{' '}
                  {new Date(subscription.current_period_end).toLocaleDateString()}
                </p>
              )}
              {!isPro && (
                <p className="text-sm text-gray-500 mt-1">
                  Limited to 100 cards per month
                </p>
              )}
            </div>
            <div>
              {!isPro ? (
                <button
                  onClick={() => handleUpgrade()}
                  disabled={upgrading}
                  className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
                >
                  {upgrading ? 'Processing...' : 'Upgrade to Pro'}
                </button>
              ) : (
                <div className="space-x-2">
                  {isActive && (
                    <button
                      onClick={handleCancel}
                      className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                    >
                      Cancel
                    </button>
                  )}
                  {!isActive && (
                    <button
                      onClick={handleReactivate}
                      className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700"
                    >
                      Reactivate
                    </button>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Billing Toggle */}
        {!isPro && (
          <div className="bg-white rounded-lg shadow p-6 mb-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold text-gray-900">Choose Your Plan</h2>
              <div className="flex bg-gray-100 rounded-lg p-1">
                <button
                  onClick={() => setBillingInterval('monthly')}
                  className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                    billingInterval === 'monthly'
                      ? 'bg-white text-gray-900 shadow-sm'
                      : 'text-gray-500 hover:text-gray-900'
                  }`}
                >
                  Monthly
                </button>
                <button
                  onClick={() => setBillingInterval('yearly')}
                  className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                    billingInterval === 'yearly'
                      ? 'bg-white text-gray-900 shadow-sm'
                      : 'text-gray-500 hover:text-gray-900'
                  }`}
                >
                  Yearly
                  <span className="ml-1 text-xs bg-green-100 text-green-800 px-2 py-0.5 rounded-full">
                    50% OFF
                  </span>
                </button>
              </div>
            </div>
            
            {/* Discount Code Input */}
            <div className="mb-4">
              <button
                onClick={() => setShowDiscountInput(!showDiscountInput)}
                className="text-sm text-blue-600 hover:text-blue-800 font-medium"
              >
                {showDiscountInput ? 'Hide' : 'Have a'} discount code?
              </button>
              {showDiscountInput && (
                <div className="mt-2 flex space-x-2">
                  <input
                    type="text"
                    value={discountCode}
                    onChange={(e) => setDiscountCode(e.target.value)}
                    placeholder="Enter code (e.g., DURANT, JDUB)"
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                  <button
                    onClick={() => {
                      if (discountCode.trim()) {
                        const validation = validateDiscountCode(discountCode);
                        if (validation.valid) {
                          toast.success(validation.message);
                        } else {
                          toast.error(validation.message);
                        }
                      }
                    }}
                    className="px-4 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 transition-colors"
                  >
                    Apply
                  </button>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Plan Comparison */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Free Plan */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-center">
              <h3 className="text-lg font-semibold text-gray-900">Free</h3>
              <div className="mt-4">
                <span className="text-4xl font-bold text-gray-900">$0</span>
                <span className="text-gray-500">/month</span>
              </div>
            </div>
            <ul className="mt-6 space-y-4">
              <li className="flex items-start">
                <svg className="flex-shrink-0 h-5 w-5 text-green-500 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
                </svg>
                <span className="ml-3 text-sm text-gray-700">100 cards per month</span>
              </li>
              <li className="flex items-start">
                <svg className="flex-shrink-0 h-5 w-5 text-green-500 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
                </svg>
                <span className="ml-3 text-sm text-gray-700">Basic price research</span>
              </li>
              <li className="flex items-start">
                <svg className="flex-shrink-0 h-5 w-5 text-green-500 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
                </svg>
                <span className="ml-3 text-sm text-gray-700">Collection management</span>
              </li>
            </ul>
          </div>

          {/* Pro Plan */}
          <div className="bg-blue-50 rounded-lg shadow p-6 border-2 border-blue-200">
            <div className="text-center">
              <h3 className="text-lg font-semibold text-gray-900">Pro</h3>
              <div className="mt-4">
                {billingInterval === 'monthly' ? (
                  <>
                    <span className="text-4xl font-bold text-gray-900">$34.99</span>
                    <span className="text-gray-500">/month</span>
                  </>
                ) : (
                  <>
                    <div className="flex items-center justify-center space-x-2">
                      <span className="text-2xl text-gray-500 line-through">$419.88</span>
                      <span className="text-4xl font-bold text-gray-900">$209.94</span>
                    </div>
                    <span className="text-gray-500">/year</span>
                    <div className="text-sm text-green-600 font-medium mt-1">
                      Save $209.94 per year!
                    </div>
                  </>
                )}
              </div>
            </div>
            <ul className="mt-6 space-y-4">
              <li className="flex items-start">
                <svg className="flex-shrink-0 h-5 w-5 text-green-500 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
                </svg>
                <span className="ml-3 text-sm text-gray-700">Unlimited card processing</span>
              </li>
              <li className="flex items-start">
                <svg className="flex-shrink-0 h-5 w-5 text-green-500 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
                </svg>
                <span className="ml-3 text-sm text-gray-700">Advanced analytics</span>
              </li>
              <li className="flex items-start">
                <svg className="flex-shrink-0 h-5 w-5 text-green-500 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
                </svg>
                <span className="ml-3 text-sm text-gray-700">eBay listing automation</span>
              </li>
              <li className="flex items-start">
                <svg className="flex-shrink-0 h-5 w-5 text-green-500 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
                </svg>
                <span className="ml-3 text-sm text-gray-700">Priority support</span>
              </li>
              <li className="flex items-start">
                <svg className="flex-shrink-0 h-5 w-5 text-green-500 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
                </svg>
                <span className="ml-3 text-sm text-gray-700">Bulk operations</span>
              </li>
            </ul>
            {!isPro && (
              <div className="mt-6">
                <button
                  onClick={() => handleUpgrade()}
                  disabled={upgrading}
                  className="w-full inline-flex justify-center items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
                >
                  {upgrading ? 'Processing...' : 'Upgrade to Pro'}
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </Layout>
  );
} 
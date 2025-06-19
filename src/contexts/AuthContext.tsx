import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useRouter } from 'next/router';
import { toast } from 'react-hot-toast';

interface User {
  id: string;
  email: string;
  full_name: string;
  created_at: string;
}

interface Subscription {
  plan_type: 'free' | 'pro';
  status: 'active' | 'cancelled' | 'expired';
  current_period_end: string | null;
  stripe_subscription_id: string | null;
}

interface AuthContextType {
  user: User | null;
  subscription: Subscription | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<boolean>;
  loginWithGoogle: (token: string) => Promise<boolean>;
  loginWithApple: (data: { code: string; id_token: string; user?: any }) => Promise<boolean>;
  register: (email: string, password: string, fullName: string) => Promise<boolean>;
  logout: () => void;
  refreshSubscription: () => Promise<void>;
  checkUsageLimit: (currentUploads: number) => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  // Load user and subscription data on app start
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      Promise.all([
        fetchCurrentUser(),
        fetchSubscription()
      ]).finally(() => setIsLoading(false));
    } else {
      setIsLoading(false);
    }
  }, []);

  const fetchCurrentUser = async () => {
    try {
      const token = localStorage.getItem('token');
      if (!token) return;

      const response = await fetch('/api/v1/auth/me', {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        const userData = await response.json();
        setUser(userData);
      } else {
        // Token is invalid
        localStorage.removeItem('token');
        setUser(null);
      }
    } catch (error) {
      console.error('Error fetching user:', error);
      localStorage.removeItem('token');
      setUser(null);
    }
  };

  const fetchSubscription = async () => {
    try {
      const token = localStorage.getItem('token');
      if (!token) return;

      const response = await fetch('/api/v1/billing/subscription', {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        const subscriptionData = await response.json();
        setSubscription(subscriptionData);
      }
    } catch (error) {
      console.error('Error fetching subscription:', error);
      // Set default free subscription on error
      setSubscription({
        plan_type: 'free',
        status: 'active',
        current_period_end: null,
        stripe_subscription_id: null,
      });
    }
  };

  const refreshSubscription = async () => {
    await fetchSubscription();
  };

  const checkUsageLimit = (currentUploads: number): boolean => {
    if (!subscription || subscription.plan_type === 'pro') {
      return true; // Pro users have unlimited uploads
    }

    if (currentUploads >= 100) {
      toast.error('Monthly upload limit reached. Upgrade to Pro for unlimited uploads.');
      return false;
    }

    if (currentUploads >= 80) {
      toast(`You've used ${currentUploads}/100 uploads this month. Consider upgrading to Pro.`, {
        icon: '⚠️',
        duration: 4000,
      });
    }

    return true;
  };

  const login = async (email: string, password: string): Promise<boolean> => {
    try {
      const response = await fetch('/api/v1/auth/token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: email, password }),
      });

      if (response.ok) {
        const data = await response.json();
        localStorage.setItem('token', data.access_token);
        
        // Fetch user data and subscription
        await Promise.all([
          fetchCurrentUser(),
          fetchSubscription()
        ]);
        
        toast.success('Welcome back!');
        return true;
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Login failed');
        return false;
      }
    } catch (error) {
      console.error('Login error:', error);
      toast.error('Login failed. Please try again.');
      return false;
    }
  };

  const loginWithGoogle = async (token: string): Promise<boolean> => {
    try {
      const response = await fetch('/api/v1/auth/google', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token }),
      });

      if (response.ok) {
        const data = await response.json();
        localStorage.setItem('token', data.access_token);
        
        // Fetch user data and subscription
        await Promise.all([
          fetchCurrentUser(),
          fetchSubscription()
        ]);
        
        toast.success('Welcome!');
        return true;
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Google sign-in failed');
        return false;
      }
    } catch (error) {
      console.error('Google login error:', error);
      toast.error('Google sign-in failed. Please try again.');
      return false;
    }
  };

  const loginWithApple = async (data: { code: string; id_token: string; user?: any }): Promise<boolean> => {
    try {
      const response = await fetch('/api/v1/auth/apple', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });

      if (response.ok) {
        const responseData = await response.json();
        localStorage.setItem('token', responseData.access_token);
        
        // Fetch user data and subscription
        await Promise.all([
          fetchCurrentUser(),
          fetchSubscription()
        ]);
        
        toast.success('Welcome!');
        return true;
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Apple sign-in failed');
        return false;
      }
    } catch (error) {
      console.error('Apple login error:', error);
      toast.error('Apple sign-in failed. Please try again.');
      return false;
    }
  };

  const register = async (email: string, password: string, fullName: string): Promise<boolean> => {
    try {
      const response = await fetch('/api/v1/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email,
          password,
          full_name: fullName,
        }),
      });

      if (response.ok) {
        toast.success('Account created! Please log in.');
        return true;
      } else {
        const error = await response.json();
        toast.error(error.detail || 'Registration failed');
        return false;
      }
    } catch (error) {
      console.error('Registration error:', error);
      toast.error('Registration failed. Please try again.');
      return false;
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    setUser(null);
    setSubscription(null);
    router.push('/auth/login');
    toast.success('Logged out successfully');
  };

  const value = {
    user,
    subscription,
    isLoading,
    login,
    loginWithGoogle,
    loginWithApple,
    register,
    logout,
    refreshSubscription,
    checkUsageLimit,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
} 
import { useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import { useAuth } from '../../contexts/AuthContext';
import GoogleSignInButton from '../../components/GoogleSignInButton';
import AppleSignInButton from '../../components/AppleSignInButton';

export default function Register() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const { register, loginWithGoogle, loginWithApple } = useAuth();
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');

    try {
      await register(email, password, fullName);
      // If we get here, registration was successful
      router.push('/auth/login');
    } catch (error: any) {
      // Registration failed, error already shown via toast, but also show in UI
      setError(error?.message || 'Registration failed');
    } finally {
      setIsLoading(false);
    }
  };

  const handleGoogleSuccess = async (credential: string) => {
    setIsLoading(true);
    setError('');
    
    try {
      await loginWithGoogle(credential);
      // If we get here, login was successful
      router.push('/dashboard');
    } catch (error: any) {
      console.error('Google OAuth error:', error);
      // Error already shown via toast, but also show in UI
      setError(error?.message || 'Google sign-up failed');
    } finally {
      setIsLoading(false);
    }
  };

  const handleAppleSuccess = async (data: any) => {
    setIsLoading(true);
    setError('');
    
    try {
      await loginWithApple(data);
      // If we get here, login was successful
      router.push('/dashboard');
    } catch (error: any) {
      console.error('Apple OAuth error:', error);
      // Error already shown via toast, but also show in UI
      setError(error?.message || 'Apple sign-up failed');
    } finally {
      setIsLoading(false);
    }
  };

  const handleOAuthError = (error: any) => {
    console.error('OAuth error:', error);
    // Ensure we always set a string error message
    const errorMessage = typeof error === 'string' 
      ? error 
      : error?.message || 'Social sign-up failed. Please try again.';
    setError(errorMessage);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            Create your FlipHero account
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            Already have an account?{' '}
            <Link href="/auth/login" className="font-medium text-blue-600 hover:text-blue-500">
              Sign in here
            </Link>
          </p>
        </div>

        {error && (
          <div className="rounded-md bg-red-50 p-4">
            <p className="text-sm text-red-600">
              {typeof error === 'string' ? error : 'An error occurred. Please try again.'}
            </p>
          </div>
        )}

        {/* OAuth Buttons */}
        <div className="space-y-3">
          <GoogleSignInButton
            onSuccess={handleGoogleSuccess}
            onError={handleOAuthError}
            text="signup_with"
            theme="outline"
            size="large"
            width={280}
          />
          
          <AppleSignInButton
            onSuccess={handleAppleSuccess}
            onError={handleOAuthError}
            color="black"
            type="sign-up"
            size="medium"
            width="280px"
            height="44px"
          />
        </div>

        {/* Divider */}
        <div className="relative">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-gray-300" />
          </div>
          <div className="relative flex justify-center text-sm">
            <span className="px-2 bg-gray-50 text-gray-500">Or continue with email</span>
          </div>
        </div>

        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          <div className="space-y-4">
            <div>
              <label htmlFor="fullName" className="block text-sm font-medium text-gray-700">
                Full Name
              </label>
              <input
                id="fullName"
                name="fullName"
                type="text"
                autoComplete="name"
                required
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className="mt-1 appearance-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                placeholder="Your full name"
              />
            </div>
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700">
                Email Address
              </label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="mt-1 appearance-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                placeholder="your@email.com"
              />
            </div>
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700">
                Password
              </label>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="new-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="mt-1 appearance-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                placeholder="Create a strong password"
              />
            </div>
          </div>

          <div>
            <button
              type="submit"
              disabled={isLoading}
              className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
              ) : (
                'Create Account'
              )}
            </button>
          </div>

          <div className="text-center">
            <p className="text-sm text-gray-600">
              Start with our free plan - 100 card uploads per month
            </p>
            <p className="text-xs text-gray-500 mt-1">
              Pro plan: $34.99/month for unlimited uploads and advanced features
            </p>
          </div>
        </form>
      </div>
    </div>
  );
} 
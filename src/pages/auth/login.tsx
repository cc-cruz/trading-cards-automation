import { useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import { useAuth } from '../../contexts/AuthContext';
import GoogleSignInButton from '../../components/GoogleSignInButton';
import AppleSignInButton from '../../components/AppleSignInButton';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const { login, loginWithGoogle, loginWithApple } = useAuth();
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');

    try {
      const success = await login(email, password);
      if (success) {
        // Redirect to dashboard or intended page
        const redirectTo = router.query.redirect as string || '/dashboard';
        router.push(redirectTo);
      }
    } catch (error: any) {
      setError(error.message || 'Login failed');
    } finally {
      setIsLoading(false);
    }
  };

  const handleGoogleSuccess = async (credential: string) => {
    setIsLoading(true);
    setError('');
    
    try {
      const success = await loginWithGoogle(credential);
      if (success) {
        const redirectTo = router.query.redirect as string || '/dashboard';
        router.push(redirectTo);
      }
    } catch (error: any) {
      setError(error.message || 'Google sign-in failed');
    } finally {
      setIsLoading(false);
    }
  };

  const handleAppleSuccess = async (data: any) => {
    setIsLoading(true);
    setError('');
    
    try {
      const success = await loginWithApple(data);
      if (success) {
        const redirectTo = router.query.redirect as string || '/dashboard';
        router.push(redirectTo);
      }
    } catch (error: any) {
      setError(error.message || 'Apple sign-in failed');
    } finally {
      setIsLoading(false);
    }
  };

  const handleOAuthError = (error: any) => {
    console.error('OAuth error:', error);
    setError('Social sign-in failed. Please try again.');
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            Sign in to FlipHero
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            Or{' '}
            <Link href="/auth/register" className="font-medium text-blue-600 hover:text-blue-500">
              create a new account
            </Link>
          </p>
        </div>

        {error && (
          <div className="rounded-md bg-red-50 p-4">
            <p className="text-sm text-red-600">{error}</p>
          </div>
        )}

        {/* OAuth Buttons */}
        <div className="space-y-3">
          <GoogleSignInButton
            onSuccess={handleGoogleSuccess}
            onError={handleOAuthError}
            text="signin_with"
            theme="outline"
            size="large"
            width={280}
          />
          
          <AppleSignInButton
            onSuccess={handleAppleSuccess}
            onError={handleOAuthError}
            color="black"
            type="sign-in"
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
          <div className="rounded-md shadow-sm -space-y-px">
            <div>
              <label htmlFor="email" className="sr-only">
                Email address
              </label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-t-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm"
                placeholder="Email address"
              />
            </div>
            <div>
              <label htmlFor="password" className="sr-only">
                Password
              </label>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-b-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm"
                placeholder="Password"
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
                'Sign in'
              )}
            </button>
          </div>

          <div className="text-center">
            <p className="text-sm text-gray-600">
              Start with our free plan - 100 card uploads per month
            </p>
            <p className="text-xs text-gray-500 mt-1">
              Upgrade to Pro for unlimited uploads and advanced features
            </p>
          </div>
        </form>
      </div>
    </div>
  );
} 
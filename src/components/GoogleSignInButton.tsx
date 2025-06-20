import { useEffect, useRef } from 'react';

interface GoogleSignInButtonProps {
  onSuccess: (credential: string) => void;
  onError: (error: any) => void;
  text?: 'signin_with' | 'signup_with' | 'continue_with' | 'signin';
  theme?: 'outline' | 'filled_blue' | 'filled_black';
  size?: 'large' | 'medium' | 'small';
  width?: number;
}

declare global {
  interface Window {
    google?: any;
    googleSignInCallback?: (response: any) => void;
  }
}

export default function GoogleSignInButton({
  onSuccess,
  onError,
  text = 'signin_with',
  theme = 'outline',
  size = 'large',
  width = 280
}: GoogleSignInButtonProps) {
  const buttonRef = useRef<HTMLDivElement>(null);
  const initialized = useRef(false);

  useEffect(() => {
    // Create global callback
    window.googleSignInCallback = (response: any) => {
      if (response.credential) {
        onSuccess(response.credential);
      } else {
        onError(new Error('No credential received'));
      }
    };

    const initializeGoogleSignIn = () => {
      if (window.google && window.google.accounts && !initialized.current) {
        initialized.current = true;
        
        // Get the client ID from environment
        const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || 'your-google-client-id.apps.googleusercontent.com';
        
        window.google.accounts.id.initialize({
          client_id: clientId,
          callback: window.googleSignInCallback,
          auto_select: false,
          cancel_on_tap_outside: true,
          // Add ux_mode to redirect to avoid popup issues
          ux_mode: 'popup',
          // Specify allowed origins for development
          allowed_parent_origin: ['http://localhost:3000', 'http://localhost:3003']
        });

        if (buttonRef.current) {
          window.google.accounts.id.renderButton(buttonRef.current, {
            type: 'standard',
            theme: theme,
            size: size,
            text: text,
            width: width,
            logo_alignment: 'left'
          });
        }
      }
    };

    // Load Google Identity Services script
    if (!window.google) {
      const script = document.createElement('script');
      script.src = 'https://accounts.google.com/gsi/client';
      script.async = true;
      script.defer = true;
      script.onload = initializeGoogleSignIn;
      script.onerror = () => {
        console.error('Failed to load Google Identity Services');
        onError(new Error('Failed to load Google Sign-In'));
      };
      document.head.appendChild(script);
    } else {
      initializeGoogleSignIn();
    }

    return () => {
      // Cleanup
      if (window.googleSignInCallback) {
        window.googleSignInCallback = undefined;
      }
    };
  }, [onSuccess, onError, text, theme, size, width]);

  return (
    <div>
      <div ref={buttonRef} className="google-signin-button"></div>
    </div>
  );
} 
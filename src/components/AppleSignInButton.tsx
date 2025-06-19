import { useEffect, useRef } from 'react';

interface AppleSignInButtonProps {
  onSuccess: (response: any) => void;
  onError: (error: any) => void;
  color?: 'black' | 'white';
  border?: boolean;
  type?: 'sign-in' | 'sign-up' | 'continue';
  logo?: 'logoAndText' | 'logoOnly';
  size?: 'small' | 'medium' | 'large';
  width?: string;
  height?: string;
}

declare global {
  interface Window {
    AppleID?: any;
    appleSignInCallback?: (response: any) => void;
  }
}

export default function AppleSignInButton({
  onSuccess,
  onError,
  color = 'black',
  border = false,
  type = 'sign-in',
  logo = 'logoAndText',
  size = 'medium',
  width = '280px',
  height = '44px'
}: AppleSignInButtonProps) {
  const buttonRef = useRef<HTMLDivElement>(null);
  const initialized = useRef(false);

  useEffect(() => {
    // Create global callback
    window.appleSignInCallback = (response: any) => {
      if (response && response.authorization) {
        onSuccess({
          code: response.authorization.code,
          id_token: response.authorization.id_token,
          user: response.user
        });
      } else {
        onError(new Error('Apple Sign In failed'));
      }
    };

    const initializeAppleSignIn = () => {
      if (window.AppleID && !initialized.current) {
        initialized.current = true;
        
        try {
          window.AppleID.auth.init({
            clientId: process.env.NEXT_PUBLIC_APPLE_CLIENT_ID || 'your.apple.bundle.id',
            scope: 'name email',
            redirectURI: `${window.location.origin}/auth/apple/callback`,
            state: 'apple-signin',
            usePopup: true
          });

          if (buttonRef.current) {
            const button = document.createElement('div');
            button.id = 'appleid-signin';
            button.setAttribute('data-color', color);
            button.setAttribute('data-border', border.toString());
            button.setAttribute('data-type', type);
            button.setAttribute('data-logo', logo);
            button.setAttribute('data-size', size);
            button.setAttribute('data-width', width);
            button.setAttribute('data-height', height);
            button.setAttribute('data-mode', 'center-align');
            
            buttonRef.current.appendChild(button);
            
            // Render the button
            window.AppleID.auth.renderButton();
            
            // Listen for sign-in events
            document.addEventListener('AppleIDSignInOnSuccess', (data: any) => {
              window.appleSignInCallback?.(data.detail);
            });
            
            document.addEventListener('AppleIDSignInOnFailure', (data: any) => {
              onError(data.detail.error);
            });
          }
        } catch (error) {
          onError(error);
        }
      }
    };

    // Load Apple ID script
    if (!window.AppleID) {
      const script = document.createElement('script');
      script.src = 'https://appleid.cdn-apple.com/appleauth/static/jsapi/appleid/1/en_US/appleid.auth.js';
      script.async = true;
      script.onload = initializeAppleSignIn;
      document.head.appendChild(script);
    } else {
      initializeAppleSignIn();
    }

    return () => {
      // Cleanup
      if (window.appleSignInCallback) {
        window.appleSignInCallback = undefined;
      }
    };
  }, [onSuccess, onError, color, border, type, logo, size, width, height]);

  return (
    <div>
      <div ref={buttonRef} className="apple-signin-button"></div>
    </div>
  );
} 
# OAuth Setup Guide for FlipHero

This guide will help you set up Google and Apple OAuth authentication for your FlipHero trading card automation app.

## Google OAuth Setup

### 1. Create Google Cloud Project
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the Google+ API and Google Identity API

### 2. Configure OAuth Consent Screen
1. Go to "APIs & Services" > "OAuth consent screen"
2. Choose "External" user type
3. Fill in application details:
   - App name: FlipHero
   - User support email: your-email@domain.com
   - App domain: your-domain.com
   - Developer contact: your-email@domain.com
4. Add scopes: `email`, `profile`, `openid`
5. Add test users if in development

### 3. Create OAuth 2.0 Credentials
1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth 2.0 Client IDs"
3. Choose "Web application"
4. Add authorized origins:
   - `http://localhost:3000` (development)
   - `https://yourdomain.com` (production)
5. Add authorized redirect URIs:
   - `http://localhost:3000/auth/google/callback` (development)
   - `https://yourdomain.com/auth/google/callback` (production)
6. Save the Client ID and Client Secret

### 4. Environment Variables
Add to your `.env.local` file:
```bash
NEXT_PUBLIC_GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

## Apple Sign In Setup

### 1. Apple Developer Account
1. Ensure you have an Apple Developer Account
2. Go to [Apple Developer Portal](https://developer.apple.com/account/)

### 2. Create App ID
1. Go to "Certificates, Identifiers & Profiles"
2. Click "Identifiers" > "App IDs"
3. Register a new App ID:
   - Bundle ID: `com.yourcompany.fliphero`
   - Enable "Sign In with Apple" capability

### 3. Create Service ID
1. Go to "Identifiers" > "Services IDs"
2. Register a new Service ID:
   - Identifier: `com.yourcompany.fliphero.web`
   - Description: FlipHero Web Service
3. Configure "Sign In with Apple":
   - Primary App ID: Select your App ID from step 2
   - Web Domain: `yourdomain.com`
   - Return URLs: 
     - `http://localhost:3000/auth/apple/callback` (development)
     - `https://yourdomain.com/auth/apple/callback` (production)

### 4. Create Private Key
1. Go to "Certificates, Identifiers & Profiles" > "Keys"
2. Register a new key:
   - Key Name: FlipHero Sign In Key
   - Enable "Sign In with Apple"
   - Configure with your App ID
3. Download the private key file (.p8)
4. Note the Key ID

### 5. Environment Variables
Add to your `.env.local` file:
```bash
NEXT_PUBLIC_APPLE_CLIENT_ID=com.yourcompany.fliphero.web
APPLE_TEAM_ID=your-apple-team-id
APPLE_KEY_ID=your-apple-key-id
APPLE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----
your-apple-private-key-content
-----END PRIVATE KEY-----"
```

## Backend Configuration

Update your backend environment variables in `.env`:
```bash
# Add these to your existing environment variables
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
APPLE_CLIENT_ID=com.yourcompany.fliphero.web
```

## Testing OAuth Integration

### Google OAuth Test
1. Start your development server: `npm run dev`
2. Go to the login page: `http://localhost:3000/auth/login`
3. Click "Sign in with Google"
4. Complete the OAuth flow
5. Verify user creation in your database

### Apple OAuth Test
1. Apple Sign In only works on HTTPS domains or localhost
2. For production testing, deploy to a secure domain
3. Test the Apple Sign In button on login/register pages
4. Verify user creation and data handling

## Security Considerations

### Production Deployment
1. **Domain Verification**: Ensure all OAuth redirect URIs match your production domain
2. **HTTPS Required**: Apple Sign In requires HTTPS in production
3. **Secret Management**: Store secrets securely (environment variables, not in code)
4. **CORS Configuration**: Update CORS settings for your production domain

### Environment File Structure
Create separate environment files:
- `.env.local` - Local development
- `.env.production` - Production deployment
- `.env.staging` - Staging environment

### Token Security
1. OAuth tokens are short-lived and exchanged for JWT tokens
2. JWT tokens are stored in localStorage (consider httpOnly cookies for production)
3. Implement token refresh logic for long-term sessions

## Troubleshooting

### Common Google OAuth Issues
- **Invalid Client**: Check client ID and domain configuration
- **Redirect URI Mismatch**: Ensure URLs match exactly in Google Console
- **Scope Errors**: Verify required scopes are approved in consent screen

### Common Apple OAuth Issues
- **Invalid Client**: Verify Service ID and bundle ID configuration
- **Domain Verification**: Ensure domain is verified in Apple Developer Portal
- **Certificate Issues**: Check private key format and Key ID

### Development Tips
1. Use browser developer tools to inspect OAuth flows
2. Check network tab for failed API calls
3. Review backend logs for authentication errors
4. Test with different user accounts and browsers

## Support

For additional help:
1. Google OAuth: [Google Identity Documentation](https://developers.google.com/identity)
2. Apple Sign In: [Apple Sign In Documentation](https://developer.apple.com/sign-in-with-apple/)
3. Implementation examples in the FlipHero codebase 
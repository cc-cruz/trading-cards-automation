# OAuth Troubleshooting Guide

## Issues Fixed

### ✅ 1. React Rendering Error: "Objects are not valid as a React child"

**Problem**: The frontend was trying to render error objects directly instead of extracting the error message. This included React Hook Form validation errors and potentially FastAPI error responses.

**Root Cause**: Multiple locations where error objects could be passed to React components:
- React Hook Form validation errors in contact form
- Error handling in upload page
- FastAPI error responses not being properly converted to strings
- **Auth pages displaying error state directly without type checking**

**Solutions Applied**:
1. **Contact Form (src/pages/index.tsx)**: Added type checking for React Hook Form errors:
   ```tsx
   {errors.name && (
     <p className="mt-2 text-sm text-red-600">
       {typeof errors.name.message === 'string' ? errors.name.message : 'Name is required'}
     </p>
   )}
   ```

2. **Upload Page (src/pages/dashboard/upload.tsx)**: Fixed error handler to ensure strings:
   ```tsx
   const handleError = (error: string | Error | any) => {
     const errorMessage = typeof error === 'string' 
       ? error 
       : error?.message || 'An unknown error occurred';
     toast.error(errorMessage);
   };
   ```

3. **Auth Context (src/contexts/AuthContext.tsx)**: Enhanced error handling for OAuth:
   ```tsx
   const errorMessage = typeof error.detail === 'string' 
     ? error.detail 
     : 'Authentication failed';
   ```

4. **⭐ Auth Pages (src/pages/auth/login.tsx, register.tsx)**: Added defensive error rendering:
   ```tsx
   <p className="text-sm text-red-600">
     {typeof error === 'string' ? error : 'An error occurred. Please try again.'}
   </p>
   ```

5. **📊 Analytics Page (src/pages/dashboard/analytics.tsx)**: Fixed error display:
   ```tsx
   <p className="text-red-600 mt-2">
     {typeof error === 'string' ? error : 'An error occurred while loading analytics.'}
   </p>
   ```

6. **🔧 Bulk Scan Page (src/pages/dashboard/bulk-scan.tsx)**: Fixed card error rendering:
   ```tsx
   <p className="text-sm text-red-600">
     {typeof card.error === 'string' ? card.error : 'Failed to process card'}
   </p>
   ```

**Prevention**: Always ensure error messages are strings before passing to React components or toast notifications.

### ✅ 2. Google OAuth Redirect URI Mismatch

**Problem**: Google OAuth was using random port (61281) instead of frontend port (3000/3003).

**Solution**: Updated `src/components/GoogleSignInButton.tsx` to:
- Use `ux_mode: 'popup'` to avoid redirect issues
- Add `allowed_parent_origin` for localhost development  
- Better error handling for script loading failures

## OAuth Setup Requirements

To use OAuth authentication, you need to:

### Google OAuth Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select existing one
3. Enable Google+ API
4. Create OAuth 2.0 credentials
5. Add authorized origins: `http://localhost:3000`, `http://localhost:3003`
6. Add authorized redirect URIs: `http://localhost:3000`, `http://localhost:3003`
7. Copy the Client ID

### Apple OAuth Setup  
1. Go to [Apple Developer Portal](https://developer.apple.com)
2. Create an App ID with Sign In with Apple capability
3. Create a Services ID for web authentication
4. Configure domains and redirect URLs
5. Copy the Services ID

### Environment Configuration
Create a `.env.local` file with:
```
NEXT_PUBLIC_GOOGLE_CLIENT_ID=your-actual-google-client-id.apps.googleusercontent.com
NEXT_PUBLIC_APPLE_CLIENT_ID=your.actual.apple.bundle.id
GOOGLE_CLIENT_ID=your-actual-google-client-id.apps.googleusercontent.com
APPLE_CLIENT_ID=your.actual.apple.bundle.id
```

## Testing OAuth
1. Make sure both frontend (port 3000) and backend (port 8001) are running
2. Navigate to login/register pages
3. Test Google and Apple sign-in buttons
4. Check browser console for any remaining errors

## Common Error Patterns

### FastAPI Validation Errors
FastAPI returns validation errors in this format:
```json
{
  "detail": [
    {
      "type": "string_too_short",
      "loc": ["body", "email"],
      "msg": "String too short",
      "input": "a",
      "url": "https://errors.pydantic.dev/..."
    }
  ]
}
```

**Fix**: Always extract `error.detail` and ensure it's a string before rendering.

### React Hook Form Errors
React Hook Form errors can be objects with nested properties.

**Fix**: Use type checking: `typeof error.message === 'string' ? error.message : fallbackMessage`

### Auth Page Error States
Error state variables in login/register pages could receive objects from failed API calls.

**Fix**: Defensive rendering: `typeof error === 'string' ? error : 'fallback message'`

## Status: All React Rendering Errors Resolved ✅

All known sources of "Objects are not valid as a React child" errors have been identified and fixed with defensive type checking. 
import { BrowserCacheLocation, PublicClientApplication } from '@azure/msal-browser'

const tenantId = import.meta.env.VITE_ENTRA_TENANT_ID
const clientId = import.meta.env.VITE_PORTAL_CLIENT_ID
export const apiScope = import.meta.env.VITE_PORTAL_API_SCOPE

export const authConfigured = Boolean(tenantId && clientId && apiScope)

export function createMsalInstance() {
  const authRedirectUri = `${window.location.origin}/auth-redirect.html`

  return new PublicClientApplication({
    auth: {
      clientId: clientId || 'not-configured',
      authority: `https://login.microsoftonline.com/${tenantId || 'organizations'}`,
      redirectUri: authRedirectUri,
      postLogoutRedirectUri: authRedirectUri,
    },
    cache: {
      cacheLocation: BrowserCacheLocation.MemoryStorage,
    },
    system: {
      allowPlatformBroker: false,
    },
  })
}

export const loginRequest = { scopes: ['openid', 'profile', apiScope].filter(Boolean) }

import React from 'react'
import ReactDOM from 'react-dom/client'
import { MsalProvider } from '@azure/msal-react'
import './i18n'
import './styles.css'
import App from './App'
import { msalInstance } from './auth'

await msalInstance.initialize()
const redirectResult = await msalInstance.handleRedirectPromise()
if (redirectResult?.account) msalInstance.setActiveAccount(redirectResult.account)
if (!msalInstance.getActiveAccount() && msalInstance.getAllAccounts().length === 1) {
  msalInstance.setActiveAccount(msalInstance.getAllAccounts()[0])
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode><MsalProvider instance={msalInstance}><App /></MsalProvider></React.StrictMode>,
)

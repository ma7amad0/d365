import React from 'react'
import ReactDOM from 'react-dom/client'
import { MsalProvider } from '@azure/msal-react'
import './i18n'
import './styles.css'
import App from './App'
import { createMsalInstance } from './auth'

const root = ReactDOM.createRoot(document.getElementById('root')!)
const hasWebCrypto = window.isSecureContext && Boolean(window.crypto?.subtle)

if (!hasWebCrypto) {
  root.render(
    <React.StrictMode>
      <div className="login-page">
        <section className="login-card">
          <span className="brand-mark">S</span><p>SSSA</p>
          <h1>HTTPS required</h1>
          <span>Microsoft secure sign-in requires this portal to be opened using a trusted HTTPS address.</span>
        </section>
      </div>
    </React.StrictMode>,
  )
} else {
  const msalInstance = createMsalInstance()
  await msalInstance.initialize()
  const redirectResult = await msalInstance.handleRedirectPromise()
  if (redirectResult?.account) msalInstance.setActiveAccount(redirectResult.account)
  if (!msalInstance.getActiveAccount() && msalInstance.getAllAccounts().length === 1) {
    msalInstance.setActiveAccount(msalInstance.getAllAccounts()[0])
  }
  root.render(
    <React.StrictMode><MsalProvider instance={msalInstance}><App /></MsalProvider></React.StrictMode>,
  )
}

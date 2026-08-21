import { useEffect, useState } from 'react'
import { InteractionRequiredAuthError } from '@azure/msal-browser'
import { useIsAuthenticated, useMsal } from '@azure/msal-react'
import { useTranslation } from 'react-i18next'
import { BadgeCheck, Bell, BriefcaseBusiness, Building2, CalendarDays, CheckSquare, ChevronRight, CircleUserRound, FileUser, Gauge, Languages, LayoutDashboard, LogIn, LogOut, Settings, UsersRound } from 'lucide-react'
import { apiScope, authConfigured, loginRequest } from './auth'

const nav = [
  ['dashboard', LayoutDashboard], ['profile', CircleUserRound], ['leave', CalendarDays],
  ['approvals', CheckSquare], ['team', UsersRound], ['administration', Settings],
] as const

const cards = [
  ['employeeProfile', FileUser], ['jobDepartment', Building2], ['leaveBalance', CalendarDays],
  ['pendingApprovals', CheckSquare], ['employment', BriefcaseBusiness], ['quickLinks', Gauge],
] as const

export default function App() {
  const { t, i18n } = useTranslation()
  const { instance, accounts } = useMsal()
  const authenticated = useIsAuthenticated()
  const [displayName, setDisplayName] = useState(accounts[0]?.name || '')

  useEffect(() => {
    if (!authenticated) return
    const account = instance.getActiveAccount() || accounts[0]
    if (!account) return
    instance.setActiveAccount(account)
    void instance.acquireTokenSilent({ account, scopes: [apiScope] }).then(async result => {
      const response = await fetch('/api/v1/me', { headers: { Authorization: `Bearer ${result.accessToken}` } })
      if (response.ok) {
        const me = await response.json() as { name?: string }
        setDisplayName(me.name || account.name || '')
      }
    }).catch(error => {
      if (error instanceof InteractionRequiredAuthError) void instance.acquireTokenRedirect({ scopes: [apiScope] })
    })
  }, [accounts, authenticated, instance])

  const toggleLanguage = async () => {
    const language = i18n.language === 'en' ? 'ar' : 'en'
    await i18n.changeLanguage(language)
    document.documentElement.lang = language
    document.documentElement.dir = language === 'ar' ? 'rtl' : 'ltr'
  }
  if (!authenticated) return <div className="login-page"><section className="login-card"><span className="brand-mark">S</span><p>SSSA</p><h1>{t('portal')}</h1><span>{authConfigured ? t('signInDetail') : t('configurationMissing')}</span><button disabled={!authConfigured} onClick={() => void instance.loginRedirect(loginRequest)}><LogIn size={19}/>{t('signIn')}</button></section></div>

  const initials = (displayName || 'Employee').split(/\s+/).slice(0, 2).map(value => value[0]).join('').toUpperCase()
  return <div className="shell">
    <aside className="sidebar">
      <div className="brand"><span className="brand-mark">S</span><div><strong>SSSA</strong><small>{t('portal')}</small></div></div>
      <nav>{nav.map(([label, Icon], index) => <button className={index === 0 ? 'active' : ''} key={label}><Icon size={19}/><span>{t(label)}</span></button>)}</nav>
      <div className="security-note"><BadgeCheck size={19}/><span>Protected by Microsoft Entra ID</span></div>
    </aside>
    <main>
      <header><button className="language" onClick={toggleLanguage}><Languages size={18}/>{i18n.language === 'en' ? 'العربية' : 'English'}</button><button className="icon-button" aria-label="Notifications"><Bell size={19}/></button><button className="icon-button" aria-label={t('logout')} onClick={() => void instance.logoutRedirect()}><LogOut size={19}/></button><div className="avatar">{initials}</div></header>
      <section className="content">
        <div className="hero"><div><p>{t('welcome')}</p><h1>{displayName || 'Employee'}</h1><span>{t('overview')}</span></div><div className="hero-orbit"><span>SSSA</span></div></div>
        <div className="notice"><BadgeCheck/><div><strong>{t('secureFoundation')}</strong><p>{t('foundationDetail')}</p></div></div>
        <div className="grid">{cards.map(([label, Icon]) => <article key={label}><div className="card-icon"><Icon/></div><div><h2>{t(label)}</h2><p>{t('availableSoon')}</p></div><ChevronRight className="chevron" size={20}/></article>)}</div>
      </section>
    </main>
  </div>
}

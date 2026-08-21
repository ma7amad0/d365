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

type View = 'dashboard' | 'profile' | 'leave'

type EmployeeProfile = {
  personnelNumber: string
  displayName?: string | null
  email?: string | null
  phone?: string | null
  officeLocation?: string | null
  professionalTitle?: string | null
  legalEntity?: string | null
  employmentStartDate?: string | null
  employmentEndDate?: string | null
}

type LeaveBalance = {
  leaveType: string
  available?: string | null
  taken?: string | null
  total?: string | null
}

export default function App() {
  const { t, i18n } = useTranslation()
  const { instance, accounts } = useMsal()
  const authenticated = useIsAuthenticated()
  const [displayName, setDisplayName] = useState(accounts[0]?.name || '')
  const [authError, setAuthError] = useState('')
  const [mappingStatus, setMappingStatus] = useState('unknown')
  const [view, setView] = useState<View>('dashboard')
  const [profile, setProfile] = useState<EmployeeProfile | null>(null)
  const [profileLoading, setProfileLoading] = useState(false)
  const [profileError, setProfileError] = useState('')
  const [leaveBalances, setLeaveBalances] = useState<LeaveBalance[] | null>(null)
  const [leaveLoading, setLeaveLoading] = useState(false)
  const [leaveError, setLeaveError] = useState('')

  useEffect(() => {
    if (!authenticated) return
    const account = instance.getActiveAccount() || accounts[0]
    if (!account) return
    instance.setActiveAccount(account)
    void instance.acquireTokenSilent({ account, scopes: [apiScope] }).then(async result => {
      const response = await fetch('/api/v1/me', { headers: { Authorization: `Bearer ${result.accessToken}` } })
      if (response.ok) {
        const me = await response.json() as { name?: string, username?: string, mapping_status?: string }
        setDisplayName(me.name || account.name || me.username || '')
        setMappingStatus(me.mapping_status || 'unknown')
      }
    }).catch(async error => {
      if (!(error instanceof InteractionRequiredAuthError)) return
      try {
        await instance.acquireTokenPopup({ account, scopes: [apiScope] })
      } catch {
        setAuthError('Your session needs attention. Select sign in again to continue.')
      }
    })
  }, [accounts, authenticated, instance])

  const signIn = async () => {
    setAuthError('')
    try {
      const result = await instance.loginPopup(loginRequest)
      instance.setActiveAccount(result.account)
    } catch {
      setAuthError('Sign-in could not be completed. Allow pop-ups for this portal and try again.')
    }
  }

  const signOut = async () => {
    setAuthError('')
    try {
      await instance.logoutPopup({ account: instance.getActiveAccount() || accounts[0] })
    } catch {
      setAuthError('Sign-out could not be completed. Allow pop-ups for this portal and try again.')
    }
  }

  const showProfile = async () => {
    setView('profile')
    if (profile) return
    setProfileLoading(true)
    setProfileError('')
    const account = instance.getActiveAccount() || accounts[0]
    if (!account) {
      setProfileError(t('profileUnavailable'))
      setProfileLoading(false)
      return
    }
    try {
      const result = await instance.acquireTokenSilent({ account, scopes: [apiScope] })
      const response = await fetch('/api/v1/me/profile', {
        headers: { Authorization: `Bearer ${result.accessToken}` },
      })
      const body = await response.json() as { employee?: EmployeeProfile, message?: string }
      if (!response.ok || !body.employee) {
        setProfileError(body.message || t('profileUnavailable'))
        return
      }
      setProfile(body.employee)
      if (body.employee.displayName) setDisplayName(body.employee.displayName)
    } catch {
      setProfileError(t('profileUnavailable'))
    } finally {
      setProfileLoading(false)
    }
  }

  const showLeave = async () => {
    setView('leave')
    if (leaveBalances) return
    setLeaveLoading(true)
    setLeaveError('')
    const account = instance.getActiveAccount() || accounts[0]
    if (!account) {
      setLeaveError(t('leaveUnavailable'))
      setLeaveLoading(false)
      return
    }
    try {
      const result = await instance.acquireTokenSilent({ account, scopes: [apiScope] })
      const response = await fetch('/api/v1/me/leave-balances', {
        headers: { Authorization: `Bearer ${result.accessToken}` },
      })
      const body = await response.json() as { balances?: LeaveBalance[], message?: string }
      if (!response.ok || !body.balances) {
        setLeaveError(body.message || t('leaveUnavailable'))
        return
      }
      setLeaveBalances(body.balances)
    } catch {
      setLeaveError(t('leaveUnavailable'))
    } finally {
      setLeaveLoading(false)
    }
  }

  const toggleLanguage = async () => {
    const language = i18n.language === 'en' ? 'ar' : 'en'
    await i18n.changeLanguage(language)
    document.documentElement.lang = language
    document.documentElement.dir = language === 'ar' ? 'rtl' : 'ltr'
  }
  if (!authenticated) return <div className="login-page"><section className="login-card"><span className="brand-mark">S</span><p>SSSA</p><h1>{t('portal')}</h1><span>{authConfigured ? t('signInDetail') : t('configurationMissing')}</span>{authError && <span role="alert">{authError}</span>}<button disabled={!authConfigured} onClick={() => void signIn()}><LogIn size={19}/>{t('signIn')}</button></section></div>

  const initials = (displayName || 'Employee').split(/\s+/).slice(0, 2).map(value => value[0]).join('').toUpperCase()
  const profileFields: Array<[keyof EmployeeProfile, string]> = [
    ['personnelNumber', 'personnelNumber'], ['email', 'email'], ['phone', 'phone'],
    ['professionalTitle', 'professionalTitle'], ['officeLocation', 'officeLocation'],
    ['legalEntity', 'legalEntity'], ['employmentStartDate', 'employmentStartDate'],
    ['employmentEndDate', 'employmentEndDate'],
  ]
  return <div className="shell">
    <aside className="sidebar">
      <div className="brand"><span className="brand-mark">S</span><div><strong>SSSA</strong><small>{t('portal')}</small></div></div>
      <nav>{nav.map(([label, Icon]) => {
        const enabled = label === 'dashboard' || label === 'profile' || label === 'leave'
        const active = label === view
        const navigate = () => label === 'profile' ? void showProfile() : label === 'leave' ? void showLeave() : setView('dashboard')
        return <button className={active ? 'active' : ''} disabled={!enabled} key={label} onClick={navigate}><Icon size={19}/><span>{t(label)}</span></button>
      })}</nav>
      <div className="security-note"><BadgeCheck size={19}/><span>Protected by Microsoft Entra ID</span></div>
    </aside>
    <main>
      <header><button className="language" onClick={toggleLanguage}><Languages size={18}/>{i18n.language === 'en' ? 'العربية' : 'English'}</button><button className="icon-button" aria-label="Notifications"><Bell size={19}/></button><button className="icon-button" aria-label={t('logout')} onClick={() => void signOut()}><LogOut size={19}/></button><div className="avatar">{initials}</div></header>
      {view === 'dashboard' ? <section className="content">
        <div className="hero"><div><p>{t('welcome')}</p><h1>{displayName || 'Employee'}</h1><span>{t('overview')}</span></div><div className="hero-orbit"><span>SSSA</span></div></div>
        <div className="notice"><BadgeCheck/><div><strong>{t('secureFoundation')}</strong><p>{t(mappingStatus === 'verified' ? 'mappingVerified' : 'foundationDetail')}</p></div></div>
        <div className="grid">{cards.map(([label, Icon]) => {
          const profileCard = label === 'employeeProfile' || label === 'jobDepartment' || label === 'employment'
          const leaveCard = label === 'leaveBalance'
          const enabled = profileCard || leaveCard
          return <button className="dashboard-card" disabled={!enabled} key={label} onClick={() => leaveCard ? void showLeave() : void showProfile()}><div className="card-icon"><Icon/></div><div><h2>{t(label)}</h2><p>{t(enabled ? 'viewDetails' : 'availableSoon')}</p></div>{enabled && <ChevronRight className="chevron" size={20}/>}</button>
        })}</div>
      </section> : view === 'profile' ? <section className="content profile-page">
        <div className="page-heading"><div><p>{t('employeeProfile')}</p><h1>{profile?.displayName || displayName || t('profile')}</h1></div><button onClick={() => setView('dashboard')}>{t('backToDashboard')}</button></div>
        {profileLoading && <div className="profile-state">{t('loadingProfile')}</div>}
        {profileError && <div className="profile-state error" role="alert"><strong>{t('profileUnavailable')}</strong><p>{profileError}</p>{mappingStatus !== 'verified' && <p>{t('mappingRequired')}</p>}<button onClick={() => { setProfileError(''); void showProfile() }}>{t('tryAgain')}</button></div>}
        {profile && <div className="profile-panel"><div className="profile-summary"><div className="profile-avatar">{initials}</div><div><h2>{profile.displayName || displayName}</h2><p>{profile.professionalTitle || t('employee')}</p></div></div><dl>{profileFields.map(([field, label]) => <div key={field}><dt>{t(label)}</dt><dd>{profile[field] || '—'}</dd></div>)}</dl></div>}
      </section> : <section className="content leave-page">
        <div className="page-heading"><div><p>{t('leave')}</p><h1>{t('leaveBalances')}</h1></div><button onClick={() => setView('dashboard')}>{t('backToDashboard')}</button></div>
        {leaveLoading && <div className="profile-state">{t('loadingLeave')}</div>}
        {leaveError && <div className="profile-state error" role="alert"><strong>{t('leaveUnavailable')}</strong><p>{leaveError}</p><button onClick={() => { setLeaveError(''); void showLeave() }}>{t('tryAgain')}</button></div>}
        {leaveBalances && leaveBalances.length === 0 && <div className="profile-state">{t('noLeaveBalances')}</div>}
        {leaveBalances && leaveBalances.length > 0 && <div className="leave-grid">{leaveBalances.map(balance => <article key={balance.leaveType}><div className="leave-type"><CalendarDays/><div><span>{t('leaveType')}</span><h2>{balance.leaveType}</h2></div></div><div className="balance-available"><strong>{balance.available ?? '—'}</strong><span>{t('availableBalance')}</span></div><dl><div><dt>{t('usedLeave')}</dt><dd>{balance.taken ?? '—'}</dd></div><div><dt>{t('totalEntitlement')}</dt><dd>{balance.total ?? '—'}</dd></div></dl></article>)}</div>}
      </section>}
    </main>
  </div>
}

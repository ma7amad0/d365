import { useTranslation } from 'react-i18next'
import { BadgeCheck, Bell, BriefcaseBusiness, Building2, CalendarDays, CheckSquare, ChevronRight, CircleUserRound, FileUser, Gauge, Languages, LayoutDashboard, Settings, UsersRound } from 'lucide-react'

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
  const toggleLanguage = async () => {
    const language = i18n.language === 'en' ? 'ar' : 'en'
    await i18n.changeLanguage(language)
    document.documentElement.lang = language
    document.documentElement.dir = language === 'ar' ? 'rtl' : 'ltr'
  }
  return <div className="shell">
    <aside className="sidebar">
      <div className="brand"><span className="brand-mark">S</span><div><strong>SSSA</strong><small>{t('portal')}</small></div></div>
      <nav>{nav.map(([label, Icon], index) => <button className={index === 0 ? 'active' : ''} key={label}><Icon size={19}/><span>{t(label)}</span></button>)}</nav>
      <div className="security-note"><BadgeCheck size={19}/><span>Protected by Microsoft Entra ID</span></div>
    </aside>
    <main>
      <header><button className="language" onClick={toggleLanguage}><Languages size={18}/>{i18n.language === 'en' ? 'العربية' : 'English'}</button><button className="icon-button" aria-label="Notifications"><Bell size={19}/></button><div className="avatar">MH</div></header>
      <section className="content">
        <div className="hero"><div><p>{t('welcome')}</p><h1>Mohammed</h1><span>{t('overview')}</span></div><div className="hero-orbit"><span>SSSA</span></div></div>
        <div className="notice"><BadgeCheck/><div><strong>{t('secureFoundation')}</strong><p>{t('foundationDetail')}</p></div></div>
        <div className="grid">{cards.map(([label, Icon]) => <article key={label}><div className="card-icon"><Icon/></div><div><h2>{t(label)}</h2><p>{t('availableSoon')}</p></div><ChevronRight className="chevron" size={20}/></article>)}</div>
      </section>
    </main>
  </div>
}


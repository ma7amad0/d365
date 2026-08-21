import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

const resources = {
  en: { translation: {
    portal: 'Employee Portal', welcome: 'Welcome back', overview: 'Your workday at a glance',
    dashboard: 'Dashboard', profile: 'My Profile', leave: 'Leave', approvals: 'Approvals',
    team: 'My Team', administration: 'Administration', employeeProfile: 'Employee profile',
    jobDepartment: 'Job & department', leaveBalance: 'Leave balance', pendingApprovals: 'Pending approvals',
    employment: 'Employment', quickLinks: 'Quick links', availableSoon: 'Available after secure sign-in',
    secureFoundation: 'Secure portal foundation is ready', foundationDetail: 'Entra SSO and employee data will be enabled in the next milestone.',
  }},
  ar: { translation: {
    portal: 'بوابة الموظفين', welcome: 'مرحباً بعودتك', overview: 'نظرة سريعة على يوم عملك',
    dashboard: 'الرئيسية', profile: 'ملفي الشخصي', leave: 'الإجازات', approvals: 'الموافقات',
    team: 'فريقي', administration: 'الإدارة', employeeProfile: 'ملف الموظف',
    jobDepartment: 'الوظيفة والقسم', leaveBalance: 'رصيد الإجازات', pendingApprovals: 'الموافقات المعلقة',
    employment: 'بيانات التوظيف', quickLinks: 'روابط سريعة', availableSoon: 'متاح بعد تسجيل الدخول الآمن',
    secureFoundation: 'البنية الآمنة للبوابة جاهزة', foundationDetail: 'سيتم تفعيل الدخول الموحد وبيانات الموظفين في المرحلة التالية.',
  }},
}

void i18n.use(initReactI18next).init({ resources, lng: 'en', fallbackLng: 'en', interpolation: { escapeValue: false } })
export default i18n


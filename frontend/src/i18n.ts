import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

const resources = {
  en: { translation: {
    portal: 'Employee Portal', welcome: 'Welcome back', overview: 'Your workday at a glance',
    dashboard: 'Dashboard', profile: 'My Profile', leave: 'Leave', approvals: 'Approvals',
    team: 'My Team', administration: 'Administration', employeeProfile: 'Employee profile',
    jobDepartment: 'Job & department', leaveBalance: 'Leave balance', pendingApprovals: 'Pending approvals',
    employment: 'Employment', quickLinks: 'Quick links', availableSoon: 'Available after secure sign-in',
    secureFoundation: 'Secure sign-in is active', foundationDetail: 'Employee data appears after your identity mapping is verified.',
    signIn: 'Sign in with Microsoft', signInDetail: 'Use your organization account to continue securely.',
    configurationMissing: 'Microsoft Entra configuration is missing from this deployment.', logout: 'Sign out',
  }},
  ar: { translation: {
    portal: 'بوابة الموظفين', welcome: 'مرحباً بعودتك', overview: 'نظرة سريعة على يوم عملك',
    dashboard: 'الرئيسية', profile: 'ملفي الشخصي', leave: 'الإجازات', approvals: 'الموافقات',
    team: 'فريقي', administration: 'الإدارة', employeeProfile: 'ملف الموظف',
    jobDepartment: 'الوظيفة والقسم', leaveBalance: 'رصيد الإجازات', pendingApprovals: 'الموافقات المعلقة',
    employment: 'بيانات التوظيف', quickLinks: 'روابط سريعة', availableSoon: 'متاح بعد تسجيل الدخول الآمن',
    secureFoundation: 'تسجيل الدخول الآمن مفعّل', foundationDetail: 'تظهر بيانات الموظف بعد التحقق من ربط الهوية.',
    signIn: 'تسجيل الدخول باستخدام Microsoft', signInDetail: 'استخدم حساب المؤسسة للمتابعة بأمان.',
    configurationMissing: 'إعدادات Microsoft Entra غير موجودة في هذا النشر.', logout: 'تسجيل الخروج',
  }},
}

void i18n.use(initReactI18next).init({ resources, lng: 'en', fallbackLng: 'en', interpolation: { escapeValue: false } })
export default i18n

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
    mappingVerified: 'Your verified employee profile is ready.', viewDetails: 'View your verified details',
    backToDashboard: 'Back to dashboard', loadingProfile: 'Loading your employee profile…',
    profileUnavailable: 'Employee profile unavailable', mappingRequired: 'An administrator must verify your Entra-to-D365 employee mapping.',
    tryAgain: 'Try again', employee: 'Employee', personnelNumber: 'Personnel number', email: 'Email', phone: 'Phone',
    professionalTitle: 'Professional title', officeLocation: 'Office location', legalEntity: 'Legal entity',
    employmentStartDate: 'Employment start date', employmentEndDate: 'Employment end date',
    leaveBalances: 'My leave balances', loadingLeave: 'Loading your leave balances…',
    leaveUnavailable: 'Leave balances unavailable', noLeaveBalances: 'No leave balances were returned for your employee record.',
    leaveType: 'Leave type', availableBalance: 'Available balance', usedLeave: 'Used this year',
    totalEntitlement: 'Total this year',
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
    mappingVerified: 'ملف الموظف الموثق جاهز.', viewDetails: 'عرض بياناتك الموثقة',
    backToDashboard: 'العودة إلى الرئيسية', loadingProfile: 'جارٍ تحميل ملف الموظف…',
    profileUnavailable: 'ملف الموظف غير متاح', mappingRequired: 'يجب أن يتحقق المسؤول من ربط حساب Entra بسجل الموظف في D365.',
    tryAgain: 'إعادة المحاولة', employee: 'موظف', personnelNumber: 'الرقم الوظيفي', email: 'البريد الإلكتروني', phone: 'الهاتف',
    professionalTitle: 'المسمى الوظيفي', officeLocation: 'موقع المكتب', legalEntity: 'الجهة القانونية',
    employmentStartDate: 'تاريخ بدء التوظيف', employmentEndDate: 'تاريخ انتهاء التوظيف',
    leaveBalances: 'أرصدة إجازاتي', loadingLeave: 'جارٍ تحميل أرصدة الإجازات…',
    leaveUnavailable: 'أرصدة الإجازات غير متاحة', noLeaveBalances: 'لم يتم العثور على أرصدة إجازات لسجل الموظف.',
    leaveType: 'نوع الإجازة', availableBalance: 'الرصيد المتاح', usedLeave: 'المستخدم هذا العام',
    totalEntitlement: 'الإجمالي هذا العام',
  }},
}

void i18n.use(initReactI18next).init({ resources, lng: 'en', fallbackLng: 'en', interpolation: { escapeValue: false } })
export default i18n

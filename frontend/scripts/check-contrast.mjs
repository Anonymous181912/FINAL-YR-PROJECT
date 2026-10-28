/**
 * WCAG 2.1 Contrast Checker for Design System Tokens
 * Checks all defined text/background token pairs in light and dark themes.
 * Fails if any normal text pair < 4.5:1 or large/component pair < 3.0:1.
 */

function parseHex(hex) {
  hex = hex.replace('#', '').trim();
  if (hex.length === 3) {
    hex = hex.split('').map(c => c + c).join('');
  }
  const r = parseInt(hex.substring(0, 2), 16);
  const g = parseInt(hex.substring(2, 4), 16);
  const b = parseInt(hex.substring(4, 6), 16);
  return { r, g, b };
}

function sRGBtoLin(colorChannel) {
  const c = colorChannel / 255;
  return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
}

function relativeLuminance({ r, g, b }) {
  return 0.2126 * sRGBtoLin(r) + 0.7152 * sRGBtoLin(g) + 0.0722 * sRGBtoLin(b);
}

function contrastRatio(hex1, hex2) {
  const lum1 = relativeLuminance(parseHex(hex1));
  const lum2 = relativeLuminance(parseHex(hex2));
  const brightest = Math.max(lum1, lum2);
  const darkest = Math.min(lum1, lum2);
  return (brightest + 0.05) / (darkest + 0.05);
}

const lightTokens = {
  bg: '#F5F7FA',
  surface: '#FFFFFF',
  surface2: '#F1F4F9',
  border: '#E3E8EF',
  text: '#0F172A',
  textMuted: '#475569',
  textSubtle: '#5F6F86',
  accentPatient: '#0F766E',
  accentDoctor: '#4338CA',
  accentAdmin: '#B45309',
  onAccent: '#FFFFFF',
  statusSuccessFg: '#166534',
  statusSuccessBg: '#F0FDF4',
  statusWarningFg: '#92400E',
  statusWarningBg: '#FFFBEB',
  statusDangerFg: '#991B1B',
  statusDangerBg: '#FEF2F2',
  statusInfoFg: '#1E40AF',
  statusInfoBg: '#EFF6FF',
  sidebarBg: '#0B1B2B',
  sidebarText: '#F8FAFC',
  sidebarTextMuted: '#94A3B8',
};

const darkTokens = {
  bg: '#0A0F1C',
  surface: '#111827',
  surface2: '#182235',
  border: '#263247',
  text: '#E8EEF7',
  textMuted: '#A7B4C7',
  textSubtle: '#8493A8',
  accentPatient: '#2DD4BF',
  accentDoctor: '#818CF8',
  accentAdmin: '#FBBF24',
  onAccent: '#0F172A',
  statusSuccessFg: '#4ADE80',
  statusSuccessBg: '#052E16',
  statusWarningFg: '#FCD34D',
  statusWarningBg: '#451A03',
  statusDangerFg: '#FCA5A5',
  statusDangerBg: '#450A0A',
  statusInfoFg: '#93C5FD',
  statusInfoBg: '#172554',
  sidebarBg: '#0B1B2B',
  sidebarText: '#F8FAFC',
  sidebarTextMuted: '#94A3B8',
};

// Fixed tokens used by public pages (landing + auth) and the portal chrome.
// These must never change with the OS theme.
const fixedTokens = {
  white: '#FFFFFF',
  authSurface: '#FFFFFF',
  authInput: '#F8FAFC',
  authText: '#0F172A',
  authLabel: '#475569',
  authMuted: '#64748B',
  authError: '#B91C1C',
  authErrorBg: '#FEF2F2',
  authNotice: '#0F766E',
  authNoticeBg: '#F0FDFA',
  authLinkPatient: '#0F766E',
  authLinkDoctor: '#0369A1',

  tealBtnStart: '#0F766E',
  tealBtnEnd: '#115E59',
  blueBtnStart: '#0369A1',
  blueBtnEnd: '#1E40AF',
  navyBtnStart: '#1E3A5F',
  navyBtnEnd: '#0F172A',

  heroBody: '#E6EEED',
  patientHeroStart: '#0F766E',
  patientHeroEnd: '#115E59',
  patientHeroMuted: '#CCFBF1',
  doctorHeroStart: '#0369A1',
  doctorHeroEnd: '#1E40AF',
  doctorHeroMuted: '#DBEAFE',
  adminHeroStart: '#1E3A5F',
  adminHeroEnd: '#0F172A',
  adminHeroMuted: '#FDE68A',

  patientSidebarStart: '#115E59',
  patientSidebarEnd: '#134E4A',
  patientSidebarMuted: '#99F6E4',
  doctorSidebarStart: '#1E3A5F',
  doctorSidebarEnd: '#1E40AF',
  doctorSidebarMuted: '#BFDBFE',
  adminSidebarStart: '#1E3A5F',
  adminSidebarEnd: '#0F172A',
  adminSidebarMuted: '#CBD5E1',

  landingBg: '#F5F7FA',
  landingSurface: '#FFFFFF',
  landingSurface2: '#F8FAFC',
  landingTeal50: '#F0FDFA',
  landingBlue50: '#EFF6FF',
  landingAmber50: '#FFFBEB',
  landingText: '#0F172A',
  landingMuted: '#475569',
  landingTeal: '#0F766E',
  landingBlue: '#0369A1',
  landingAmber: '#B45309',
  landingFooterBg: '#0F172A',
  landingFooterText: '#CBD5E1',
  landingFooterMuted: '#94A3B8',
};

const checks = [
  // Light Theme Checks
  { theme: 'light', fg: 'text', bg: 'bg', min: 4.5 },
  { theme: 'light', fg: 'textMuted', bg: 'bg', min: 4.5 },
  { theme: 'light', fg: 'textSubtle', bg: 'bg', min: 4.5 },
  { theme: 'light', fg: 'text', bg: 'surface', min: 4.5 },
  { theme: 'light', fg: 'textMuted', bg: 'surface', min: 4.5 },
  { theme: 'light', fg: 'textSubtle', bg: 'surface', min: 4.5 },
  { theme: 'light', fg: 'text', bg: 'surface2', min: 4.5 },
  { theme: 'light', fg: 'textMuted', bg: 'surface2', min: 4.5 },
  { theme: 'light', fg: 'onAccent', bg: 'accentPatient', min: 4.5 },
  { theme: 'light', fg: 'onAccent', bg: 'accentDoctor', min: 4.5 },
  { theme: 'light', fg: 'onAccent', bg: 'accentAdmin', min: 4.5 },
  { theme: 'light', fg: 'statusSuccessFg', bg: 'statusSuccessBg', min: 4.5 },
  { theme: 'light', fg: 'statusWarningFg', bg: 'statusWarningBg', min: 4.5 },
  { theme: 'light', fg: 'statusDangerFg', bg: 'statusDangerBg', min: 4.5 },
  { theme: 'light', fg: 'statusInfoFg', bg: 'statusInfoBg', min: 4.5 },
  { theme: 'light', fg: 'sidebarText', bg: 'sidebarBg', min: 4.5 },
  { theme: 'light', fg: 'sidebarTextMuted', bg: 'sidebarBg', min: 4.5 },

  // Dark Theme Checks
  { theme: 'dark', fg: 'text', bg: 'bg', min: 4.5 },
  { theme: 'dark', fg: 'textMuted', bg: 'bg', min: 4.5 },
  { theme: 'dark', fg: 'textSubtle', bg: 'bg', min: 4.5 },
  { theme: 'dark', fg: 'text', bg: 'surface', min: 4.5 },
  { theme: 'dark', fg: 'textMuted', bg: 'surface', min: 4.5 },
  { theme: 'dark', fg: 'textSubtle', bg: 'surface', min: 4.5 },
  { theme: 'dark', fg: 'text', bg: 'surface2', min: 4.5 },
  { theme: 'dark', fg: 'textMuted', bg: 'surface2', min: 4.5 },
  { theme: 'dark', fg: 'onAccent', bg: 'accentPatient', min: 4.5 },
  { theme: 'dark', fg: 'onAccent', bg: 'accentDoctor', min: 4.5 },
  { theme: 'dark', fg: 'onAccent', bg: 'accentAdmin', min: 4.5 },
  { theme: 'dark', fg: 'statusSuccessFg', bg: 'statusSuccessBg', min: 4.5 },
  { theme: 'dark', fg: 'statusWarningFg', bg: 'statusWarningBg', min: 4.5 },
  { theme: 'dark', fg: 'statusDangerFg', bg: 'statusDangerBg', min: 4.5 },
  { theme: 'dark', fg: 'statusInfoFg', bg: 'statusInfoBg', min: 4.5 },
  { theme: 'dark', fg: 'sidebarText', bg: 'sidebarBg', min: 4.5 },
  { theme: 'dark', fg: 'sidebarTextMuted', bg: 'sidebarBg', min: 4.5 },
  { theme: 'light', fg: 'textMuted', bg: 'surface2', min: 4.5 },
  { theme: 'light', fg: 'textSubtle', bg: 'surface2', min: 4.5 },
  { theme: 'dark', fg: 'textMuted', bg: 'surface2', min: 4.5 },
  { theme: 'dark', fg: 'textSubtle', bg: 'surface2', min: 4.5 },

  // Auth pages (login + register): fixed white form pane, dark text, light inputs
  { theme: 'fixed', fg: 'authText', bg: 'authSurface', min: 4.5 },
  { theme: 'fixed', fg: 'authLabel', bg: 'authSurface', min: 4.5 },
  { theme: 'fixed', fg: 'authMuted', bg: 'authSurface', min: 4.5 },
  { theme: 'fixed', fg: 'authText', bg: 'authInput', min: 4.5 },
  { theme: 'fixed', fg: 'authMuted', bg: 'authInput', min: 4.5 },
  { theme: 'fixed', fg: 'authLinkPatient', bg: 'authSurface', min: 4.5 },
  { theme: 'fixed', fg: 'authLinkDoctor', bg: 'authSurface', min: 4.5 },
  { theme: 'fixed', fg: 'authError', bg: 'authErrorBg', min: 4.5 },
  { theme: 'fixed', fg: 'authNotice', bg: 'authNoticeBg', min: 4.5 },

  // Auth buttons and left brand panels (white text on solid gradients)
  { theme: 'fixed', fg: 'white', bg: 'tealBtnStart', min: 4.5 },
  { theme: 'fixed', fg: 'white', bg: 'tealBtnEnd', min: 4.5 },
  { theme: 'fixed', fg: 'white', bg: 'blueBtnStart', min: 4.5 },
  { theme: 'fixed', fg: 'white', bg: 'blueBtnEnd', min: 4.5 },
  { theme: 'fixed', fg: 'white', bg: 'navyBtnStart', min: 4.5 },
  { theme: 'fixed', fg: 'white', bg: 'navyBtnEnd', min: 4.5 },
  { theme: 'fixed', fg: 'white', bg: 'patientHeroStart', min: 4.5 },
  { theme: 'fixed', fg: 'white', bg: 'patientHeroEnd', min: 4.5 },
  { theme: 'fixed', fg: 'patientHeroMuted', bg: 'patientHeroStart', min: 4.5 },
  { theme: 'fixed', fg: 'patientHeroMuted', bg: 'patientHeroEnd', min: 4.5 },
  { theme: 'fixed', fg: 'heroBody', bg: 'patientHeroStart', min: 4.5 },
  { theme: 'fixed', fg: 'heroBody', bg: 'patientHeroEnd', min: 4.5 },
  { theme: 'fixed', fg: 'white', bg: 'doctorHeroStart', min: 4.5 },
  { theme: 'fixed', fg: 'white', bg: 'doctorHeroEnd', min: 4.5 },
  { theme: 'fixed', fg: 'doctorHeroMuted', bg: 'doctorHeroStart', min: 4.5 },
  { theme: 'fixed', fg: 'doctorHeroMuted', bg: 'doctorHeroEnd', min: 4.5 },
  { theme: 'fixed', fg: 'heroBody', bg: 'doctorHeroStart', min: 4.5 },
  { theme: 'fixed', fg: 'heroBody', bg: 'doctorHeroEnd', min: 4.5 },
  { theme: 'fixed', fg: 'white', bg: 'adminHeroStart', min: 4.5 },
  { theme: 'fixed', fg: 'white', bg: 'adminHeroEnd', min: 4.5 },
  { theme: 'fixed', fg: 'adminHeroMuted', bg: 'adminHeroStart', min: 4.5 },
  { theme: 'fixed', fg: 'adminHeroMuted', bg: 'adminHeroEnd', min: 4.5 },
  { theme: 'fixed', fg: 'heroBody', bg: 'adminHeroStart', min: 4.5 },
  { theme: 'fixed', fg: 'heroBody', bg: 'adminHeroEnd', min: 4.5 },

  // Dashboard portal chrome: patient teal, doctor blue, admin navy sidebars
  { theme: 'fixed', fg: 'white', bg: 'patientSidebarStart', min: 4.5 },
  { theme: 'fixed', fg: 'white', bg: 'patientSidebarEnd', min: 4.5 },
  { theme: 'fixed', fg: 'patientSidebarMuted', bg: 'patientSidebarStart', min: 4.5 },
  { theme: 'fixed', fg: 'patientSidebarMuted', bg: 'patientSidebarEnd', min: 4.5 },
  { theme: 'fixed', fg: 'white', bg: 'doctorSidebarStart', min: 4.5 },
  { theme: 'fixed', fg: 'white', bg: 'doctorSidebarEnd', min: 4.5 },
  { theme: 'fixed', fg: 'doctorSidebarMuted', bg: 'doctorSidebarStart', min: 4.5 },
  { theme: 'fixed', fg: 'doctorSidebarMuted', bg: 'doctorSidebarEnd', min: 4.5 },
  { theme: 'fixed', fg: 'white', bg: 'adminSidebarStart', min: 4.5 },
  { theme: 'fixed', fg: 'white', bg: 'adminSidebarEnd', min: 4.5 },
  { theme: 'fixed', fg: 'adminSidebarMuted', bg: 'adminSidebarStart', min: 4.5 },
  { theme: 'fixed', fg: 'adminSidebarMuted', bg: 'adminSidebarEnd', min: 4.5 },

  // Landing page (fixed light content + dark footer)
  { theme: 'fixed', fg: 'landingText', bg: 'landingBg', min: 4.5 },
  { theme: 'fixed', fg: 'landingText', bg: 'landingSurface', min: 4.5 },
  { theme: 'fixed', fg: 'landingText', bg: 'landingSurface2', min: 4.5 },
  { theme: 'fixed', fg: 'landingText', bg: 'landingTeal50', min: 4.5 },
  { theme: 'fixed', fg: 'landingText', bg: 'landingBlue50', min: 4.5 },
  { theme: 'fixed', fg: 'landingText', bg: 'landingAmber50', min: 4.5 },
  { theme: 'fixed', fg: 'landingMuted', bg: 'landingBg', min: 4.5 },
  { theme: 'fixed', fg: 'landingMuted', bg: 'landingSurface', min: 4.5 },
  { theme: 'fixed', fg: 'landingMuted', bg: 'landingSurface2', min: 4.5 },
  { theme: 'fixed', fg: 'landingMuted', bg: 'landingTeal50', min: 4.5 },
  { theme: 'fixed', fg: 'landingMuted', bg: 'landingBlue50', min: 4.5 },
  { theme: 'fixed', fg: 'landingMuted', bg: 'landingAmber50', min: 4.5 },
  { theme: 'fixed', fg: 'landingTeal', bg: 'landingTeal50', min: 4.5 },
  { theme: 'fixed', fg: 'landingBlue', bg: 'landingBlue50', min: 4.5 },
  { theme: 'fixed', fg: 'landingAmber', bg: 'landingAmber50', min: 4.5 },
  { theme: 'fixed', fg: 'landingFooterText', bg: 'landingFooterBg', min: 4.5 },
  { theme: 'fixed', fg: 'landingFooterMuted', bg: 'landingFooterBg', min: 4.5 },
];

let failures = 0;
console.log('--- WCAG 2.1 Contrast Ratio Verification ---');

for (const check of checks) {
  const tokenSet = check.theme === 'light'
    ? lightTokens
    : check.theme === 'dark'
      ? darkTokens
      : fixedTokens;
  const fgColor = tokenSet[check.fg];
  const bgColor = tokenSet[check.bg];
  const ratio = contrastRatio(fgColor, bgColor);
  const passed = ratio >= check.min;
  const formattedRatio = ratio.toFixed(2) + ':1';

  if (!passed) {
    failures++;
    console.error(`❌ [${check.theme.toUpperCase()}] ${check.fg} (${fgColor}) on ${check.bg} (${bgColor}) -> ${formattedRatio} (Required >= ${check.min}:1)`);
  } else {
    console.log(`✅ [${check.theme.toUpperCase()}] ${check.fg} (${fgColor}) on ${check.bg} (${bgColor}) -> ${formattedRatio} >= ${check.min}:1`);
  }
}

console.log('--------------------------------------------');
if (failures > 0) {
  console.error(`Contrast check FAILED with ${failures} violations.`);
  process.exit(1);
} else {
  console.log(`All ${checks.length} token pairs PASSED WCAG 2.1 AA requirements.`);
  process.exit(0);
}

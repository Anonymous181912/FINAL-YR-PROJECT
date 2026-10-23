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
];

let failures = 0;
console.log('--- WCAG 2.1 Contrast Ratio Verification ---');

for (const check of checks) {
  const tokenSet = check.theme === 'light' ? lightTokens : darkTokens;
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

import * as React from 'react'
import { Outlet, NavLink, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../auth.jsx'
import {
  LayoutDashboard,
  FileText,
  Pill,
  Users,
  Clock,
  LogOut,
  Sparkles,
  ShieldCheck,
  Stethoscope,
  User as UserIcon,
  Menu,
  X,
  UserRound,
  History as HistoryIcon,
  KeyRound,
  Bell,
  Sun,
  Moon,
  Laptop,
  Search,
  ChevronLeft,
  ChevronRight,
  TrendingUp,
  Activity,
  FileCheck2,
  UploadCloud,
} from 'lucide-react'
import { listNotifications, markNotificationRead, markAllNotificationsRead } from '../services/notifications'
import { GlobalSearch } from '../components/GlobalSearch'
import { Avatar } from '../components/ui/Avatar'
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
} from '../components/ui/DropdownMenu'

export function NotificationBell() {
  const [open, setOpen] = React.useState(false)
  const [items, setItems] = React.useState([])
  const unread = items.filter((n) => !n.is_read).length

  const refresh = async () => {
    try {
      const data = await listNotifications()
      setItems(data || [])
    } catch {
      /* backend quiet */
    }
  }

  React.useEffect(() => {
    refresh()
    const t = setInterval(refresh, 120000)
    return () => clearInterval(t)
  }, [])

  const handleRead = async (id) => {
    try {
      await markNotificationRead(id)
      setItems((prev) => prev.map((n) => (n.id === id ? { ...n, is_read: true } : n)))
    } catch { /* ignore */ }
  }

  const handleReadAll = async () => {
    try {
      await markAllNotificationsRead()
      setItems((prev) => prev.map((n) => ({ ...n, is_read: true })))
    } catch { /* ignore */ }
  }

  return (
    <div className="relative">
      <button
        onClick={() => { setOpen(!open); if (!open) refresh() }}
        aria-label={`Notifications${unread ? `, ${unread} unread` : ''}`}
        title="Notifications"
        className="relative p-2 rounded-item hover:bg-surface-2 text-foreground-muted hover:text-foreground transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
      >
        <Bell className="w-5 h-5" />
        {unread > 0 && (
          <span className="absolute top-1 right-1 bg-primary-500 text-white rounded-full text-[10px] font-bold px-1 min-w-[16px] h-4 flex items-center justify-center leading-none">
            {unread > 9 ? '9+' : unread}
          </span>
        )}
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-12 w-80 max-h-96 overflow-y-auto bg-surface text-foreground border border-border rounded-card shadow-dropdown z-50 p-3 animate-in fade-in-0 zoom-in-95">
            <div className="flex justify-between items-center pb-2 mb-2 border-b border-border">
              <div className="text-sm font-bold font-heading">Notifications</div>
              {unread > 0 && (
                <button
                  onClick={handleReadAll}
                  className="text-xs text-primary-500 hover:underline font-medium"
                >
                  Mark all read
                </button>
              )}
            </div>

            {items.length === 0 ? (
              <div className="py-6 text-center text-xs text-foreground-muted">
                No notifications right now.
              </div>
            ) : (
              <div className="space-y-2">
                {items.slice(0, 20).map((n) => (
                  <div
                    key={n.id}
                    className={`p-2.5 rounded-item text-xs transition-colors border ${
                      n.is_read
                        ? 'bg-transparent border-transparent text-foreground-muted'
                        : 'bg-primary-50 dark:bg-primary-900/20 border-primary-100 dark:border-primary-800 text-foreground'
                    }`}
                  >
                    <div className="font-semibold text-foreground">{n.title}</div>
                    {n.body && <div className="text-foreground-subtle mt-0.5">{n.body}</div>}
                    {!n.is_read && (
                      <button
                        onClick={() => handleRead(n.id)}
                        className="text-[11px] text-primary-500 font-semibold mt-1 hover:underline"
                      >
                        Mark as read
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}

export function ThemeToggle({ theme, onThemeChange }) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          aria-label="Toggle theme"
          className="p-2 rounded-item hover:bg-surface-2 text-foreground-muted hover:text-foreground transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
        >
          {theme === 'dark' ? (
            <Moon className="w-5 h-5 text-primary-500" />
          ) : theme === 'light' ? (
            <Sun className="w-5 h-5 text-primary-500" />
          ) : (
            <Laptop className="w-5 h-5" />
          )}
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onClick={() => onThemeChange('light')}>
          <Sun className="w-4 h-4 mr-2" />
          <span>Light</span>
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => onThemeChange('dark')}>
          <Moon className="w-4 h-4 mr-2" />
          <span>Dark</span>
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => onThemeChange('system')}>
          <Laptop className="w-4 h-4 mr-2" />
          <span>System</span>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

export default function DoctorLayout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  
  const [collapsed, setCollapsed] = React.useState(false)
  const [mobileDrawerOpen, setMobileDrawerOpen] = React.useState(false)
  const [searchOpen, setSearchOpen] = React.useState(false)

  // 3-state Theme: system | light | dark
  const [themePreference, setThemePreference] = React.useState(() => {
    try {
      return localStorage.getItem('theme_pref') || 'system'
    } catch {
      return 'system'
    }
  })

  // Synchronize actual theme class/attribute on html root
  React.useEffect(() => {
    const root = document.documentElement
    const applyTheme = (isDark) => {
      if (isDark) {
        root.setAttribute('data-theme', 'dark')
        root.classList.add('dark')
      } else {
        root.setAttribute('data-theme', 'light')
        root.classList.remove('dark')
      }
    }

    if (themePreference === 'system') {
      const media = window.matchMedia('(prefers-color-scheme: dark)')
      applyTheme(media.matches)
      const listener = (e) => applyTheme(e.matches)
      media.addEventListener('change', listener)
      return () => media.removeEventListener('change', listener)
    } else {
      applyTheme(themePreference === 'dark')
    }

    try {
      localStorage.setItem('theme_pref', themePreference)
    } catch { /* ignore */ }
  }, [themePreference])

  // Synchronize role attribute on html root for semantic accent variables
  React.useEffect(() => {
    document.documentElement.setAttribute('data-role', 'doctor')
  }, [])

  // Global Ctrl+K / Cmd+K listener
  React.useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setSearchOpen((prev) => !prev)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  const handleLogout = () => {
    logout()
    navigate('/doctor/login')
  }

  // Doctor Navigation
  const doctorNav = [
    { to: '/doctor/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/doctor/patients', label: 'Patients', icon: Users },
    { to: '/doctor/prescriptions?new=1', label: 'Write Prescription', icon: Pill },
    { to: '/doctor/prescriptions', label: 'Prescriptions', icon: FileText },
    { to: '/doctor/reports', label: 'Reports', icon: FileText },
    { to: '/doctor/access', label: 'Access Requests', icon: ShieldCheck },
    { to: '/doctor/profile', label: 'My Profile', icon: UserRound },
  ]

  const getPageTitle = () => {
    const path = location.pathname
    if (path.startsWith('/doctor/reports/')) return 'Report Details'
    if (path === '/doctor/reports') return 'Patient Reports'
    if (path === '/doctor/patients') return 'Patient Directory'
    if (path === '/doctor/prescriptions') {
      return location.search.includes('new=1') ? 'Write Prescription' : 'Prescriptions'
    }
    if (path === '/doctor/history') return 'Patient Timeline'
    if (path === '/doctor/access') return 'Access Requests'
    if (path === '/doctor/profile') return 'Doctor Profile'
    return 'Dashboard'
  }

  return (
    <div className="min-h-screen flex bg-background text-foreground" data-portal="doctor">
      {/* Accessibility skip to content */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:p-4 focus:bg-primary-500 focus:text-white focus:rounded-md m-2"
      >
        Skip to main content
      </a>

      {/* Global Search Dialog */}
      <GlobalSearch
        open={searchOpen}
        onOpenChange={setSearchOpen}
        userRole="doctor"
      />

      {/* Mobile Drawer Overlay */}
      {mobileDrawerOpen && (
        <div
          className="fixed inset-0 bg-black/60 z-40 md:hidden backdrop-blur-sm"
          onClick={() => setMobileDrawerOpen(false)}
        />
      )}

      {/* Sidebar - Doctor Blue Theme */}
      <aside
        className={`fixed md:sticky top-0 h-screen z-50 flex flex-col bg-primary-900 text-primary-50 border-r border-primary-800 transition-all duration-300 ease-in-out ${
          collapsed ? 'w-[72px]' : 'w-[264px]'
        } ${mobileDrawerOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}`}
        style={{ background: 'linear-gradient(180deg, #1e3a5f 0%, #1e40af 100%)' }}
      >
        {/* Brand Header */}
        <div className="h-16 flex items-center justify-between px-4 border-b border-primary-800/80 shrink-0">
          <div className="flex items-center gap-3 overflow-hidden">
            <div className="w-10 h-10 rounded-item bg-white/10 flex items-center justify-center text-primary-50 shrink-0">
              <Stethoscope className="w-5 h-5" />
            </div>
            {!collapsed && (
              <div className="flex flex-col truncate">
                <span className="text-base font-bold font-heading text-white leading-tight truncate">
                  MediReport AI
                </span>
                <span className="text-[11px] text-primary-200 font-semibold uppercase tracking-wider">
                  Clinical Portal
                </span>
              </div>
            )}
          </div>
          {/* Collapse toggle (Desktop only) */}
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="hidden md:flex p-1.5 rounded-md text-primary-200 hover:text-white hover:bg-white/10 transition-colors"
            title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          </button>
          {/* Close drawer (Mobile only) */}
          <button
            onClick={() => setMobileDrawerOpen(false)}
            className="md:hidden p-1.5 rounded-md text-primary-200 hover:text-white"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Role Portal Category Indicator */}
        {!collapsed && (
          <div className="px-5 pt-4 pb-2 text-[11px] font-bold uppercase tracking-widest text-primary-200">
            Clinical Portal
          </div>
        )}

        {/* Navigation Items */}
        <nav className="flex-1 px-3 py-2 space-y-1.5 overflow-y-auto">
          {doctorNav.map((item) => {
            const Icon = item.icon
            const isMatch = location.pathname === item.to || (item.to.includes('?') && location.pathname + location.search === item.to)
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/doctor/dashboard'}
                onClick={() => setMobileDrawerOpen(false)}
                className={({ isActive }) =>
                  `flex items-center gap-3.5 px-3 py-2.5 rounded-item text-sm font-medium transition-all ${
                    isActive || isMatch
                      ? 'bg-white/15 text-white font-semibold shadow-subtle'
                      : 'text-primary-200 hover:text-white hover:bg-white/5'
                  } ${collapsed ? 'justify-center px-0' : ''}`}
                title={collapsed ? item.label : undefined}
              >
                <Icon className="w-5 h-5 shrink-0" />
                {!collapsed && <span className="truncate">{item.label}</span>}
              </NavLink>
            )
          })}
        </nav>

        {/* Clinical Boundary Disclaimer */}
        {!collapsed && (
          <div className="m-3 p-3 rounded-item bg-white/5 border border-white/10 text-primary-200 text-[11px] flex items-start gap-2">
            <ShieldCheck className="w-4 h-4 text-primary-400 shrink-0 mt-0.5" />
            <span className="leading-tight">
              Educational prototype. Never provides clinical diagnoses.
            </span>
          </div>
        )}

        {/* User Footer Chip */}
        <div className="p-3 border-t border-primary-800/80 shrink-0">
          <div className={`flex items-center gap-3 ${collapsed ? 'justify-center' : ''}`}>
            <Avatar
              name={user?.full_name || user?.email}
              size="sm"
            />
            {!collapsed && (
              <div className="flex flex-col truncate min-w-0 flex-1">
                <span className="text-xs font-semibold text-white truncate" title={user?.full_name || user?.email}>
                  {user?.full_name || user?.email}
                </span>
                <span className="text-[11px] text-primary-200 capitalize truncate">
                  Doctor
                </span>
              </div>
            )}
            {!collapsed && (
              <button
                onClick={handleLogout}
                className="p-1.5 text-primary-200 hover:text-white hover:bg-white/10 rounded-md transition-colors"
                title="Sign out"
              >
                <LogOut className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Bar (64px) */}
        <header className="h-16 px-4 md:px-8 border-b border-border bg-surface flex items-center justify-between sticky top-0 z-30 shadow-subtle">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setMobileDrawerOpen(true)}
              className="md:hidden p-2 rounded-item hover:bg-surface-2 text-foreground-muted hover:text-foreground"
              aria-label="Open mobile menu"
            >
              <Menu className="w-5 h-5" />
            </button>
            <div className="text-lg font-bold font-heading text-foreground">
              {getPageTitle()}
            </div>
          </div>

          <div className="flex items-center gap-2 md:gap-3">
            {/* Global Search trigger (Ctrl+K) */}
            <button
              onClick={() => setSearchOpen(true)}
              className="hidden sm:flex items-center gap-2 px-3 py-1.5 text-xs text-foreground-muted bg-surface-2 hover:bg-surface-2/80 border border-border rounded-item transition-colors"
            >
              <Search className="w-3.5 h-3.5" />
              <span>Search...</span>
              <kbd className="px-1.5 py-0.5 text-[10px] font-mono bg-surface border border-border/80 rounded text-foreground-subtle">
                Ctrl K
              </kbd>
            </button>

            {/* Mobile search icon button */}
            <button
              onClick={() => setSearchOpen(true)}
              className="sm:hidden p-2 rounded-item hover:bg-surface-2 text-foreground-muted hover:text-foreground"
              aria-label="Search"
            >
              <Search className="w-5 h-5" />
            </button>

            {/* Notification Bell */}
            <NotificationBell />

            {/* Theme Toggle (System / Light / Dark) */}
            <ThemeToggle
              theme={themePreference}
              onThemeChange={setThemePreference}
            />

            {/* User Profile Menu */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button className="flex items-center gap-2 p-1 rounded-full hover:ring-2 hover:ring-primary-500/50 transition-all focus:outline-none focus:ring-2 focus:ring-primary-500">
                  <Avatar
                    name={user?.full_name || user?.email}
                    size="sm"
                  />
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <div className="p-2 border-b border-border/50">
                  <div className="text-xs font-semibold text-foreground truncate">
                    {user?.full_name || 'User'}
                  </div>
                  <div className="text-[11px] text-foreground-subtle truncate">
                    {user?.email}
                  </div>
                </div>
                <DropdownMenuItem onClick={() => navigate('/doctor/profile')}>
                  <UserRound className="w-4 h-4 mr-2 text-primary-500" />
                  <span>Doctor Profile</span>
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={handleLogout} className="text-red-500 focus:text-red-500">
                  <LogOut className="w-4 h-4 mr-2" />
                  <span>Sign Out</span>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </header>

        {/* Page Content Outlet */}
        <main id="main-content" className="flex-1 p-4 md:p-8 max-w-container w-full mx-auto">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
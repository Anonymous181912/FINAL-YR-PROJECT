import * as React from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, User, FileText, Pill, Clock, ArrowRight, ShieldCheck } from 'lucide-react'
import { Dialog, DialogContent } from './ui/Dialog'
import { listPatients } from '../services/patients'

export function GlobalSearch({ open, onOpenChange, userRole }) {
  const [query, setQuery] = React.useState('')
  const [patients, setPatients] = React.useState([])
  const [loading, setLoading] = React.useState(false)
  const navigate = useNavigate()

  React.useEffect(() => {
    if (!open) {
      setQuery('')
      setPatients([])
    }
  }, [open])

  React.useEffect(() => {
    if (userRole !== 'doctor' || !query.trim() || query.length < 2) {
      setPatients([])
      return
    }

    const timer = setTimeout(async () => {
      setLoading(true)
      try {
        const results = await listPatients(query.trim(), 0, 8)
        setPatients(results || [])
      } catch {
        setPatients([])
      } finally {
        setLoading(false)
      }
    }, 250)

    return () => clearTimeout(timer)
  }, [query, userRole])

  const handleSelect = (path) => {
    onOpenChange(false)
    navigate(path)
  }

  // Quick navigation items by role
  const quickLinks = userRole === 'doctor' ? [
    { label: 'Dashboard', path: '/dashboard', icon: Clock },
    { label: 'Patients Directory', path: '/patients', icon: User },
    { label: 'Prescriptions', path: '/prescriptions', icon: Pill },
    { label: 'Access Requests', path: '/patients?tab=requests', icon: ShieldCheck },
    { label: 'My Profile', path: '/doctor/profile', icon: User },
  ] : userRole === 'admin' ? [
    { label: 'Dashboard', path: '/dashboard', icon: Clock },
    { label: 'Doctor Verification', path: '/admin?tab=verification', icon: ShieldCheck },
    { label: 'Audit Log', path: '/admin?tab=audit', icon: FileText },
  ] : [
    { label: 'Dashboard', path: '/dashboard', icon: Clock },
    { label: 'My Reports', path: '/reports', icon: FileText },
    { label: 'Health Timeline', path: '/history', icon: Clock },
    { label: 'Lab Trends', path: '/reports?tab=trends', icon: FileText },
    { label: 'Prescriptions', path: '/prescriptions', icon: Pill },
    { label: 'Access & Privacy', path: '/access', icon: ShieldCheck },
    { label: 'My Profile', path: '/profile', icon: User },
  ]

  const filteredLinks = query.trim()
    ? quickLinks.filter(l => l.label.toLowerCase().includes(query.toLowerCase()))
    : quickLinks

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="p-0 overflow-hidden max-w-xl top-[30%]">
        <div className="flex items-center px-4 border-b border-border bg-surface-2/50">
          <Search className="w-5 h-5 text-foreground-muted mr-3 shrink-0" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={userRole === 'doctor' ? 'Search patients or quick navigate...' : 'Search pages, reports, prescriptions...'}
            className="w-full h-12 bg-transparent text-sm text-foreground placeholder:text-foreground-subtle outline-none"
            autoFocus
          />
          <kbd className="hidden sm:inline-block px-1.5 py-0.5 text-[10px] font-mono font-medium text-foreground-subtle bg-surface border border-border rounded">
            ESC
          </kbd>
        </div>

        <div className="max-h-[340px] overflow-y-auto p-2 space-y-2">
          {/* Patient Search Results (Doctor only) */}
          {userRole === 'doctor' && query.trim().length >= 2 && (
            <div className="mb-3">
              <div className="px-2 py-1 text-xs font-semibold text-foreground-subtle uppercase tracking-wider">
                Patients ({patients.length})
              </div>
              {loading ? (
                <div className="p-3 text-xs text-foreground-muted text-center">Searching patients...</div>
              ) : patients.length === 0 ? (
                <div className="p-3 text-xs text-foreground-muted text-center">No matching patients found.</div>
              ) : (
                patients.map(p => (
                  <button
                    key={p.id}
                    onClick={() => handleSelect(`/patients/${p.patient_id || p.id}`)}
                    className="w-full flex items-center justify-between p-2.5 rounded-item hover:bg-accent-soft text-left group transition-colors"
                  >
                    <div className="flex items-center gap-2.5">
                      <div className="w-7 h-7 rounded-full bg-accent-soft text-accent flex items-center justify-center text-xs font-bold">
                        {p.full_name?.charAt(0) || 'P'}
                      </div>
                      <div>
                        <div className="text-sm font-semibold text-foreground group-hover:text-accent">
                          {p.full_name}
                        </div>
                        <div className="text-xs text-foreground-subtle tabular-nums">
                          ID: {p.patient_id || p.id} &bull; {p.gender || 'Unknown gender'}
                        </div>
                      </div>
                    </div>
                    <ArrowRight className="w-4 h-4 text-foreground-subtle group-hover:text-accent group-hover:translate-x-0.5 transition-transform" />
                  </button>
                ))
              )}
            </div>
          )}

          {/* Quick Navigation Links */}
          <div>
            <div className="px-2 py-1 text-xs font-semibold text-foreground-subtle uppercase tracking-wider">
              Quick Navigation
            </div>
            {filteredLinks.map(link => {
              const Icon = link.icon
              return (
                <button
                  key={link.path}
                  onClick={() => handleSelect(link.path)}
                  className="w-full flex items-center justify-between p-2.5 rounded-item hover:bg-accent-soft text-left group transition-colors"
                >
                  <div className="flex items-center gap-2.5 text-sm font-medium text-foreground group-hover:text-accent">
                    <Icon className="w-4 h-4 text-foreground-muted group-hover:text-accent" />
                    <span>{link.label}</span>
                  </div>
                  <ArrowRight className="w-4 h-4 text-foreground-subtle group-hover:text-accent group-hover:translate-x-0.5 transition-transform" />
                </button>
              )
            })}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}

import { Link } from 'react-router-dom'
import { useFixedLightTheme } from '../utils/useFixedLightTheme.js'
import {
  Stethoscope,
  User,
  ArrowRight,
  Sparkles,
  ShieldCheck,
  FileText,
  Pill,
  Activity,
  HeartPulse,
  Brain,
  Users,
  ChevronRight,
} from 'lucide-react'

export default function Landing() {
  useFixedLightTheme()

  return (
    <div className="min-h-screen bg-background">
      {/* Hero Section */}
      <section className="relative bg-gradient-to-b from-slate-50 to-white dark:from-slate-900 dark:to-slate-800">
        <div className="absolute inset-0 bg-[url('/grid.svg')] opacity-5" />
        
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 lg:py-32">
          <div className="text-center max-w-3xl mx-auto">
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-400 text-sm font-medium mb-6">
              <Sparkles size={16} />
              <span>Digital Healthcare Platform</span>
            </div>
            
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold font-heading text-foreground mb-6 leading-tight">
              Intelligent Medical Report Interpretation & Healthcare Platform
            </h1>
            
            <p className="text-lg sm:text-xl text-foreground-muted max-w-2xl mx-auto mb-10 leading-relaxed">
              Bridging patients and doctors with OCR extraction, rule-based clinical NLP, 
              and patient-friendly AI interpretations. Separate secure portals for patients and healthcare providers.
            </p>
            
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16">
              <Link to="/patient/login" className="btn btn-teal text-lg px-8 py-3">
                <User size={20} className="mr-2" />
                <span>I am a Patient</span>
              </Link>
              <Link to="/doctor/login" className="btn btn-primary text-lg px-8 py-3">
                <Stethoscope size={20} className="mr-2" />
                <span>I am a Doctor</span>
              </Link>
            </div>
            
            <p className="text-sm text-foreground-muted">
              <Link to="/admin/login" className="text-primary-700 hover:underline">Admin Portal</Link>
            </p>
          </div>
        </div>
        
        {/* Floating Cards */}
        <div className="absolute bottom-[-60px] left-4 right-4 lg:left-1/2 lg:right-auto lg:w-[calc(50%-2rem)] lg:ml-8 z-10">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <FeatureCard 
              icon={Brain}
              title="AI-Powered NLP"
              description="Rule-based clinical entity extraction with deterministic results"
              color="teal"
            />
            <FeatureCard 
              icon={ShieldCheck}
              title="Safety First"
              description="Medication interaction checking with allergy alerts"
              color="primary"
            />
            <FeatureCard 
              icon={FileText}
              title="Digital Prescriptions"
              description="Verified PDF generation with QR code verification"
              color="amber"
            />
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 lg:py-32 bg-white dark:bg-slate-900 relative z-0">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold font-heading text-foreground mb-4">
              Designed for Healthcare
            </h2>
            <p className="text-lg text-foreground-muted max-w-2xl mx-auto">
              Purpose-built portals with distinct experiences for patients and doctors
            </p>
          </div>
          
          <div className="grid lg:grid-cols-2 gap-12 mb-16">
            {/* Patient Portal Features */}
            <div className="bg-teal-50 dark:bg-teal-900/20 rounded-2xl p-8 border border-teal-100 dark:border-teal-800">
              <div className="flex items-center gap-3 mb-6">
                <div className="w-12 h-12 rounded-xl bg-teal-100 dark:bg-teal-900/50 flex items-center justify-center">
                  <User size={24} className="text-teal-700 dark:text-teal-400" />
                </div>
                <div>
                  <h3 className="text-2xl font-bold font-heading text-foreground">Patient Portal</h3>
                  <p className="text-teal-700 dark:text-teal-400 font-medium">Personal Health Management</p>
                </div>
              </div>
              <ul className="space-y-4">
                {[
                  { icon: FileText, label: "My Reports", desc: "Upload and view lab reports with AI interpretations" },
                  { icon: Pill, label: "My Prescriptions", desc: "View issued prescriptions with PDF download" },
                  { icon: Activity, label: "Health Timeline", desc: "Chronological view of reports and prescriptions" },
                  { icon: ShieldCheck, label: "Access & Privacy", desc: "Control which doctors can prescribe for you" },
                  { icon: HeartPulse, label: "Emergency Card", desc: "Printable emergency card with QR code" },
                  { icon: Users, label: "Profile", desc: "Manage personal info and emergency contacts" },
                ].map((item, i) => (
                  <li key={i} className="flex items-start gap-3">
                    <item.icon size={20} className="text-teal-700 shrink-0 mt-0.5" />
                    <div>
                      <p className="font-medium text-foreground">{item.label}</p>
                      <p className="text-sm text-foreground-muted">{item.desc}</p>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
            
            {/* Doctor Portal Features */}
            <div className="bg-primary-50 dark:bg-primary-900/20 rounded-2xl p-8 border border-primary-100 dark:border-primary-800">
              <div className="flex items-center gap-3 mb-6">
                <div className="w-12 h-12 rounded-xl bg-primary-100 dark:bg-primary-900/50 flex items-center justify-center">
                  <Stethoscope size={24} className="text-primary-700 dark:text-primary-400" />
                </div>
                <div>
                  <h3 className="text-2xl font-bold font-heading text-foreground">Doctor Portal</h3>
                  <p className="text-primary-700 dark:text-primary-400 font-medium">Clinical Workspace</p>
                </div>
              </div>
              <ul className="space-y-4">
                {[
                  { icon: Users, label: "Patients", desc: "Search and manage patient directory" },
                  { icon: Pill, label: "Write Prescription", desc: "Create digital prescriptions with safety checks" },
                  { icon: FileText, label: "My Prescriptions", desc: "Review all authored prescriptions" },
                  { icon: ShieldCheck, label: "Access Requests", desc: "Manage patient access approvals" },
                  { icon: Activity, label: "Dashboard", desc: "Prescriptions issued today, follow-ups due" },
                  { icon: HeartPulse, label: "Profile", desc: "License info and verification status" },
                ].map((item, i) => (
                  <li key={i} className="flex items-start gap-3">
                    <item.icon size={20} className="text-primary-700 shrink-0 mt-0.5" />
                    <div>
                      <p className="font-medium text-foreground">{item.label}</p>
                      <p className="text-sm text-foreground-muted">{item.desc}</p>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* Security & Compliance */}
      <section className="py-20 bg-slate-50 dark:bg-slate-800/50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid md:grid-cols-3 gap-8 text-center">
            {[
              { icon: ShieldCheck, title: "Role-Based Access", desc: "Separate portals with strict route guards" },
              { icon: Brain, title: "Clinical Safety", desc: "Medication interaction & allergy checking" },
              { icon: FileText, title: "Audit Trail", desc: "Complete logging of all clinical actions" },
            ].map((item, i) => (
              <div key={i} className="p-6">
                <div className="w-16 h-16 mx-auto mb-4 rounded-xl bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center">
                  <item.icon size={28} className="text-primary-700 dark:text-primary-400" />
                </div>
                <h3 className="text-xl font-bold font-heading text-foreground mb-2">{item.title}</h3>
                <p className="text-foreground-muted">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-slate-900 text-slate-300 py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid md:grid-cols-4 gap-8 mb-8">
            <div>
              <div className="flex items-center gap-2 mb-4">
                <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-teal-500 to-primary-600 flex items-center justify-center">
                  <Sparkles size={20} className="text-white" />
                </div>
                <span className="text-xl font-bold font-heading text-white">MediReport AI</span>
              </div>
              <p className="text-sm text-slate-400">Digital Healthcare Platform for patients and providers</p>
            </div>
            <div>
              <h4 className="font-semibold text-white mb-4">Patient Portal</h4>
              <ul className="space-y-2 text-sm">
                <li><Link to="/patient/login" className="hover:text-teal-400 transition-colors">Login</Link></li>
                <li><Link to="/patient/register" className="hover:text-teal-400 transition-colors">Register</Link></li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold text-white mb-4">Doctor Portal</h4>
              <ul className="space-y-2 text-sm">
                <li><Link to="/doctor/login" className="hover:text-primary-400 transition-colors">Login</Link></li>
                <li><Link to="/doctor/register" className="hover:text-primary-400 transition-colors">Register</Link></li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold text-white mb-4">Resources</h4>
              <ul className="space-y-2 text-sm">
                <li><a href="#" className="hover:text-slate-400 transition-colors">Documentation</a></li>
                <li><a href="#" className="hover:text-slate-400 transition-colors">Privacy Policy</a></li>
                <li><a href="#" className="hover:text-slate-400 transition-colors">Terms of Service</a></li>
              </ul>
            </div>
          </div>
          <div className="border-t border-slate-800 pt-8 text-center text-sm text-slate-400">
            <p>Final Year Engineering Project &copy; {new Date().getFullYear()} &bull; FastAPI + React + MongoDB</p>
          </div>
        </div>
      </footer>
    </div>
  )
}

function FeatureCard({ icon: Icon, title, description, color }) {
  const colorMap = {
    teal: {
      card: 'bg-teal-50 dark:bg-teal-900/20 border-teal-100 dark:border-teal-800',
      iconWrap: 'bg-teal-100 dark:bg-teal-900/50',
      icon: 'text-teal-700 dark:text-teal-400',
    },
    primary: {
      card: 'bg-primary-50 dark:bg-primary-900/20 border-primary-100 dark:border-primary-800',
      iconWrap: 'bg-primary-100 dark:bg-primary-900/50',
      icon: 'text-primary-700 dark:text-primary-400',
    },
    amber: {
      card: 'bg-amber-50 dark:bg-amber-900/20 border-amber-100 dark:border-amber-800',
      iconWrap: 'bg-amber-100 dark:bg-amber-900/50',
      icon: 'text-amber-700 dark:text-amber-400',
    },
  }

  const styles = colorMap[color] || colorMap.primary

  return (
    <div className={`p-6 rounded-xl border ${styles.card}`}>
      <div className={`w-12 h-12 rounded-lg flex items-center justify-center mb-4 ${styles.iconWrap}`}>
        <Icon size={24} className={styles.icon} />
      </div>
      <h3 className="font-bold text-lg text-foreground mb-2">{title}</h3>
      <p className="text-sm text-foreground-muted">{description}</p>
    </div>
  )
}
import type { ReactNode } from 'react'

export function PageHeader({ eyebrow, title, children }: { eyebrow?: string; title: string; children?: ReactNode }) {
  return (
    <header className="max-w-3xl">
      {eyebrow && <p className="font-mono text-sm font-semibold text-accent">{eyebrow}</p>}
      <h1 className="mt-1 text-3xl font-bold tracking-tight sm:text-4xl">{title}</h1>
      {children && <div className="mt-3 text-lg leading-relaxed text-muted">{children}</div>}
    </header>
  )
}

export function Section({
  title,
  id,
  intro,
  children,
  aside,
}: {
  title: string
  id?: string
  intro?: ReactNode
  children: ReactNode
  aside?: ReactNode
}) {
  return (
    <section id={id} aria-labelledby={id ? `${id}-title` : undefined} className="mt-16 scroll-mt-24">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <h2 id={id ? `${id}-title` : undefined} className="text-2xl font-[650] tracking-tight">
          {title}
        </h2>
        {aside}
      </div>
      {intro && <p className="mt-2 max-w-3xl text-muted">{intro}</p>}
      <div className="mt-5">{children}</div>
    </section>
  )
}

export type Tone = 'neutral' | 'accent' | 'ok' | 'warn' | 'danger'

export function Badge({ children, tone = 'neutral' }: { children: ReactNode; tone?: Tone }) {
  const tones: Record<Tone, string> = {
    neutral: 'border-line bg-paper-2 text-muted',
    accent: 'border-transparent bg-accent-soft text-accent',
    ok: 'border-transparent bg-ok-soft text-ok',
    warn: 'border-transparent bg-warn-soft text-warn',
    danger: 'border-transparent bg-danger-soft text-danger',
  }
  return (
    <span className={`inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-semibold ${tones[tone]}`}>
      {children}
    </span>
  )
}

const STATUS_ICON: Record<'ok' | 'warn' | 'danger' | 'idle', ReactNode> = {
  ok: <circle cx="6" cy="6" r="5" fill="var(--ok-mark)" />,
  warn: <path d="M6 1 L11 11 L1 11 Z" fill="var(--warn-mark)" />,
  danger: <rect x="1" y="1" width="10" height="10" rx="2" fill="var(--danger-mark)" />,
  idle: <circle cx="6" cy="6" r="4.5" fill="none" stroke="var(--faint)" strokeWidth="1.5" />,
}

/** State is shape + label + colour, never colour alone. */
export function Status({ state, children }: { state: 'ok' | 'warn' | 'danger' | 'idle'; children: ReactNode }) {
  const color = { ok: 'text-ok', warn: 'text-warn', danger: 'text-danger', idle: 'text-faint' }[state]
  return (
    <span className={`inline-flex items-center gap-1.5 text-sm font-semibold ${color}`}>
      <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true">
        {STATUS_ICON[state]}
      </svg>
      {children}
    </span>
  )
}

export function Button({
  children,
  onClick,
  variant = 'primary',
  disabled,
  type = 'button',
  busy = false,
}: {
  children: ReactNode
  onClick?: () => void
  variant?: 'primary' | 'secondary' | 'danger'
  disabled?: boolean
  type?: 'button' | 'submit'
  busy?: boolean
}) {
  const variants = {
    primary: 'bg-brand text-white hover:bg-brand-hover',
    secondary: 'border border-line bg-paper text-text hover:border-accent hover:text-accent',
    danger: 'border border-line bg-paper text-danger hover:border-danger hover:bg-danger-soft',
  }
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled || busy}
      aria-busy={busy || undefined}
      className={`inline-flex h-9 items-center gap-1.5 rounded-lg px-4 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-50 ${variants[variant]}`}
    >
      {busy && <Spinner />}
      {children}
    </button>
  )
}

export function Spinner() {
  return (
    <svg className="size-4 animate-spin motion-reduce:animate-none" viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" strokeOpacity="0.25" strokeWidth="3" />
      <path d="M21 12a9 9 0 0 0-9-9" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  )
}

export function ErrorNote({ title, message, hint }: { title?: string; message: string; hint?: string }) {
  return (
    <div role="alert" className="rounded-lg border border-danger/30 bg-danger-soft px-3 py-2 text-sm text-danger">
      {title && <p className="font-semibold">{title}</p>}
      <p>{message}</p>
      {hint && <p className="mt-1 font-mono text-xs text-text">{hint}</p>}
    </div>
  )
}

export function Empty({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-xl border border-dashed border-line px-4 py-8 text-center text-sm text-muted">
      {children}
    </div>
  )
}

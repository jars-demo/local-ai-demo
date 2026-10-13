// The mark is a server rack with a closed loop: everything stays inside the box.
export function Logo({ size = 30, withText = true }: { size?: number; withText?: boolean }) {
  return (
    <span className="inline-flex items-center gap-2.5">
      <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
        <rect width="32" height="32" rx="8" fill="var(--brand)" />
        <rect x="7" y="7" width="18" height="5" rx="1.5" fill="#fff" />
        <rect x="7" y="13.5" width="18" height="5" rx="1.5" fill="#fff" opacity="0.85" />
        <rect x="7" y="20" width="18" height="5" rx="1.5" fill="#fff" opacity="0.7" />
        <circle cx="21.5" cy="9.5" r="1.3" fill="#16a34a" />
        <circle cx="21.5" cy="16" r="1.3" fill="#16a34a" />
        <circle cx="21.5" cy="22.5" r="1.3" fill="#fde68a" />
      </svg>
      {withText && (
        <span className="leading-tight">
          <span className="block text-[15px] font-bold tracking-tight">Local AI</span>
          <span className="block font-mono text-[11px] text-muted">offline · self-hosted</span>
        </span>
      )}
    </span>
  )
}

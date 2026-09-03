export function Teta2Logo({ compact = false }: { compact?: boolean }) {
  return (
    <div className={compact ? "t2-logo compact" : "t2-logo"} aria-label="Teta2">
      <span className="t2-logo-mark" aria-hidden="true">
        <svg viewBox="0 0 64 64" role="img">
          <defs>
            <linearGradient id="teta2MarkGradient" x1="9" y1="8" x2="53" y2="56" gradientUnits="userSpaceOnUse">
              <stop stopColor="#7657ff" />
              <stop offset="1" stopColor="#4f7cff" />
            </linearGradient>
          </defs>
          <path d="M20.4 9.1c4.5 0 7.8 2.1 11.6 2.1 3.8 0 7.1-2.1 11.6-2.1 8.5 0 13.3 7.1 11.4 16.7-1 5.2-3.7 9.4-5.4 14.3-2 5.8-2.4 14.6-7.7 14.6-4.6 0-4.2-10.2-9.9-10.2s-5.3 10.2-9.9 10.2c-5.3 0-5.7-8.8-7.7-14.6-1.7-4.9-4.4-9.1-5.4-14.3C7.1 16.2 11.9 9.1 20.4 9.1Z" fill="none" stroke="url(#teta2MarkGradient)" strokeWidth="3.2" strokeLinecap="round" strokeLinejoin="round"/>
          <path d="M25 22.5h14M32 15.5v14" stroke="url(#teta2MarkGradient)" strokeWidth="2.2" strokeLinecap="round" opacity=".55"/>
        </svg>
      </span>
      {!compact && <span className="t2-logo-word"><strong>Teta2</strong><small>AI dental platform</small></span>}
    </div>
  );
}

type IconProps = { size?: number; className?: string };

const base = (size: number) => ({
  width: size,
  height: size,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.5,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  "aria-hidden": true,
});

export function ArrowUpRight({ size = 18, className }: IconProps) {
  return (
    <svg {...base(size)} className={className}>
      <path d="M7 17 17 7M8 7h9v9" />
    </svg>
  );
}

export function ArrowDown({ size = 18, className }: IconProps) {
  return (
    <svg {...base(size)} className={className}>
      <path d="M12 5v14M6 13l6 6 6-6" />
    </svg>
  );
}

export function Close({ size = 20, className }: IconProps) {
  return (
    <svg {...base(size)} className={className}>
      <path d="M6 6l12 12M18 6 6 18" />
    </svg>
  );
}

export function Bag({ size = 20, className }: IconProps) {
  return (
    <svg {...base(size)} className={className}>
      <path d="M5 8h14l-1 12H6L5 8Z" />
      <path d="M9 8V6a3 3 0 0 1 6 0v2" />
    </svg>
  );
}

export function Heart({ size = 18, filled = false, className }: IconProps & { filled?: boolean }) {
  return (
    <svg {...base(size)} className={className} fill={filled ? "currentColor" : "none"}>
      <path d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10Z" />
    </svg>
  );
}

export function Plus({ size = 18, className }: IconProps) {
  return (
    <svg {...base(size)} className={className}>
      <path d="M12 5v14M5 12h14" />
    </svg>
  );
}

export function Check({ size = 18, className }: IconProps) {
  return (
    <svg {...base(size)} className={className}>
      <path d="m5 12.5 4.5 4.5L19 7.5" />
    </svg>
  );
}

export function WhatsApp({ size = 18, className }: IconProps) {
  return (
    <svg {...base(size)} className={className}>
      <path d="M4 20l1.3-3.9A8 8 0 1 1 8 19l-4 1Z" />
      <path d="M9.2 8.6c.2-.4.6-.5.9-.3l.9 1.6c.1.3 0 .6-.2.8l-.5.5c.5 1.1 1.4 2 2.5 2.5l.5-.5c.2-.2.5-.3.8-.2l1.6.9c.3.2.4.6.2.9-.5.9-1.5 1.3-2.4 1-2.2-.8-4-2.6-4.8-4.8-.3-.9 0-1.8.5-2.4Z" />
    </svg>
  );
}

export function Instagram({ size = 18, className }: IconProps) {
  return (
    <svg {...base(size)} className={className}>
      <rect x="4" y="4" width="16" height="16" rx="4.5" />
      <circle cx="12" cy="12" r="3.6" />
      <circle cx="16.8" cy="7.2" r=".6" fill="currentColor" />
    </svg>
  );
}

export function Menu({ size = 22, className }: IconProps) {
  return (
    <svg {...base(size)} className={className}>
      <path d="M4 9h16M4 15h16" />
    </svg>
  );
}

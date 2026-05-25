/**
 * Aurora Design System — Tokens (TypeScript mirror)
 * Use estes em inline styles quando CSS vars não couberem.
 * Mantenha sincronizado com tokens.css.
 */

export const colors = {
  navy:        "#0F172A",
  navy2:       "#1E293B",
  blue:        "#0052FF",
  blueHover:   "#003FCC",
  sky:         "#0EA5E9",
  aurora1:     "#93C5FD",
  aurora2:     "#60A5FA",
  aurora3:     "#3B82F6",
  blue10:      "#DBEAFE",
  blue20:      "#BFDBFE",
  blue30:      "#93C5FD",

  text:        "#0F172A",
  text2:       "#334155",
  muted:       "#64748B",
  muted2:      "#94A3B8",

  bg:          "#F0F7FF",
  surface:     "rgba(255, 255, 255, 0.72)",
  surfaceSolid:"#FFFFFF",
  surfaceElev: "rgba(255, 255, 255, 0.92)",

  glassBg:     "rgba(255, 255, 255, 0.55)",
  glassBg2:    "rgba(255, 255, 255, 0.32)",
  glassBorder: "rgba(255, 255, 255, 0.55)",
  border:      "rgba(186, 230, 253, 0.5)",
  borderSolid: "#E2E8F0",
  borderStrong:"rgba(59, 130, 246, 0.25)",

  success:     "#16A34A",
  success10:   "#DCFCE7",
  success20:   "#BBF7D0",
  warning:     "#D97706",
  warning10:   "#FEF3C7",
  warning20:   "#FDE68A",
  danger:      "#DC2626",
  danger10:    "#FEE2E2",
  danger20:    "#FECACA",
  info:        "#0B6BD4",
  info10:      "#DBEAFE",
} as const;

export const fonts = {
  sans:  "'Manrope', system-ui, -apple-system, 'Segoe UI', sans-serif",
  serif: "'Instrument Serif', Georgia, 'Times New Roman', serif",
  mono:  "'JetBrains Mono', ui-monospace, Menlo, Consolas, monospace",
} as const;

export const radii = {
  xs:   "4px",
  sm:   "8px",
  md:   "14px",
  lg:   "22px",
  xl:   "32px",
  pill: "100px",
  full: "9999px",
} as const;

export const shadows = {
  sm:           "0 1px 3px rgba(15,23,42,.06), 0 1px 2px rgba(15,23,42,.04)",
  md:           "0 4px 12px rgba(15,23,42,.08), 0 2px 4px rgba(15,23,42,.05)",
  lg:           "0 18px 50px rgba(15,23,42,.10), 0 4px 14px rgba(15,23,42,.05)",
  xl:           "0 25px 70px rgba(15,23,42,.15), 0 10px 20px rgba(15,23,42,.08)",
  glass:        "0 8px 32px rgba(15, 23, 42, 0.08), 0 2px 8px rgba(30, 111, 217, 0.06), inset 0 1px 0 rgba(255, 255, 255, 0.7)",
  glassHover:   "0 18px 50px rgba(15, 23, 42, 0.12), 0 4px 14px rgba(30, 111, 217, 0.15), inset 0 1px 0 rgba(255, 255, 255, 0.85)",
  cta:          "0 2px 8px rgba(0, 82, 255, 0.35)",
  ctaHover:     "0 8px 24px rgba(0, 82, 255, 0.45)",
  focus:        "0 0 0 3px rgba(0, 82, 255, 0.25)",
} as const;

export const easing = {
  smooth: "cubic-bezier(.4, 0, .2, 1)",
  spring: "cubic-bezier(.34, 1.56, .64, 1)",
} as const;

export const glass = {
  bg:      colors.glassBg,
  border:  colors.glassBorder,
  blur:    "blur(24px) saturate(180%)",
  blurLg:  "blur(36px) saturate(200%)",
  blurSm:  "blur(12px) saturate(140%)",
} as const;

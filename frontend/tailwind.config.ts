import type { Config } from "tailwindcss";

/**
 * OrgAudi — Aurora Design System (light bank-grade)
 * Tokens vivem em src/styles/tokens.css como CSS custom properties.
 * Tailwind consome via var(--*) para garantir fonte única da verdade.
 */
const config: Config = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // ── Aurora paleta ─────────────────────────────────────────
        navy:       "var(--navy)",
        "navy-2":   "var(--navy-2)",
        blue:       "var(--blue)",
        "blue-hover": "var(--blue-hover)",
        sky:        "var(--sky)",
        "aurora-1": "var(--aurora-1)",
        "aurora-2": "var(--aurora-2)",
        "aurora-3": "var(--aurora-3)",
        "blue-10":  "var(--blue-10)",
        "blue-20":  "var(--blue-20)",
        "blue-30":  "var(--blue-30)",

        // ── Text ──────────────────────────────────────────────────
        text:       "var(--text)",
        "text-2":   "var(--text-2)",
        muted:      "var(--muted)",
        "muted-2":  "var(--muted-2)",

        // ── Surfaces ──────────────────────────────────────────────
        bg: {
          DEFAULT:   "var(--bg)",
          surface:   "var(--surface)",
          solid:     "var(--surface-solid)",
          elev:      "var(--surface-elev)",
        },

        // ── Borders ───────────────────────────────────────────────
        line: {
          DEFAULT: "var(--border)",
          solid:   "var(--border-solid)",
          strong:  "var(--border-strong)",
        },

        // ── Semânticos ────────────────────────────────────────────
        success: {
          DEFAULT: "var(--success)",
          10: "var(--success-10)",
          20: "var(--success-20)",
        },
        warning: {
          DEFAULT: "var(--warning)",
          10: "var(--warning-10)",
          20: "var(--warning-20)",
        },
        danger: {
          DEFAULT: "var(--danger)",
          10: "var(--danger-10)",
          20: "var(--danger-20)",
        },
        info: {
          DEFAULT: "var(--info)",
          10: "var(--info-10)",
        },

        // ── Legacy aliases (compat — gradual migration) ──────────
        orgatec: {
          ember:  "#0F172A",
          coal:   "#1E293B",
          deep:   "#0052FF",
          royal:  "#003FCC",
          bright: "#3B82F6",
          sky:    "#0EA5E9",
          cyan:   "#0EA5E9",
          glow:   "#60A5FA",
          aurora: "#DBEAFE",
          ash:    "#E0F2FE",
        },
        ink: {
          DEFAULT: "var(--text)",
          muted:   "var(--text-2)",
          subtle:  "var(--muted)",
        },
        accent: {
          ok:   "var(--success)",
          warn: "var(--warning)",
          err:  "var(--danger)",
          info: "var(--info)",
        },
      },

      fontFamily: {
        sans:    ["Manrope", "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
        serif:   ["Instrument Serif", "Georgia", "Times New Roman", "serif"],
        mono:    ["JetBrains Mono", "ui-monospace", "Menlo", "Consolas", "monospace"],
        display: ["Manrope", "system-ui", "sans-serif"],
      },

      fontSize: {
        "display":   ["var(--text-display)", { lineHeight: "1.1", letterSpacing: "-0.03em" }],
        "display-4xl": ["var(--text-4xl)", { lineHeight: "1.1", letterSpacing: "-0.03em" }],
      },

      boxShadow: {
        sm:           "var(--shadow-sm)",
        md:           "var(--shadow-md)",
        lg:           "var(--shadow-lg)",
        xl:           "var(--shadow-xl)",
        glass:        "var(--glass-shadow)",
        "glass-hover":"var(--glass-shadow-hover)",
        cta:          "var(--shadow-cta)",
        "cta-hover":  "var(--shadow-cta-hover)",
        focus:        "var(--shadow-focus)",
        // Legacy
        "glass-lg":   "var(--glass-shadow-hover)",
        "glass-btn":  "var(--shadow-cta)",
        glow:         "var(--shadow-cta-hover)",
        "glow-cyan":  "0 0 24px rgba(14, 165, 233, 0.40)",
        card:         "var(--glass-shadow)",
      },

      backgroundImage: {
        "aurora-mesh": "var(--bg-mesh)",
        "aurora-btn":  "linear-gradient(135deg, var(--blue) 0%, var(--blue-hover) 100%)",
        // Legacy
        "orgatec-header":
          "linear-gradient(135deg, #0F172A 0%, #1E293B 35%, #0052FF 80%, #3B82F6 100%)",
        "glass-card":
          "linear-gradient(135deg, rgba(255,255,255,0.85) 0%, rgba(245,250,255,0.60) 100%)",
        "glass-btn":
          "linear-gradient(135deg, rgba(255,255,255,0.95) 0%, rgba(232,242,255,0.85) 100%)",
        "aurora-glow":
          "radial-gradient(ellipse at center, rgba(0,82,255,0.15) 0%, transparent 70%)",
      },

      borderRadius: {
        xs:   "var(--r-xs)",
        sm:   "var(--r-sm)",
        md:   "var(--r-md)",
        lg:   "var(--r-lg)",
        xl:   "var(--r-xl)",
        pill: "var(--r-pill)",
        card: "var(--r-xl)",
        btn:  "var(--r-sm)",
      },

      backdropBlur: {
        glass:    "24px",
        "glass-lg": "36px",
        "glass-sm": "12px",
        xs:  "4px",
        sm:  "8px",
        md:  "12px",
        lg:  "20px",
        xl:  "28px",
      },

      transitionTimingFunction: {
        smooth: "cubic-bezier(.4, 0, .2, 1)",
        spring: "cubic-bezier(.34, 1.56, .64, 1)",
      },
    },
  },
  plugins: [],
};

export default config;

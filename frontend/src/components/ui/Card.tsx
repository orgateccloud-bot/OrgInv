import type { ReactNode } from "react";
import { cx } from "../../lib/fmt";

export function Card({
  title,
  subtitle,
  actions,
  children,
  className,
  padding = true,
  eyebrow,
}: {
  title?: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
  padding?: boolean;
  eyebrow?: ReactNode;
}) {
  return (
    <section className={cx("card", className)}>
      {(title || actions || eyebrow) && (
        <header>
          <div className="flex flex-col gap-1">
            {eyebrow && <span className="text-eyebrow">{eyebrow}</span>}
            {title && <h3>{title}</h3>}
            {subtitle && (
              <p className="text-xs text-muted leading-snug">{subtitle}</p>
            )}
          </div>
          {actions && <div className="shrink-0">{actions}</div>}
        </header>
      )}
      <div className={padding ? "p-5" : ""}>{children}</div>
    </section>
  );
}

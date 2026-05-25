import { cloneElement, isValidElement, useId, type ReactNode } from "react";
import { cx } from "../../lib/fmt";

export function Field({
  label,
  children,
  hint,
  error,
  className,
  htmlFor,
}: {
  label: string;
  children: ReactNode;
  hint?: ReactNode;
  error?: ReactNode;
  className?: string;
  htmlFor?: string;
}) {
  const autoId = useId();
  const id = htmlFor ?? autoId;

  // Injeta id no filho (input/select/textarea) para casar com o label
  let wrapped: ReactNode = children;
  if (isValidElement(children)) {
    const childProps = children.props as { id?: string };
    if (!childProps.id) {
      wrapped = cloneElement(children, { id } as Record<string, unknown>);
    }
  }

  return (
    <div className={cx("flex flex-col", className)}>
      <label className="field-label" htmlFor={id}>
        {label}
      </label>
      {wrapped}
      {error ? (
        <span className="text-xs mt-1.5" style={{ color: "var(--danger)" }}>
          {error}
        </span>
      ) : hint ? (
        <span className="text-xs mt-1.5 text-muted">{hint}</span>
      ) : null}
    </div>
  );
}

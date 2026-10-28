"use client";

/**
 * Button.tsx — Primary, accent, secondary, and icon buttons (design 4.8).
 */

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "accent" | "secondary" | "icon";
  size?: "default" | "lg";
  children: React.ReactNode;
}

export default function Button({
  variant = "primary",
  size = "default",
  children,
  className = "",
  disabled,
  ...props
}: ButtonProps) {
  const base =
    "inline-flex items-center justify-center font-semibold transition-all duration-150 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:transform-none";

  const variants: Record<string, string> = {
    primary: "",
    accent: "",
    secondary: "",
    icon: "",
  };

  const sizeClasses =
    size === "lg" ? "h-14 text-base" : "h-[52px] text-sm";

  const variantStyles: Record<
    string,
    React.CSSProperties
  > = {
    primary: {
      background: "var(--ink-900)",
      color: "var(--text-on-dark)",
      borderRadius: "var(--r-pill)",
      padding: "0 32px",
      fontFamily: "var(--font-inter), sans-serif",
    },
    accent: {
      background: "var(--accent-sky)",
      color: "var(--ink-900)",
      borderRadius: "var(--r-pill)",
      padding: "0 32px",
      fontFamily: "var(--font-inter), sans-serif",
    },
    secondary: {
      background: "transparent",
      color: "var(--text-on-light)",
      border: "1px solid var(--ink-200)",
      borderRadius: "var(--r-pill)",
      padding: "0 24px",
      fontFamily: "var(--font-inter), sans-serif",
    },
    icon: {
      background: "transparent",
      border: "1px solid var(--ink-200)",
      borderRadius: "50%",
      width: 44,
      height: 44,
      padding: 0,
    },
  };

  return (
    <button
      className={`${base} ${variants[variant]} ${variant !== "icon" ? sizeClasses : ""} ${className}`}
      style={variantStyles[variant]}
      disabled={disabled}
      onMouseDown={(e) => {
        if (!disabled) {
          (e.currentTarget as HTMLElement).style.transform = "scale(0.98)";
        }
      }}
      onMouseUp={(e) => {
        (e.currentTarget as HTMLElement).style.transform = "scale(1)";
      }}
      onMouseLeave={(e) => {
        (e.currentTarget as HTMLElement).style.transform = "scale(1)";
      }}
      {...props}
    >
      {children}
    </button>
  );
}

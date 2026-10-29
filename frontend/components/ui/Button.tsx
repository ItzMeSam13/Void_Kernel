"use client";

import React from "react";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "accent" | "secondary" | "icon" | "ghost";
  size?: "sm" | "md" | "lg";
  children?: React.ReactNode;
}

export function Button({
  variant = "primary",
  size = "md",
  className = "",
  disabled,
  children,
  ...props
}: ButtonProps) {
  const baseStyles =
    "inline-flex items-center justify-center font-medium transition-all duration-200 cursor-pointer select-none outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-sky-600)] focus-visible:ring-offset-2";

  let variantStyles = "";
  let sizeStyles = "";

  if (variant === "primary") {
    variantStyles =
      "bg-[var(--ink-900)] text-[var(--text-on-dark)] hover:bg-[var(--ink-800)] active:scale-[0.98]";
    sizeStyles =
      size === "sm"
        ? "h-10 px-5 rounded-full text-[13px]"
        : size === "lg"
        ? "h-14 px-8 rounded-full text-[16px] font-semibold"
        : "h-[52px] px-7 rounded-full text-[15px] font-semibold";
  } else if (variant === "accent") {
    variantStyles =
      "bg-[var(--accent-sky)] text-[var(--ink-900)] font-semibold hover:bg-[var(--accent-sky-600)] active:scale-[0.98]";
    sizeStyles =
      size === "sm"
        ? "h-10 px-5 rounded-full text-[13px]"
        : size === "lg"
        ? "h-14 px-8 rounded-full text-[16px]"
        : "h-[52px] px-7 rounded-full text-[15px]";
  } else if (variant === "secondary") {
    variantStyles =
      "bg-transparent text-[var(--text-on-light)] border border-[var(--ink-200)] hover:bg-[var(--ink-100)] active:scale-[0.98]";
    sizeStyles =
      size === "sm"
        ? "h-10 px-4 rounded-full text-[13px]"
        : size === "lg"
        ? "h-14 px-7 rounded-full text-[15px]"
        : "h-[52px] px-6 rounded-full text-[14px]";
  } else if (variant === "icon") {
    variantStyles =
      "bg-transparent text-[var(--text-on-dark)] border border-[var(--ink-700)] hover:bg-[var(--ink-800)] active:scale-[0.95] rounded-full p-0";
    sizeStyles =
      size === "sm" ? "w-10 h-10" : size === "lg" ? "w-14 h-14" : "w-12 h-12";
  } else if (variant === "ghost") {
    variantStyles =
      "bg-transparent text-[var(--ink-500)] hover:text-[var(--text-on-light)] hover:bg-[var(--ink-100)] rounded-full";
    sizeStyles = "h-10 px-4 text-[13px]";
  }

  const disabledStyles = disabled
    ? "opacity-40 cursor-not-allowed hover:bg-auto active:scale-100"
    : "";

  return (
    <button
      className={`${baseStyles} ${variantStyles} ${sizeStyles} ${disabledStyles} ${className}`}
      disabled={disabled}
      {...props}
    >
      {children}
    </button>
  );
}


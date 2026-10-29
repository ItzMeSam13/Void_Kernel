"use client";

import React, { Suspense, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Globe,
  Settings,
  Bell,
  User,
  ShieldCheck,
  Menu,
  X,
} from "lucide-react";

interface NavLink {
  label: string;
  href: string;
  external?: boolean;
}

const NAV_LINKS: NavLink[] = [
  { label: "Check", href: "/" },
  { label: "Reports", href: "/#recent" },
  { label: "Analytics", href: "/analytics" },
  { label: "Docs", href: "https://github.com", external: true },
  { label: "FAQ", href: "#faq" },
];

function NavLinksList() {
  const pathname = usePathname();

  return (
    <>
      {NAV_LINKS.map((link) => {
        const isActive =
          link.href === "/"
            ? pathname === "/"
            : link.href.startsWith("/#")
            ? false
            : pathname.startsWith(link.href);

        return (
          <div
            key={link.label}
            className="relative h-full flex items-center justify-center"
          >
            <Link
              href={link.href}
              target={link.external ? "_blank" : undefined}
              className={`text-[16px] font-medium transition-colors duration-150 ${
                isActive
                  ? "text-white font-semibold"
                  : "text-[var(--text-on-dark-muted)] hover:text-white"
              }`}
            >
              {link.label}
            </Link>

            {/* 2px white underline sitting on the bar's bottom border per design.md §4.1 */}
            {isActive && (
              <span className="absolute bottom-0 w-[72px] h-[2px] bg-white rounded-t-full transition-all duration-200" />
            )}
          </div>
        );
      })}
    </>
  );
}

function NavLinksFallback() {
  return (
    <>
      {NAV_LINKS.map((link) => (
        <div
          key={link.label}
          className="relative h-full flex items-center justify-center"
        >
          <Link
            href={link.href}
            target={link.external ? "_blank" : undefined}
            className="text-[16px] font-medium text-[var(--text-on-dark-muted)] hover:text-white transition-colors duration-150"
          >
            {link.label}
          </Link>
        </div>
      ))}
    </>
  );
}

export function TopBar() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <header className="relative w-full h-[100px] md:h-[112px] bg-[var(--ink-900)] px-6 md:px-14 flex items-center justify-between border-b border-[var(--ink-700)] select-none">
      {/* Left: Original Shield-Magnifier Glyph + Wordmark */}
      <div className="flex items-center gap-10">
        <Link href="/" className="flex items-center gap-3.5 group">
          <div className="w-11 h-11 rounded-[14px] bg-gradient-to-br from-[var(--accent-sky)] to-[var(--accent-sky-600)] flex items-center justify-center text-[var(--ink-900)] shadow-sm group-hover:scale-105 transition-transform duration-200">
            <ShieldCheck className="w-6 h-6 stroke-[2.2]" />
          </div>
          <span className="text-white font-display font-extrabold text-[26px] tracking-[-0.03em]">
            Nith
          </span>
        </Link>

        {/* Desktop Nav Links */}
        <nav className="hidden lg:flex items-center gap-8 h-[112px]">
          <Suspense fallback={<NavLinksFallback />}>
            <NavLinksList />
          </Suspense>
        </nav>
      </div>

      {/* Right Cluster */}
      <div className="flex items-center gap-3 md:gap-4">
        {/* Language selector */}
        <div className="hidden sm:flex items-center gap-2 h-10 px-3.5 rounded-full border border-[var(--ink-700)] text-[var(--text-on-dark-muted)] hover:text-white hover:border-[var(--ink-500)] transition-colors cursor-pointer text-[13px] font-medium">
          <Globe className="w-4 h-4 text-[var(--accent-sky)]" />
          <span>English</span>
        </div>

        {/* Avatar with sky-blue notification dot */}
        <button
          className="relative w-11 h-11 md:w-12 md:h-12 rounded-full border border-[var(--ink-700)] flex items-center justify-center text-white hover:bg-[var(--ink-800)] transition-colors"
          aria-label="User profile"
        >
          <User className="w-5 h-5 text-white/90" />
          <span className="absolute top-2.5 right-2.5 w-2.5 h-2.5 rounded-full bg-[var(--accent-sky)] ring-2 ring-[var(--ink-900)]" />
        </button>

        {/* Settings button */}
        <button
          className="hidden sm:flex w-11 h-11 md:w-12 md:h-12 rounded-full border border-[var(--ink-700)] items-center justify-center text-white hover:bg-[var(--ink-800)] transition-colors"
          aria-label="Settings"
        >
          <Settings className="w-5 h-5 text-white/90" />
        </button>

        {/* Bell notification button */}
        <button
          className="w-11 h-11 md:w-12 md:h-12 rounded-full border border-[var(--ink-700)] flex items-center justify-center text-white hover:bg-[var(--ink-800)] transition-colors"
          aria-label="Notifications"
        >
          <Bell className="w-5 h-5 text-white/90" />
        </button>

        {/* Mobile menu toggle */}
        <button
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="lg:hidden w-11 h-11 rounded-full border border-[var(--ink-700)] flex items-center justify-center text-white"
          aria-label="Toggle navigation"
        >
          {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>

      {/* Mobile Drawer Menu */}
      {mobileMenuOpen && (
        <div className="lg:hidden absolute top-[100px] left-0 w-full bg-[var(--ink-900)] border-b border-[var(--ink-700)] p-6 z-50 flex flex-col gap-4 shadow-xl">
          {NAV_LINKS.map((link) => (
            <Link
              key={link.label}
              href={link.href}
              onClick={() => setMobileMenuOpen(false)}
              className="text-lg font-medium text-[var(--text-on-dark-muted)] hover:text-white py-2"
            >
              {link.label}
            </Link>
          ))}
        </div>
      )}
    </header>
  );
}


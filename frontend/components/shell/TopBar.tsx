"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Globe,
  User,
  Settings,
  Bell,
  Menu,
  X,
  ShieldCheck,
} from "lucide-react";

/**
 * TopBar.tsx — Dark top navigation bar (design 4.1)
 * Height 112px, contains logo, nav links, and right cluster.
 */

const NAV_LINKS = [
  { href: "/", label: "Check" },
  { href: "/results", label: "Reports" },
  { href: "/analytics", label: "Analytics" },
  { href: "#", label: "Docs" },
  { href: "#", label: "FAQ" },
];

export default function TopBar() {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  function isActive(href: string) {
    if (href === "/") return pathname === "/";
    return pathname.startsWith(href);
  }

  return (
    <header
      className="relative flex items-center justify-between h-[112px] px-8 lg:px-14"
      style={{
        background: "var(--ink-900)",
        borderBottom: "1px solid var(--ink-700)",
      }}
    >
      {/* Logo */}
      <Link href="/" className="flex items-center gap-3 shrink-0">
        <div
          className="w-10 h-10 rounded-xl flex items-center justify-center"
          style={{ background: "var(--accent-sky)" }}
        >
          <ShieldCheck size={22} strokeWidth={1.5} color="var(--ink-900)" />
        </div>
        <span
          className="text-[26px] font-extrabold tracking-tight"
          style={{
            color: "var(--text-on-dark)",
            fontFamily: "var(--font-manrope), sans-serif",
          }}
        >
          Nith
        </span>
      </Link>

      {/* Desktop nav */}
      <nav className="hidden md:flex items-center gap-8" role="navigation">
        {NAV_LINKS.map((link) => (
          <Link
            key={link.label}
            href={link.href}
            className="relative text-[17px] font-medium pb-1 transition-colors duration-150"
            style={{
              color: isActive(link.href)
                ? "var(--text-on-dark)"
                : "var(--text-on-dark-muted)",
              fontFamily: "var(--font-inter), sans-serif",
            }}
          >
            {link.label}
            {isActive(link.href) && (
              <span
                className="absolute bottom-[-4px] left-0 right-0 h-[2px] rounded-full"
                style={{ background: "var(--text-on-dark)" }}
              />
            )}
          </Link>
        ))}
      </nav>

      {/* Right cluster */}
      <div className="hidden md:flex items-center gap-3">
        {/* Language selector */}
        <button
          className="flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-colors duration-150 hover:opacity-80"
          style={{
            color: "var(--text-on-dark-muted)",
            fontFamily: "var(--font-inter), sans-serif",
          }}
        >
          <Globe size={18} strokeWidth={1.5} />
          <span>English</span>
        </button>

        {/* Icon buttons */}
        {[
          { icon: User, hasNotif: true },
          { icon: Settings, hasNotif: false },
          { icon: Bell, hasNotif: false },
        ].map(({ icon: Icon, hasNotif }, i) => (
          <button
            key={i}
            className="relative w-12 h-12 rounded-full flex items-center justify-center transition-colors duration-150"
            style={{
              border: "1px solid var(--ink-700)",
              background: "transparent",
            }}
            onMouseEnter={(e) =>
              (e.currentTarget.style.background = "var(--ink-800)")
            }
            onMouseLeave={(e) =>
              (e.currentTarget.style.background = "transparent")
            }
          >
            <Icon size={20} strokeWidth={1.5} color="var(--text-on-dark)" />
            {hasNotif && (
              <span
                className="absolute top-2.5 right-2.5 w-2.5 h-2.5 rounded-full"
                style={{
                  background: "var(--accent-sky)",
                  border: "2px solid var(--ink-900)",
                }}
              />
            )}
          </button>
        ))}
      </div>

      {/* Mobile hamburger */}
      <button
        className="md:hidden w-12 h-12 rounded-full flex items-center justify-center"
        style={{ border: "1px solid var(--ink-700)" }}
        onClick={() => setMobileOpen(!mobileOpen)}
        aria-label={mobileOpen ? "Close menu" : "Open menu"}
      >
        {mobileOpen ? (
          <X size={20} color="var(--text-on-dark)" strokeWidth={1.5} />
        ) : (
          <Menu size={20} color="var(--text-on-dark)" strokeWidth={1.5} />
        )}
      </button>

      {/* Mobile nav overlay */}
      {mobileOpen && (
        <div
          className="absolute top-full left-0 right-0 z-50 p-6 flex flex-col gap-4 md:hidden"
          style={{ background: "var(--ink-900)", borderTop: "1px solid var(--ink-700)" }}
        >
          {NAV_LINKS.map((link) => (
            <Link
              key={link.label}
              href={link.href}
              className="text-lg font-medium py-2"
              style={{
                color: isActive(link.href)
                  ? "var(--text-on-dark)"
                  : "var(--text-on-dark-muted)",
              }}
              onClick={() => setMobileOpen(false)}
            >
              {link.label}
            </Link>
          ))}
        </div>
      )}
    </header>
  );
}

"use client";
import Link from "next/link";
import { twMerge } from "tailwind-merge";

export function Nav({ className = "" }: { className?: string }) {
  return (
    <header className={twMerge("h-14 border-b border-[color:var(--color-border)] bg-background", className)}>
      <div className="container-max layout-gutter h-full flex items-center justify-between">
        <Link href="/" className="flex items-center">
          <span className="text-lg font-semibold tracking-tight text-foreground">
            {/* insert brand name here */}
          </span>
        </Link>
        <nav className="hidden sm:flex items-center gap-6 text-sm text-muted-foreground">
          <Link href="#features" className="hover:text-foreground">Features</Link>
          <Link href="#pricing" className="hover:text-foreground">Pricing</Link>
          <Link href="#contact" className="hover:text-foreground">Contact</Link>
        </nav>
      </div>
    </header>
  );
}

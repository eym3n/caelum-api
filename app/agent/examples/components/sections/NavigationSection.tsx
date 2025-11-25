'use client';

import * as FEAAS from "@sitecore-feaas/clientside/react";
import React, { useState, useEffect } from 'react';
import { Menu, X } from 'lucide-react';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import { cn } from '@/lib/utils';

interface NavLink {
  label: string;
  href: string;
}

interface NavigationSectionProps {
  logoText: string;
  links: NavLink[];
  ctaText: string;
  ctaLink: string;
}

const DEFAULT_PROPS: NavigationSectionProps = {
  logoText: "MatchMe",
  links: [
    { label: "Benefits", href: "#benefits" },
    { label: "Features", href: "#features" },
    { label: "Pricing", href: "#pricing" },
  ],
  ctaText: "Find Matches",
  ctaLink: "#cta",
};

export function NavigationSection(props: Partial<NavigationSectionProps>) {
  const { logoText, links, ctaText, ctaLink } = { ...DEFAULT_PROPS, ...props };
  const [isScrolled, setIsScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 20);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <nav
      className={clsx(
        "fixed top-0 left-0 right-0 z-50 transition-all duration-300 h-20 flex items-center",
        isScrolled ? "bg-[#18181B]/80 backdrop-blur-md shadow-lg border-b border-white/5" : "bg-transparent"
      )}
    >
      <div className="max-w-7xl mx-auto px-6 md:px-8 w-full flex items-center justify-between">
        {/* Logo */}
        <Link href="/" className="group">
          <span className="font-nunito font-bold text-2xl tracking-tight bg-gradient-to-r from-[#F97316] to-[#EC4899] bg-clip-text text-transparent">
            {logoText}
          </span>
        </Link>

        {/* Desktop Links */}
        <div className="hidden md:flex items-center gap-8">
          {links.map((link) => (
            <Link
              key={link.label}
              href={link.href}
              className="text-zinc-300 font-lato hover:text-[#F97316] transition-colors duration-150 text-sm font-medium"
            >
              {link.label}
            </Link>
          ))}
        </div>

        {/* Desktop CTA */}
        <div className="hidden md:block">
          <Link
            href={ctaLink}
            className="inline-flex items-center justify-center px-6 py-2.5 rounded-full bg-gradient-to-r from-[#F97316] to-[#EC4899] text-white font-bold tracking-wider text-sm shadow-md hover:shadow-lg hover:scale-105 transition-all duration-200 ease-in-out hover:brightness-110"
          >
            {ctaText}
          </Link>
        </div>

        {/* Mobile Toggle */}
        <button
          className="md:hidden text-zinc-200 hover:text-[#F97316] transition-colors"
          onClick={() => setMobileMenuOpen(true)}
          aria-label="Open menu"
        >
          <Menu size={28} />
        </button>
      </div>

      {/* Mobile Menu Overlay */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <motion.div
            initial={{ opacity: 0, x: "100%" }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: "100%" }}
            transition={{ type: "tween", duration: 0.3, ease: "easeInOut" }}
            className="fixed inset-0 z-[60] bg-[#121215] flex flex-col p-6 md:hidden"
          >
            <div className="flex items-center justify-between mb-12">
              <span className="font-nunito font-bold text-2xl tracking-tight bg-gradient-to-r from-[#F97316] to-[#EC4899] bg-clip-text text-transparent">
                {logoText}
              </span>
              <button
                onClick={() => setMobileMenuOpen(false)}
                className="text-zinc-200 hover:text-[#EC4899] transition-colors"
                aria-label="Close menu"
              >
                <X size={28} />
              </button>
            </div>

            <div className="flex flex-col gap-6 items-start">
              {links.map((link) => (
                <Link
                  key={link.label}
                  href={link.href}
                  onClick={() => setMobileMenuOpen(false)}
                  className="text-2xl font-lato font-medium text-zinc-300 hover:text-[#F97316] transition-colors"
                >
                  {link.label}
                </Link>
              ))}
            </div>

            <div className="mt-auto mb-8">
              <Link
                href={ctaLink}
                onClick={() => setMobileMenuOpen(false)}
                className="w-full flex items-center justify-center px-8 py-4 rounded-full bg-gradient-to-r from-[#F97316] to-[#EC4899] text-white font-bold tracking-wider text-lg shadow-lg"
              >
                {ctaText}
              </Link>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </nav>
  );
}

FEAAS.registerComponent(NavigationSection, {
  name: "navigation-section",
  title: "Navigation Bar",
  description: "Sticky navigation bar with logo, links, and CTA",
  group: "Navigation",
  properties: {
    logoText: { type: "string", title: "Logo Text" },
    links: {
      type: "array",
      title: "Navigation Links",
      items: {
        type: "object",
        properties: {
          label: { type: "string", title: "Label" },
          href: { type: "string", title: "URL" },
        },
      },
    },
    ctaText: { type: "string", title: "CTA Text" },
    ctaLink: { type: "string", title: "CTA Link" },
  },
  ui: {
    ctaLink: {
      "ui:placeholder": "Enter URL or anchor ID",
    },
  },
});

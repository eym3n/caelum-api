'use client';

import * as FEAAS from "@sitecore-feaas/clientside/react";
import React from 'react';
import Link from 'next/link';
import { cn } from '@/lib/utils';

interface FooterLink {
  label: string;
  href: string;
}

interface FooterSectionProps {
  logoText: string;
  copyright: string;
  links: FooterLink[];
}

const DEFAULT_PROPS: FooterSectionProps = {
  logoText: "MatchMe",
  copyright: "© 2024 MatchMe Inc. All rights reserved.",
  links: [
    { label: "Privacy Policy", href: "#" },
    { label: "Terms of Service", href: "#" },
  ],
};

export function FooterSection(props: Partial<FooterSectionProps>) {
  const { logoText, copyright, links } = { ...DEFAULT_PROPS, ...props };

  return (
    <footer className="w-full bg-[#121215] py-16 text-zinc-400 border-t border-white/5">
      <div className="max-w-7xl mx-auto px-6 md:px-8 flex flex-col md:flex-row justify-between items-center gap-8 text-center md:text-left">
        
        {/* Brand */}
        <div>
          <span className="font-nunito font-bold text-2xl tracking-tight bg-gradient-to-r from-[#F97316] to-[#EC4899] bg-clip-text text-transparent opacity-80 block mb-2">
            {logoText}
          </span>
          <p className="font-lato text-sm text-zinc-500">
            {copyright}
          </p>
        </div>

        {/* Links */}
        <div className="flex gap-8">
          {links.map((link, idx) => (
            <Link 
              key={idx}
              href={link.href}
              className="text-zinc-400 font-lato hover:text-[#F97316] hover:underline transition-colors duration-150 text-sm"
            >
              {link.label}
            </Link>
          ))}
        </div>
      </div>
    </footer>
  );
}

FEAAS.registerComponent(FooterSection, {
  name: "footer-section",
  title: "Footer",
  description: "Standard footer with logo and links",
  group: "Navigation",
  properties: {
    logoText: { type: "string", title: "Logo Text" },
    copyright: { type: "string", title: "Copyright Text" },
    links: {
      type: "array",
      title: "Footer Links",
      items: {
        type: "object",
        properties: {
          label: { type: "string", title: "Label" },
          href: { type: "string", title: "URL" },
        },
      },
    },
  },
});

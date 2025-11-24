'use client';

import * as FEAAS from "@sitecore-feaas/clientside/react";
import React, { useState } from 'react';
import { motion } from 'framer-motion';
import Link from 'next/link';

interface CtaSectionProps {
  headline: string;
  subtext: string;
  ctaText: string;
  consentText: string;
  privacyLinkText: string;
  privacyLinkUrl: string;
}

const DEFAULT_PROPS: CtaSectionProps = {
  headline: "Ready to Write Your Love Story?",
  subtext: "Join 1M+ singles finding real connection today.",
  ctaText: "Find Matches",
  consentText: "I agree to receive match notifications.",
  privacyLinkText: "Privacy Policy",
  privacyLinkUrl: "#"
};

const EASE_OUT = [0.16, 1, 0.3, 1] as const;

export function CtaSection(props: Partial<CtaSectionProps>) {
  const { headline, subtext, ctaText, consentText, privacyLinkText, privacyLinkUrl } = { ...DEFAULT_PROPS, ...props };
  const [loading, setLoading] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    // Simulate submission
    setTimeout(() => {
      setLoading(false);
      alert("Thanks for signing up!");
    }, 1500);
  };

  return (
    <section id="cta" className="relative w-full py-24 md:py-32 bg-[#18181B] text-zinc-200 border-t border-white/5">
      <div className="max-w-7xl mx-auto px-6 md:px-8 text-center">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, ease: EASE_OUT }}
        >
          <h2 className="font-nunito font-bold text-4xl md:text-6xl text-white mb-6">
            {headline}
          </h2>
          <p className="font-lato text-zinc-400 text-lg md:text-xl mb-12 max-w-2xl mx-auto">
            {subtext}
          </p>
        </motion.div>

        <motion.form 
          onSubmit={handleSubmit}
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, ease: EASE_OUT, delay: 0.2 }}
          className="max-w-xl mx-auto flex flex-col gap-6"
        >
          <div className="flex flex-col gap-4">
            <input 
              type="text" 
              placeholder="Name" 
              required
              className="w-full px-6 py-4 rounded-full bg-[#121215] border border-zinc-700 text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-[#F97316] focus:border-transparent transition-all"
            />
            <input 
              type="email" 
              placeholder="Email" 
              required
              className="w-full px-6 py-4 rounded-full bg-[#121215] border border-zinc-700 text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-[#F97316] focus:border-transparent transition-all"
            />
            <input 
              type="number" 
              placeholder="Age" 
              min="18"
              required
              className="w-full px-6 py-4 rounded-full bg-[#121215] border border-zinc-700 text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-[#F97316] focus:border-transparent transition-all"
            />
          </div>

          <div className="flex items-center gap-3 justify-center text-sm text-zinc-500">
             <input type="checkbox" id="consent" required className="accent-[#F97316]" />
             <label htmlFor="consent">
               {consentText} <Link href={privacyLinkUrl} className="underline hover:text-[#F97316]">{privacyLinkText}</Link>
             </label>
          </div>

          <button 
            type="submit" 
            disabled={loading}
            className="w-full py-4 rounded-full bg-gradient-to-r from-[#F97316] to-[#EC4899] text-white font-bold tracking-wider uppercase text-lg shadow-lg hover:shadow-xl hover:scale-[1.02] transition-all duration-200 ease-in-out hover:brightness-110 disabled:opacity-70 disabled:cursor-not-allowed"
          >
            {loading ? "Processing..." : ctaText}
          </button>
        </motion.form>
      </div>
    </section>
  );
}

FEAAS.registerComponent(CtaSection, {
  name: "cta-section",
  title: "Final CTA Form",
  description: "Lead capture form",
  group: "Conversion",
  properties: {
    headline: { type: "string", title: "Headline" },
    subtext: { type: "string", title: "Subtext" },
    ctaText: { type: "string", title: "Button Text" },
    consentText: { type: "string", title: "Consent Text" },
    privacyLinkText: { type: "string", title: "Privacy Link Text" },
    privacyLinkUrl: { type: "string", title: "Privacy Link URL" },
  },
});

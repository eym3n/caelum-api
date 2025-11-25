'use client';

import * as FEAAS from "@sitecore-feaas/clientside/react";
import React from 'react';
import { motion } from 'framer-motion';
import { Check } from 'lucide-react';
import Link from 'next/link';
import { cn } from '@/lib/utils';

interface PricingSectionProps {
  headline: string;
  subtext: string;
  planName: string;
  price: string;
  features: string[];
  ctaText: string;
  ctaLink: string;
}

const DEFAULT_PROPS: PricingSectionProps = {
  headline: "Unlock Premium Features.",
  subtext: "Free to match + premium features.",
  planName: "MatchMe Premium",
  price: "$19.99/month",
  features: ["Unlimited Swipes", "Advanced Filters", "See Who Likes You"],
  ctaText: "Find Matches",
  ctaLink: "#cta",
};

const EASE_OUT = [0.16, 1, 0.3, 1] as const;

export function PricingSection(props: Partial<PricingSectionProps>) {
  const { headline, subtext, planName, price, features, ctaText, ctaLink } = { ...DEFAULT_PROPS, ...props };

  return (
    <section id="pricing" className="relative w-full py-24 md:py-32 bg-[#18181B] text-zinc-200">
      <div className="max-w-7xl mx-auto px-6 md:px-8 flex flex-col items-center">
        <motion.div
           initial={{ opacity: 0, y: 20 }}
           whileInView={{ opacity: 1, y: 0 }}
           viewport={{ once: true }}
           transition={{ duration: 0.6, ease: EASE_OUT }}
           className="text-center mb-16"
        >
          <h2 className="font-nunito font-bold text-3xl md:text-5xl text-white mb-4">
            {headline}
          </h2>
          <p className="font-lato text-zinc-400 text-lg">
            {subtext}
          </p>
        </motion.div>

        <motion.div 
          initial={{ opacity: 0, y: 40 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          whileHover={{ y: -4, transition: { duration: 0.3 } }}
          transition={{ duration: 0.7, ease: EASE_OUT }}
          className="relative w-full max-w-md bg-[#28282D] rounded-3xl p-8 md:p-12 border border-[#EC4899]/30 shadow-2xl flex flex-col items-center group overflow-hidden"
        >
          {/* Glow Effect */}
          <div className="absolute inset-0 bg-[#EC4899]/5 opacity-50 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none" />
          <div className="absolute -top-32 -right-32 w-64 h-64 bg-[#EC4899]/20 blur-3xl rounded-full pointer-events-none" />

          <h3 className="font-nunito font-bold text-2xl text-white mb-2 relative z-10">{planName}</h3>
          <div className="text-4xl md:text-5xl font-nunito font-bold text-white mb-8 relative z-10">
            {price}
          </div>

          <ul className="w-full space-y-4 mb-10 relative z-10">
            {features.map((feature, idx) => (
              <li key={idx} className="flex items-center gap-3 text-zinc-300 font-lato">
                <div className="w-6 h-6 rounded-full bg-[#EC4899]/20 flex items-center justify-center text-[#EC4899] shrink-0">
                  <Check size={14} strokeWidth={3} />
                </div>
                {feature}
              </li>
            ))}
          </ul>

          <Link
            href={ctaLink}
            className="w-full py-4 rounded-full bg-gradient-to-r from-[#F97316] to-[#EC4899] text-white font-bold tracking-wider uppercase text-sm shadow-lg hover:shadow-xl hover:scale-[1.02] transition-all duration-200 ease-in-out hover:brightness-110 flex items-center justify-center relative z-10"
          >
            {ctaText}
          </Link>
        </motion.div>
      </div>
    </section>
  );
}

FEAAS.registerComponent(PricingSection, {
  name: "pricing-section",
  title: "Pricing Card",
  description: "Single centered pricing card",
  group: "Content",
  properties: {
    headline: { type: "string", title: "Headline" },
    subtext: { type: "string", title: "Subtext" },
    planName: { type: "string", title: "Plan Name" },
    price: { type: "string", title: "Price" },
    features: { type: "array", title: "Features", items: { type: "string" } },
    ctaText: { type: "string", title: "CTA Text" },
    ctaLink: { type: "string", title: "CTA Link" },
  },
});

'use client';

import * as FEAAS from "@sitecore-feaas/clientside/react";
import React from 'react';
import { motion } from 'framer-motion';
import Link from 'next/link';
import { cn } from '@/lib/utils';

interface TrustIndicator {
  label: string;
  value: string;
}

interface HeroSectionProps {
  eyebrow: string;
  headline: string;
  subtext: string;
  primaryCtaLabel: string;
  primaryCtaLink: string;
  secondaryCtaLabel: string;
  secondaryCtaLink: string;
  trustIndicators: TrustIndicator[];
}

const DEFAULT_PROPS: HeroSectionProps = {
  eyebrow: "MatchMe: The Future of Dating.",
  headline: "Find Your Perfect Match. Write Your Love Story.",
  subtext: "Find your perfect match with advanced compatibility algorithms.",
  primaryCtaLabel: "Find Matches",
  primaryCtaLink: "#cta",
  secondaryCtaLabel: "Take Quiz",
  secondaryCtaLink: "#quiz",
  trustIndicators: [
    { value: "1M+", label: "Matches" },
    { value: "Verified", label: "Profiles" }
  ],
};

const EASE_OUT = [0.16, 1, 0.3, 1] as const;

export function HeroSection(props: Partial<HeroSectionProps>) {
  const { eyebrow, headline, subtext, primaryCtaLabel, primaryCtaLink, secondaryCtaLabel, secondaryCtaLink, trustIndicators } = { ...DEFAULT_PROPS, ...props };

  return (
    <section className="relative w-full min-h-[80vh] flex flex-col items-center justify-center overflow-hidden bg-[#18181B] pt-32 pb-20 md:pt-40 md:pb-32 px-6 md:px-8">
      {/* Cinematic Background Gradient */}
      <div 
        className="absolute inset-0 pointer-events-none"
        style={{
          background: `radial-gradient(50% 50% at 50% 50%, rgba(249, 115, 22, 0.2) 0%, rgba(24, 24, 27, 0) 70%)`
        }}
      />
      
      {/* Content Container */}
      <div className="relative z-10 max-w-4xl mx-auto text-center flex flex-col items-center">
        
        {/* Eyebrow */}
        <motion.span 
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, ease: EASE_OUT }}
          className="text-[#F97316] font-bold tracking-widest uppercase text-sm mb-6"
        >
          {eyebrow}
        </motion.span>

        {/* Headline */}
        <motion.h1 
          initial={{ opacity: 0, scale: 0.95 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7, ease: EASE_OUT, delay: 0.1 }}
          className="font-nunito font-bold text-4xl md:text-6xl lg:text-7xl text-white leading-[1.1] mb-6 tracking-tight"
        >
          {headline}
        </motion.h1>

        {/* Subtext */}
        <motion.p 
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, ease: EASE_OUT, delay: 0.2 }}
          className="font-lato text-zinc-300 text-lg md:text-xl max-w-2xl mb-10 leading-relaxed"
        >
          {subtext}
        </motion.p>

        {/* CTAs */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, ease: EASE_OUT, delay: 0.3 }}
          className="flex flex-col sm:flex-row items-center gap-4 mb-16 w-full sm:w-auto"
        >
          <Link 
            href={primaryCtaLink}
            className="w-full sm:w-auto px-8 py-4 rounded-full bg-gradient-to-r from-[#F97316] to-[#EC4899] text-white font-bold tracking-wider uppercase text-sm shadow-lg hover:shadow-xl hover:scale-[1.02] transition-all duration-200 ease-in-out hover:brightness-110 flex items-center justify-center"
          >
            {primaryCtaLabel}
          </Link>
          <Link 
            href={secondaryCtaLink}
            className="w-full sm:w-auto px-8 py-4 rounded-full border-2 border-[#EC4899] text-[#EC4899] font-lato font-bold tracking-wide uppercase text-sm bg-transparent hover:bg-pink-900/10 transition-all duration-200 ease-in-out flex items-center justify-center"
          >
            {secondaryCtaLabel}
          </Link>
        </motion.div>

        {/* Trust Indicators */}
        <motion.div
           initial={{ opacity: 0 }}
           whileInView={{ opacity: 1 }}
           viewport={{ once: true }}
           transition={{ duration: 0.8, delay: 0.5 }}
           className="flex gap-8 mb-20 border-t border-white/5 pt-8"
        >
          {trustIndicators.map((stat, idx) => (
             <div key={idx} className="flex flex-col items-center">
               <span className="text-2xl font-nunito font-bold text-white">{stat.value}</span>
               <span className="text-xs text-zinc-500 uppercase tracking-wider">{stat.label}</span>
             </div>
          ))}
        </motion.div>

        {/* Profile Showcase (Layered Cards) */}
        <div className="relative w-full max-w-3xl h-64 md:h-80 perspective-1000">
           {/* Card 1 (Left Back) */}
           <motion.div 
             initial={{ opacity: 0, x: -50, rotate: -10 }}
             whileInView={{ opacity: 0.6, x: 0, rotate: -6 }}
             viewport={{ once: true }}
             transition={{ duration: 0.8, ease: EASE_OUT, delay: 0.4 }}
             className="absolute left-4 md:left-12 top-4 w-48 md:w-64 h-64 md:h-72 bg-[#28282D] rounded-2xl border border-[#EC4899]/20 shadow-2xl flex flex-col p-4 z-0"
           >
              <div className="w-full h-32 bg-zinc-800 rounded-lg mb-3 animate-pulse opacity-50"></div>
              <div className="w-3/4 h-4 bg-zinc-700 rounded mb-2"></div>
              <div className="w-1/2 h-4 bg-zinc-700 rounded"></div>
           </motion.div>

           {/* Card 2 (Right Back) */}
           <motion.div 
             initial={{ opacity: 0, x: 50, rotate: 10 }}
             whileInView={{ opacity: 0.6, x: 0, rotate: 6 }}
             viewport={{ once: true }}
             transition={{ duration: 0.8, ease: EASE_OUT, delay: 0.5 }}
             className="absolute right-4 md:right-12 top-4 w-48 md:w-64 h-64 md:h-72 bg-[#28282D] rounded-2xl border border-[#F97316]/20 shadow-2xl flex flex-col p-4 z-0"
           >
              <div className="w-full h-32 bg-zinc-800 rounded-lg mb-3 animate-pulse opacity-50"></div>
              <div className="w-3/4 h-4 bg-zinc-700 rounded mb-2"></div>
              <div className="w-1/2 h-4 bg-zinc-700 rounded"></div>
           </motion.div>

           {/* Card 3 (Center Front) */}
           <motion.div 
             initial={{ opacity: 0, y: 50 }}
             whileInView={{ opacity: 1, y: 0 }}
             viewport={{ once: true }}
             animate={{ y: [0, -10, 0] }}
             transition={{ 
                opacity: { duration: 0.8, ease: EASE_OUT, delay: 0.6 },
                y: { repeat: Infinity, duration: 6, ease: "easeInOut" } // Floating effect
             }}
             className="absolute left-1/2 -translate-x-1/2 top-0 w-56 md:w-72 h-72 md:h-80 bg-[#28282D] rounded-2xl border border-white/10 shadow-[0_20px_50px_rgba(0,0,0,0.5)] flex flex-col p-4 z-10"
           >
              <div className="relative w-full h-40 bg-zinc-800 rounded-lg mb-4 overflow-hidden group">
                 <div className="absolute inset-0 bg-gradient-to-tr from-[#F97316]/20 to-[#EC4899]/20 group-hover:opacity-100 transition-opacity duration-500"></div>
                 {/* Mock User Image Placeholder */}
                 <div className="w-full h-full flex items-center justify-center text-zinc-600">
                    <svg className="w-12 h-12" fill="currentColor" viewBox="0 0 24 24"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>
                 </div>
              </div>
              <div className="w-3/4 h-5 bg-zinc-700 rounded mb-3"></div>
              <div className="w-full h-16 bg-zinc-800/50 rounded p-2 flex gap-2">
                 <div className="w-full h-2 bg-zinc-700 rounded mt-1"></div>
                 <div className="w-2/3 h-2 bg-zinc-700 rounded mt-1"></div>
              </div>
              <div className="mt-auto flex gap-2">
                 <div className="w-8 h-8 rounded-full bg-[#EC4899]/20 flex items-center justify-center text-[#EC4899]">
                    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/></svg>
                 </div>
                 <div className="w-8 h-8 rounded-full bg-zinc-700 flex items-center justify-center">
                    <svg className="w-4 h-4 text-zinc-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12"/></svg>
                 </div>
              </div>
           </motion.div>
        </div>
      </div>
    </section>
  );
}

FEAAS.registerComponent(HeroSection, {
  name: "hero-section",
  title: "Hero Section",
  description: "Cinematic hero with radial gradient and profile showcase",
  group: "Hero",
  properties: {
    eyebrow: { type: "string", title: "Eyebrow Text" },
    headline: { type: "string", title: "Headline" },
    subtext: { type: "string", title: "Subtext" },
    primaryCtaLabel: { type: "string", title: "Primary CTA Label" },
    primaryCtaLink: { type: "string", title: "Primary CTA Link" },
    secondaryCtaLabel: { type: "string", title: "Secondary CTA Label" },
    secondaryCtaLink: { type: "string", title: "Secondary CTA Link" },
    trustIndicators: {
       type: "array",
       title: "Trust Stats",
       items: {
          type: "object",
          properties: {
             label: { type: "string", title: "Label" },
             value: { type: "string", title: "Value" }
          }
       }
    }
  },
});

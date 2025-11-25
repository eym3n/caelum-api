'use client';

import * as FEAAS from "@sitecore-feaas/clientside/react";
import React from 'react';
import { motion } from 'framer-motion';
import { Heart, Shield, MessageCircle } from 'lucide-react';
import clsx from 'clsx';
import { cn } from '@/lib/utils';

interface BenefitItem {
  title: string;
  description: string;
  iconName: string;
}

interface BenefitsSectionProps {
  headline: string;
  subtext: string;
  benefits: BenefitItem[];
}

const DEFAULT_PROPS: BenefitsSectionProps = {
  headline: "Why MatchMe? Hope, Connection, Excitement.",
  subtext: "Discover the core advantages that make MatchMe different.",
  benefits: [
    { 
      title: "Quality Matches", 
      description: "Our algorithm filters out noise to bring you people who truly align with your values.", 
      iconName: "Heart" 
    },
    { 
      title: "Safe Dating", 
      description: "Verified profiles and privacy-first features ensure you can date with complete peace of mind.", 
      iconName: "Shield" 
    },
    { 
      title: "Easy Communication", 
      description: "Break the ice effortlessly with our intuitive messaging and connection tools.", 
      iconName: "MessageCircle" 
    },
  ],
};

const iconMap: Record<string, React.ReactNode> = {
  Heart: <Heart size={32} />,
  Shield: <Shield size={32} />,
  MessageCircle: <MessageCircle size={32} />,
};

const EASE_OUT = [0.16, 1, 0.3, 1] as const;

export function BenefitsSection(props: Partial<BenefitsSectionProps>) {
  const { headline, subtext, benefits } = { ...DEFAULT_PROPS, ...props };

  return (
    <section id="benefits" className="relative w-full py-24 md:py-32 bg-[#18181B] text-zinc-200">
      <div className="max-w-6xl mx-auto px-6 md:px-8">
        
        {/* Header */}
        <div className="text-center mb-20">
          <motion.h2 
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, ease: EASE_OUT }}
            className="font-nunito font-bold text-3xl md:text-5xl text-white mb-6"
          >
            {headline}
          </motion.h2>
          <motion.p 
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, ease: EASE_OUT, delay: 0.1 }}
            className="font-lato text-zinc-400 text-lg md:text-xl max-w-2xl mx-auto"
          >
            {subtext}
          </motion.p>
        </div>

        {/* Stepping Stones Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 md:gap-6">
          {benefits.map((benefit, idx) => (
            <motion.div
              key={idx}
              initial={{ opacity: 0, y: 40 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6, ease: EASE_OUT, delay: idx * 0.15 }}
              className={clsx(
                "group relative bg-[#222225] rounded-2xl p-8 border border-white/5 hover:border-[#EC4899]/30 transition-all duration-300",
                // Stepping stones offset
                idx === 1 && "md:mt-8",
                idx === 2 && "md:mt-16"
              )}
            >
              <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-[#EC4899]/0 to-[#EC4899]/0 group-hover:from-[#EC4899]/5 group-hover:to-transparent transition-all duration-500" />
              
              <div className="relative z-10">
                <div className="w-14 h-14 rounded-full bg-[#EC4899]/10 flex items-center justify-center text-[#EC4899] mb-6 group-hover:scale-110 transition-transform duration-300">
                  {iconMap[benefit.iconName] || <Heart size={32} />}
                </div>
                
                <h3 className="text-xl font-nunito font-bold text-white mb-4 group-hover:text-[#F97316] transition-colors duration-200">
                  {benefit.title}
                </h3>
                
                <p className="font-lato text-zinc-400 leading-relaxed">
                  {benefit.description}
                </p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

FEAAS.registerComponent(BenefitsSection, {
  name: "benefits-section",
  title: "Benefits Grid",
  description: "Three-column grid with stepping stone layout",
  group: "Content",
  properties: {
    headline: { type: "string", title: "Headline" },
    subtext: { type: "string", title: "Subtext" },
    benefits: {
      type: "array",
      title: "Benefits",
      items: {
        type: "object",
        properties: {
          title: { type: "string", title: "Title" },
          description: { type: "string", title: "Description" },
          iconName: { type: "string", title: "Icon Name (Heart, Shield, MessageCircle)" },
        },
      },
    },
  },
});

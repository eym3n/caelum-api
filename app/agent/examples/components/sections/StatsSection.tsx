'use client';

import * as FEAAS from "@sitecore-feaas/clientside/react";
import React from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
interface StatItem {
  value: string;
  label: string;
}

interface StatsSectionProps {
  headline: string;
  stats: StatItem[];
}

const DEFAULT_PROPS: StatsSectionProps = {
  headline: "Our Community by the Numbers.",
  stats: [
    { value: "1M+", label: "Matches Made" },
    { value: "100%", label: "Profiles Verified" },
    { value: "Yes", label: "GDPR Compliant" },
    { value: "Always", label: "Free Communication" }
  ],
};

const EASE_OUT = [0.16, 1, 0.3, 1] as const;

export function StatsSection(props: Partial<StatsSectionProps>) {
  const { headline, stats } = { ...DEFAULT_PROPS, ...props };

  return (
    <section className="relative w-full py-24 bg-[#18181B] text-zinc-200">
      <div className="max-w-5xl mx-auto px-6 md:px-8">
        <motion.h2 
          initial={{ opacity: 0, scale: 0.95 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, ease: EASE_OUT }}
          className="text-center font-nunito font-bold text-2xl md:text-4xl text-white mb-16"
        >
          {headline}
        </motion.h2>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 md:gap-12">
          {stats.map((stat, idx) => (
            <motion.div
              key={idx}
              initial={{ opacity: 0 }}
              whileInView={{ opacity: 1 }}
              viewport={{ once: true }}
              transition={{ duration: 0.8, ease: EASE_OUT, delay: idx * 0.1 }}
              className="flex flex-col items-center text-center"
            >
              <span className="block text-4xl md:text-6xl font-nunito font-bold mb-2 bg-gradient-to-r from-[#F97316] to-[#EC4899] bg-clip-text text-transparent">
                {stat.value}
              </span>
              <span className="text-zinc-400 font-lato text-sm uppercase tracking-wider font-medium">
                {stat.label}
              </span>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

FEAAS.registerComponent(StatsSection, {
  name: "stats-section",
  title: "Stats Grid",
  description: "Simple stats grid with gradient numbers",
  group: "Content",
  properties: {
    headline: { type: "string", title: "Headline" },
    stats: {
      type: "array",
      title: "Stats",
      items: {
        type: "object",
        properties: {
          value: { type: "string", title: "Value" },
          label: { type: "string", title: "Label" },
        },
      },
    },
  },
});

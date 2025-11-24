'use client';

import * as FEAAS from "@sitecore-feaas/clientside/react";
import React from 'react';
import { motion } from 'framer-motion';
import Link from 'next/link';
import clsx from 'clsx';

interface FeatureItem {
  title: string;
  description: string;
  hasCta?: boolean;
  ctaText?: string;
  ctaLink?: string;
}

interface FeaturesSectionProps {
  headline: string;
  features: FeatureItem[];
}

const DEFAULT_PROPS: FeaturesSectionProps = {
  headline: "Compatibility Engineered for Romance.",
  features: [
    {
      title: "Compatibility Quiz",
      description: "Our scientifically-backed quiz dives deep into your personality, values, and relationship goals to find your true equal.",
      hasCta: true,
      ctaText: "Take Quiz",
      ctaLink: "#quiz"
    },
    {
      title: "Video Profiles",
      description: "See the real person behind the profile with 30-second video intros that capture personality better than photos ever could.",
      hasCta: false
    },
    {
      title: "In-app Messaging",
      description: "Secure, private, and intuitive messaging keeps your conversation flowing without sharing personal contact details too soon.",
      hasCta: false
    },
    {
      title: "Safety Features",
      description: "From photo verification to advanced reporting tools, we've built a fortress around your dating experience.",
      hasCta: false
    }
  ]
};

const EASE_OUT = [0.16, 1, 0.3, 1] as const;

export function FeaturesSection(props: Partial<FeaturesSectionProps>) {
  const { headline, features } = { ...DEFAULT_PROPS, ...props };

  return (
    <section id="features" className="relative w-full py-24 md:py-32 overflow-hidden">
      {/* Distinct Background */}
      <div 
        className="absolute inset-0 z-0"
        style={{ background: 'linear-gradient(135deg, #18181B 0%, #121215 100%)' }}
      />

      <div className="relative z-10 max-w-7xl mx-auto px-6 md:px-8">
        <motion.h2 
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, ease: EASE_OUT }}
          className="text-center font-nunito font-bold text-3xl md:text-5xl text-white mb-20"
        >
          {headline}
        </motion.h2>

        <div className="flex flex-col gap-24">
          {features.map((feature, idx) => {
            const isEven = idx % 2 === 0;
            return (
              <div key={idx} className="grid grid-cols-1 md:grid-cols-2 gap-12 md:gap-24 items-center">
                {/* Text Block */}
                <motion.div
                  initial={{ opacity: 0, x: isEven ? -50 : 50 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.7, ease: EASE_OUT }}
                  className={clsx(
                    "flex flex-col items-start",
                    !isEven && "md:order-last"
                  )}
                >
                  <h3 className="text-[#F97316] font-nunito font-bold text-2xl md:text-3xl mb-6">
                    {feature.title}
                  </h3>
                  <p className="font-lato text-zinc-300 text-lg leading-relaxed mb-8">
                    {feature.description}
                  </p>
                  {feature.hasCta && (
                    <Link 
                      href={feature.ctaLink || "#"}
                      className="inline-flex items-center justify-center px-8 py-3 rounded-full border-2 border-[#EC4899] text-[#EC4899] font-lato font-bold tracking-wide uppercase text-sm bg-transparent hover:bg-pink-900/10 transition-all duration-200 ease-in-out"
                    >
                      {feature.ctaText}
                    </Link>
                  )}
                </motion.div>

                {/* Visual Block (Mock UI) */}
                <motion.div
                  initial={{ opacity: 0, x: isEven ? 50 : -50 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.7, ease: EASE_OUT }}
                  className="w-full h-64 md:h-96 bg-white/5 backdrop-blur-sm rounded-2xl border border-white/10 flex items-center justify-center relative overflow-hidden group"
                >
                  {/* Decorative internal elements for mock UI */}
                  <div className="absolute inset-x-8 top-8 bottom-8 bg-[#18181B]/50 rounded-xl border border-white/5 p-6 flex flex-col gap-4">
                     <div className="w-1/3 h-4 bg-zinc-700/50 rounded animate-pulse" />
                     <div className="w-2/3 h-4 bg-zinc-700/30 rounded" />
                     <div className="flex-1 bg-zinc-800/20 rounded-lg mt-4 border border-white/5 flex items-center justify-center">
                        <span className="text-zinc-600 font-nunito font-bold text-4xl opacity-20">{idx + 1}</span>
                     </div>
                  </div>
                  {/* Hover effect */}
                  <div className="absolute inset-0 bg-gradient-to-tr from-[#F97316]/5 to-[#EC4899]/5 opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                </motion.div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

FEAAS.registerComponent(FeaturesSection, {
  name: "features-section",
  title: "Features Serpentine",
  description: "Alternating feature blocks with text and mock visuals",
  group: "Content",
  properties: {
    headline: { type: "string", title: "Headline" },
    features: {
      type: "array",
      title: "Features",
      items: {
        type: "object",
        properties: {
          title: { type: "string", title: "Title" },
          description: { type: "string", title: "Description" },
          hasCta: { type: "boolean", title: "Show CTA?" },
          ctaText: { type: "string", title: "CTA Text" },
          ctaLink: { type: "string", title: "CTA Link" },
        },
      },
    },
  },
});

'use client';

import * as FEAAS from "@sitecore-feaas/clientside/react";
import React from 'react';
import { motion } from 'framer-motion';

interface TestimonialItem {
  quote: string;
  author: string;
}

interface TestimonialsSectionProps {
  headline: string;
  testimonials: TestimonialItem[];
}

const DEFAULT_PROPS: TestimonialsSectionProps = {
  headline: "Real Love Stories Start Here.",
  testimonials: [
    { quote: "Found my soulmate.", author: "A. Johnson" },
    { quote: "Safe and fun.", author: "B. Lee" }
  ],
};

const EASE_OUT = [0.16, 1, 0.3, 1] as const;

export function TestimonialsSection(props: Partial<TestimonialsSectionProps>) {
  const { headline, testimonials } = { ...DEFAULT_PROPS, ...props };

  return (
    <section className="relative w-full py-24 md:py-32 bg-[#18181B] text-zinc-200">
      <div className="max-w-6xl mx-auto px-6 md:px-8">
        <motion.h2 
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, ease: EASE_OUT }}
          className="text-center font-nunito font-bold text-3xl md:text-5xl text-white mb-20"
        >
          {headline}
        </motion.h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 md:gap-12">
          {testimonials.map((item, idx) => (
            <motion.div
              key={idx}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6, ease: EASE_OUT, delay: idx * 0.1 }}
              className="bg-[#28282D] rounded-3xl p-10 md:p-12 border border-white/5 relative flex flex-col justify-between"
            >
              <div className="mb-8">
                 {/* Stylized Quote Mark */}
                <span className="block text-[#F97316] text-6xl font-serif leading-none opacity-80 mb-4">“</span>
                <p className="font-lato text-2xl md:text-3xl font-light italic text-zinc-100 leading-relaxed">
                  {item.quote}
                </p>
              </div>
              
              <div className="flex items-center gap-4">
                <div className="w-10 h-1 bg-[#F97316] rounded-full" />
                <span className="font-nunito font-bold text-[#F97316] text-lg uppercase tracking-wide">
                  {item.author}
                </span>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

FEAAS.registerComponent(TestimonialsSection, {
  name: "testimonials-section",
  title: "Testimonials",
  description: "Two-column testimonial grid",
  group: "Content",
  properties: {
    headline: { type: "string", title: "Headline" },
    testimonials: {
      type: "array",
      title: "Testimonials",
      items: {
        type: "object",
        properties: {
          quote: { type: "string", title: "Quote" },
          author: { type: "string", title: "Author" },
        },
      },
    },
  },
});

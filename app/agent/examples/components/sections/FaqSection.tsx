'use client';

import * as FEAAS from "@sitecore-feaas/clientside/react";
import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Plus, Minus } from 'lucide-react';
import clsx from 'clsx';

interface FaqItem {
  question: string;
  answer: string;
}

interface FaqSectionProps {
  headline: string;
  subtext: string;
  questions: FaqItem[];
}

const DEFAULT_PROPS: FaqSectionProps = {
  headline: "Questions About Safety and Privacy?",
  subtext: "We address your biggest concerns.",
  questions: [
    { question: "Are there fake profiles on MatchMe?", answer: "We use AI-driven verification and manual reviews to ensure every profile is real." },
    { question: "What is the true cost of the app?", answer: "MatchMe is free to download and match. Premium features unlock unlimited swipes and advanced filters." },
    { question: "How is my privacy protected?", answer: "We use end-to-end encryption and never sell your data to third parties. You have full control over what you share." },
  ],
};

const EASE_OUT = [0.16, 1, 0.3, 1] as const;

export function FaqSection(props: Partial<FaqSectionProps>) {
  const { headline, subtext, questions } = { ...DEFAULT_PROPS, ...props };
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  const toggleIndex = (index: number) => {
    setOpenIndex(openIndex === index ? null : index);
  };

  return (
    <section className="relative w-full py-24 bg-[#18181B] text-zinc-200">
      <div className="max-w-7xl mx-auto px-6 md:px-8 grid grid-cols-1 md:grid-cols-3 gap-12 md:gap-24">
        {/* Left Column: Header */}
        <motion.div 
          initial={{ opacity: 0, x: -20 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, ease: EASE_OUT }}
          className="md:col-span-1"
        >
          <h2 className="font-nunito font-bold text-3xl md:text-4xl text-white mb-6">
            {headline}
          </h2>
          <p className="font-lato text-zinc-400 text-lg">
            {subtext}
          </p>
        </motion.div>

        {/* Right Column: Accordion */}
        <div className="md:col-span-2 flex flex-col">
          {questions.map((item, idx) => (
            <motion.div
              key={idx}
              initial={{ opacity: 0, y: 10 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, ease: EASE_OUT, delay: idx * 0.1 }}
              className="border-b border-zinc-800"
            >
              <button
                onClick={() => toggleIndex(idx)}
                className="w-full flex items-center justify-between py-6 text-left group hover:bg-[#121215]/50 transition-colors px-4 rounded-lg -mx-4"
                aria-expanded={openIndex === idx}
              >
                <span className="font-nunito font-bold text-lg md:text-xl text-zinc-200 group-hover:text-white transition-colors">
                  {item.question}
                </span>
                <span className={clsx("text-[#F97316] transition-transform duration-300", openIndex === idx && "rotate-180")}>
                  {openIndex === idx ? <Minus size={24} /> : <Plus size={24} />}
                </span>
              </button>
              <AnimatePresence>
                {openIndex === idx && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.3, ease: "easeInOut" }}
                    className="overflow-hidden"
                  >
                    <div className="pb-8 pt-2 pl-4 md:pl-0 pr-4 font-lato text-zinc-400 leading-relaxed">
                      {item.answer}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

FEAAS.registerComponent(FaqSection, {
  name: "faq-section",
  title: "FAQ Accordion",
  description: "Two-column FAQ with accordion",
  group: "Content",
  properties: {
    headline: { type: "string", title: "Headline" },
    subtext: { type: "string", title: "Subtext" },
    questions: {
      type: "array",
      title: "Questions",
      items: {
        type: "object",
        properties: {
          question: { type: "string", title: "Question" },
          answer: { type: "string", title: "Answer" },
        },
      },
    },
  },
});

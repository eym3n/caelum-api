import type { FeatureItem, TestimonialItem, PricingPlan, FAQItem } from "@/types/marketing";

export const features: FeatureItem[] = [
  { key: "feature-1", title: "Showcase a core benefit", description: "Explain the primary outcome your product unlocks in one concise sentence.", icon: "CheckCircle2" },
  { key: "feature-2", title: "Highlight an automation", description: "Describe how workflows become faster, easier, or more consistent.", icon: "Sparkles" },
  { key: "feature-3", title: "Surface real-time insight", description: "Call out dashboards, reporting, or collaboration superpowers.", icon: "BarChart3" },
  { key: "feature-4", title: "Keep teams aligned", description: "Mention visibility, shared status, or approvals across stakeholders.", icon: "Users" },
  { key: "feature-5", title: "Secure by default", description: "Reassure visitors about compliance, reliability, or uptime guarantees.", icon: "ShieldCheck" },
  { key: "feature-6", title: "Extensible platform", description: "Invite readers to explore integrations, APIs, or tailored workflows.", icon: "Puzzle" },
];

export const testimonials: TestimonialItem[] = [
  {
    quote: "Swap in a short customer quote that spotlights a measurable result or transformation.",
    author: "Customer Name",
    company: "Company or Team",
  },
  {
    quote: "Include social proof that reinforces trust, credibility, or ease of use.",
    author: "Customer Name",
    company: "Company or Team",
  },
];

export const pricing: PricingPlan[] = [
  {
    id: "starter",
    name: "Starter",
    price: "$0",
    features: ["Great for getting started", "Core features enabled", "Community support"],
    ctaLabel: "Choose Starter",
  },
  {
    id: "growth",
    name: "Growth",
    price: "$49",
    highlight: true,
    features: ["Everything in Starter", "Advanced analytics & automations", "Priority support"],
    ctaLabel: "Choose Growth",
  },
  {
    id: "scale",
    name: "Scale",
    price: "Custom",
    features: ["Tailored onboarding", "Custom workflows", "Dedicated success team"],
    ctaLabel: "Contact sales",
  },
];

export const faqs: FAQItem[] = [
  { q: "How long does implementation take?", a: "Use this space to outline your onboarding timeline and any available guidance." },
  { q: "Can we change plans later?", a: "Reassure visitors that pricing tiers are flexible and upgrade-friendly." },
  { q: "What support is included?", a: "Describe your support channels, documentation, and customer success approach." },
];

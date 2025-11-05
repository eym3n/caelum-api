export interface FeatureItem {
  key: string;
  title: string;
  description: string;
  icon: string; // lucide icon name
}

export interface TestimonialItem {
  quote: string;
  author: string;
  role?: string;
  company?: string;
}

export interface PricingPlan {
  id: string;
  name: string;
  price: string; // e.g., "$29/mo"
  highlight?: boolean;
  features: string[];
  ctaLabel: string;
}

export interface FAQItem {
  q: string;
  a: string;
}

import { 
  NavigationSection, 
  HeroSection, 
  BenefitsSection,
  FeaturesSection,
  TestimonialsSection,
  StatsSection,
  PricingSection,
  FaqSection,
  CtaSection,
  FooterSection
} from "@/components/sections";

export default function Home() {
  return (
    <main className="bg-[#18181B] min-h-screen text-zinc-200 selection:bg-[#EC4899] selection:text-white">
      <NavigationSection />
      <HeroSection />
      <BenefitsSection />
      <FeaturesSection />
      <TestimonialsSection />
      <StatsSection />
      <PricingSection />
      <FaqSection />
      <CtaSection />
      <FooterSection />
    </main>
  );
}

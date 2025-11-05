import HeroSection from "@/components/sections/hero-section";
import BenefitsSection from "@/components/sections/benefits-section";
import FeaturesSection from "@/components/sections/features-section";
// import ClientsSection from "@/components/sections/clients-section";
import ReviewsSection from "@/components/sections/reviews-section";
import PricingSection from "@/components/sections/pricing-section";
import FAQSection from "@/components/sections/faq-section";
import CTASection from "@/components/sections/cta-section";
import FooterSection from "@/components/sections/footer-section";

export default function Home() {
  return (
    <main>
      <HeroSection />
      <BenefitsSection />
      <FeaturesSection />
      <ReviewsSection />
      <PricingSection />
      <FAQSection />
      <CTASection />
      <FooterSection />
    </main>
  );
}

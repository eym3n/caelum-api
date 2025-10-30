# Aceternity UI Quick Reference

Use these go-to components to craft layered, animated marketing experiences. Install via:

```bash
npx shadcn@latest add @aceternity/<package>
```

## Hero Starters
- **`spotlight` / `spotlight-new`** – pointer-driven spotlight highlight; pair with bold typography.
- **`dotted-glow-background`** + **`sparkles`** – layered hero backdrop with pulsing dots and particle shimmer.
- **`hero-sections`** – prebuilt hero layouts ready for CTA blocks.
- **`hero-parallax`** – scroll-responsive hero composition.

## Background Depth
- **`aurora-background`** – animated gradient haze for premium feel.
- **`background-beams`** or **`background-beams-with-collision`** – kinetic beams behind content modules.
- **`wavy-background`** – soft wave separators between sections.
- **`canvas-reveal-effect`** – dramatic reveal on scroll.

## Storytelling & Motion
- **`sticky-scroll-reveal`** – perfect for process timelines and feature walkthroughs.
- **`parallax-scroll`** – depth for imagery galleries.
- **`timeline`** – chronological storytelling with built-in motion.
- **`infinite-moving-cards`** – logo/partner marquee.

## Trust & Testimonials
- **`testimonials`** – animated testimonial slider.
- **`apple-cards-carousel`** – premium case study carousel.
- **`floating-dock`** – floating CTA or quick navigation dock.

## Buttons & CTAs
- **`moving-border`** – animated border CTA button.
- **`stateful-button`** – loading/success flows for forms.
- **`hover-border-gradient`** – vibrant hover treatments.

## Interactive Cards
- **`card-stack`** – layered deck reveals.
- **`focus-cards`** – dynamic hover focus for feature grids.
- **`expandable-card`** – collapsible detail card.

## Supplementary Effects
- **`floating-navbar`** – floating header with micro-interactions.
- **`following-pointer`** / **`pointer-highlight`** – custom cursor aesthetics.
- **`layout-grid`** / **`bento-grid`** – quick multi-column layouts.

### Installation Checklist
1. Ensure `motion`, `clsx`, `tailwind-merge`, and `cn` helper are present.
2. Install component via `shadcn add`.
3. Add required CSS (keyframes/variables) to `app/globals.css`.
4. Import component from `@/components/<name>` and wrap with Framer Motion transitions as needed.
5. Record the component usage in architecture/planner state to avoid duplication.


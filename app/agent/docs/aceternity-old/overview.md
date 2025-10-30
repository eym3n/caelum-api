# Aceternity UI – Overview & Setup

Aceternity UI is an open-source collection of interactive React components built with Tailwind CSS and the Framer Motion/Motion animation library. It ships background effects, hero modules, cards, scroll/parallax widgets, animated text, navbars, forms, loaders, and more—all designed to drop directly into a Next.js project.

This guide covers the essential steps to start using Aceternity UI inside a Next.js App Router project.

## 1. Create or Reuse a Next.js Project

### 1.1 Scaffold the project

```bash
npx create-next-app@latest my-app

# Enable: TypeScript, ESLint, Tailwind CSS, App Router, src/ directory

cd my-app
npm run dev
```

You can also run `npm create next-app@latest` (interactive prompts behave the same). The official installation guide lists the expected answers.[^1]

### 1.2 Add Tailwind CSS (if missing)

If Tailwind was not enabled during scaffolding:

```bash
npm install tailwindcss @tailwindcss/postcss @tailwindcss/cli
```

Create or update `app/globals.css`:

```css
@import "tailwindcss";

@theme inline {
  --font-display: "Inter", "sans-serif";
  --color-primary-500: oklch(0.84 0.18 117.33);
  --spacing: 0.25rem;
}
```

Configure PostCSS to use `@tailwindcss/postcss` and restart the dev server.[^2]

### 1.3 Install shared utilities

Many Aceternity components rely on class merging and Motion. Install the recommended utilities and add the `cn` helper:

```bash
npm install motion clsx tailwind-merge
```

```ts
// lib/utils.ts
import { ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

> **React 19 / Next.js 15 note:** You may need `framer-motion`/`motion` version `12.0.0-alpha.1` with peer dependency overrides. Check the Aceternity utilities page for the latest advice.[^3]

### 1.4 Initialise the shadcn CLI

Aceternity distributes components via the shadcn CLI. Run it once per project:

```bash
npx shadcn@latest init
```

Choose the style, base colour, and whether to use CSS variables based on your design system.[^4]

### 1.5 Add an Aceternity component

Install any component with:

```bash
npx shadcn@latest add @aceternity/<component-package>
```

Example – Dotted Glow Background:

```bash
npx shadcn@latest add @aceternity/dotted-glow-background
```

Each component page lists the exact package name, props, and any extra CSS you must add.[^5]

## 2. Render Components in Next.js

After installation, the CLI places the component under `components/`. Import and render it in your page or layout. Some components also require keyframes or CSS variables in `globals.css`—check the docs before shipping.

```tsx
// app/page.tsx
import { DottedGlowBackground } from "@/components/dotted-glow-background";
import { Sparkles } from "@/components/sparkles";

export default function Home() {
  return (
    <main className="relative h-screen overflow-hidden">
      <DottedGlowBackground
        gap={12}
        radius={2}
        color="rgba(0,0,0,0.7)"
        glowColor="rgba(0, 170, 255, 0.85)"
        opacity={0.6}
      />

      <Sparkles
        particleColor="rgb(255, 215, 0)"
        particleSize={3}
        speed={2}
        particleDensity={80}
      />

      <section className="relative z-10 flex h-full items-center justify-center">
        <h1 className="text-4xl font-bold text-white">
          Welcome to my Aceternity page
        </h1>
      </section>
    </main>
  );
}
```

`DottedGlowBackground` paints a pulsing dot grid while `Sparkles` adds particle effects. Layer them beneath your content for a premium hero.

## 3. Extra CSS Warnings

Some components require additional CSS (e.g., Background Ripple Effect keyframes, Gradient Animation CSS variables). Always read the “Installation” notes on the component page and update `app/globals.css` accordingly before running the component.

[^1]: [Install Next.js](https://ui.aceternity.com/docs/install-nextjs)
[^2]: [Install Tailwind CSS](https://ui.aceternity.com/docs/install-tailwindcss)
[^3]: [React 19 support notes](https://ui.aceternity.com/docs/add-utilities)
[^4]: [shadcn CLI options](https://ui.aceternity.com/docs/cli)
[^5]: [Dotted Glow Background install](https://ui.aceternity.com/components/dotted-glow-background)



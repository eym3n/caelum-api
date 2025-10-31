
# 🧠 AI UI Builder Manifest

*Manifest for autonomous Next.js + Tailwind UI generation*

## 🏗️ Purpose

This document defines the **visual standards**, **coding conventions**, and **quality control rules** for any AI agent generating front-end code using **Next.js**, **Tailwind CSS**, and related UI frameworks (e.g. `shadcn/ui`).
The goal: make every generated app *look professionally designed by default*.

---

## 🎨 Design Philosophy

* **Simplicity First** — prefer clear structure over excessive decoration.
* **Opinionated Defaults** — consistent padding, spacing, radii, and typography across pages.
* **Predictable Rhythm** — follow an 8pt vertical rhythm (`2, 4, 6, 8, 12, 16` spacing units).
* **Familiar Modern Aesthetic** — minimalism, rounded edges, subtle shadows, warm neutrals.
* **Responsiveness by Default** — mobile-first with defined breakpoints at `sm`, `md`, `lg`, `xl`, `2xl`.
* **Accessibility** — keyboard navigability, color contrast ≥ 4.5:1, `focus-visible` styles.

---

## 🧩 Required Dependencies

### Core

```
next
react
tailwindcss
@tailwindcss/forms
@tailwindcss/typography
tailwindcss-animate
class-variance-authority
tailwind-merge
lucide-react
```

### Optional (Recommended)

```
shadcn/ui
framer-motion
geist/font or @next/font/google
```

---

## ⚙️ Tailwind Configuration Baseline

```ts
// tailwind.config.ts
import { fontFamily } from "tailwindcss/defaultTheme";

export default {
  darkMode: ["class"],
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    container: {
      center: true,
      padding: "1rem",
      screens: { "2xl": "1280px" },
    },
    extend: {
      fontFamily: { sans: ["var(--font-inter)", ...fontFamily.sans] },
      borderRadius: {
        lg: "0.75rem",
        xl: "1rem",
        "2xl": "1.25rem",
      },
      boxShadow: {
        soft: "0 1px 2px rgba(0,0,0,0.04), 0 8px 24px rgba(0,0,0,0.06)",
      },
      transitionTimingFunction: {
        smooth: "cubic-bezier(.2,.6,.2,1)",
      },
      colors: {
        border: "hsl(210 14% 89%)",
        input: "hsl(210 16% 94%)",
        ring: "hsl(222 84% 60%)",
        background: "hsl(0 0% 100%)",
        foreground: "hsl(222 47% 11%)",
        muted: {
          DEFAULT: "hsl(210 16% 96%)",
          foreground: "hsl(215 16% 46%)",
        },
        card: {
          DEFAULT: "hsl(0 0% 100%)",
          foreground: "hsl(222 47% 11%)",
        },
      },
    },
  },
  plugins: [
    require("@tailwindcss/typography"),
    require("@tailwindcss/forms"),
    require("tailwindcss-animate"),
  ],
};
```

---

## 🧱 Base Styling Rules

**globals.css**

example:

```css
@import "tailwindcss";
@plugin "tailwindcss-animate";
@plugin "@tailwindcss/typography";
@plugin "@tailwindcss/forms";

/* Theme tokens */
:root {
  /* Brand */
  --brand-50:  #eef7ff;
  --brand-100: #dbeeff;
  --brand-200: #b7dcff;
  --brand-300: #8ec6ff;
  --brand-400: #5ea9ff;
  --brand-500: #2b8aff; /* primary */
  --brand-600: #1f6fe0;
  --brand-700: #1b59b3;
  --brand-800: #17488e;
  --brand-900: #123a72;

  /* Neutrals */
  --neutral-50:  #f8fafc;
  --neutral-100: #f1f5f9;
  --neutral-200: #e2e8f0;
  --neutral-300: #cbd5e1;
  --neutral-400: #94a3b8;
  --neutral-500: #64748b;
  --neutral-600: #475569;
  --neutral-700: #334155;
  --neutral-800: #1f2937;
  --neutral-900: #0f172a;

  /* Semantic */
  --success:  #16a34a;
  --warning:  #f59e0b;
  --danger:   #ef4444;
  --info:     #0ea5e9;

  /* Radius & shadow */
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --radius:  0.625rem;
  --background:  oklch(1 0 0);
  --foreground:  oklch(0.145 0 0);
  --card:  oklch(1 0 0);
  --card-foreground:  oklch(0.145 0 0);
  --popover:  oklch(1 0 0);
  --popover-foreground:  oklch(0.145 0 0);
  --primary:  oklch(0.205 0 0);
  --primary-foreground:  oklch(0.985 0 0);
  --secondary:  oklch(0.97 0 0);
  --secondary-foreground:  oklch(0.205 0 0);
  --muted:  oklch(0.97 0 0);
  --muted-foreground:  oklch(0.556 0 0);
  --accent:  oklch(0.97 0 0);
  --accent-foreground:  oklch(0.205 0 0);
  --destructive:  oklch(0.577 0.245 27.325);
  --border:  oklch(0.922 0 0);
  --input:  oklch(0.922 0 0);
  --ring:  oklch(0.708 0 0);
  --chart-1:  oklch(0.646 0.222 41.116);
  --chart-2:  oklch(0.6 0.118 184.704);
  --chart-3:  oklch(0.398 0.07 227.392);
  --chart-4:  oklch(0.828 0.189 84.429);
  --chart-5:  oklch(0.769 0.188 70.08);
  --sidebar:  oklch(0.985 0 0);
  --sidebar-foreground:  oklch(0.145 0 0);
  --sidebar-primary:  oklch(0.205 0 0);
  --sidebar-primary-foreground:  oklch(0.985 0 0);
  --sidebar-accent:  oklch(0.97 0 0);
  --sidebar-accent-foreground:  oklch(0.205 0 0);
  --sidebar-border:  oklch(0.922 0 0);
  --sidebar-ring:  oklch(0.708 0 0);
}

@theme inline {
  --color-background: var(--neutral-50);
  --color-foreground: var(--neutral-900);
  --color-muted: var(--neutral-600);
  --color-border: var(--neutral-200);
  --color-card: #ffffff;
  --color-ring: var(--brand-500);

  --color-primary-50: var(--brand-50);
  --color-primary-100: var(--brand-100);
  --color-primary-200: var(--brand-200);
  --color-primary-300: var(--brand-300);
  --color-primary-400: var(--brand-400);
  --color-primary-500: var(--brand-500);
  --color-primary-600: var(--brand-600);
  --color-primary-700: var(--brand-700);
  --color-primary-800: var(--brand-800);
  --color-primary-900: var(--brand-900);

  --font-sans: var(--font-sans);
  --font-heading: var(--font-heading);

  --radius: var(--radius-md);

  --color-sidebar-ring:  var(--sidebar-ring);

  --color-sidebar-border:  var(--sidebar-border);

  --color-sidebar-accent-foreground:  var(--sidebar-accent-foreground);

  --color-sidebar-accent:  var(--sidebar-accent);

  --color-sidebar-primary-foreground:  var(--sidebar-primary-foreground);

  --color-sidebar-primary:  var(--sidebar-primary);

  --color-sidebar-foreground:  var(--sidebar-foreground);

  --color-sidebar:  var(--sidebar);

  --color-chart-5:  var(--chart-5);

  --color-chart-4:  var(--chart-4);

  --color-chart-3:  var(--chart-3);

  --color-chart-2:  var(--chart-2);

  --color-chart-1:  var(--chart-1);

  --color-input:  var(--input);

  --color-destructive:  var(--destructive);

  --color-accent-foreground:  var(--accent-foreground);

  --color-accent:  var(--accent);

  --color-muted-foreground:  var(--muted-foreground);

  --color-secondary-foreground:  var(--secondary-foreground);

  --color-secondary:  var(--secondary);

  --color-primary-foreground:  var(--primary-foreground);

  --color-primary:  var(--primary);

  --color-popover-foreground:  var(--popover-foreground);

  --color-popover:  var(--popover);

  --color-card-foreground:  var(--card-foreground);

  --radius-sm:  calc(var(--radius) - 4px);

  --radius-md:  calc(var(--radius) - 2px);

  --radius-lg:  var(--radius);

  --radius-xl:  calc(var(--radius) + 4px);
}

:root.dark, .dark :root {
  --color-background: #0b1220;
  --color-foreground: #e5e7eb;
  --color-muted: #9ca3af;
  --color-border: #1f2937;
  --color-card: #0f172a;
}

/* Base */
html, body { height: 100%; }
body { font-family: var(--font-sans, ui-sans-serif), system-ui, -apple-system, Segoe UI, Roboto, "Helvetica Neue", Arial, "Noto Sans", "Apple Color Emoji", "Segoe UI Emoji"; }

/* Typography helpers */
.font-heading { font-family: var(--font-heading, ui-sans-serif), system-ui, -apple-system, Segoe UI, Roboto, "Helvetica Neue", Arial; }

/* Focus styles */
:focus-visible { outline: none; box-shadow: 0 0 0 2px white, 0 0 0 4px var(--brand-500); border-radius: 8px; }

/***** Utilities *****/
@layer utilities {
  .container-max { @apply container mx-auto max-w-screen-xl; }
  .layout-gutter { @apply px-6 md:px-8; }
}

/***** Component presets *****/
@layer components {
  .card { @apply bg-white border border-[--color-border]; }
  .btn-base { @apply inline-flex items-center justify-center text-sm font-medium transition-all duration-200 ease-[cubic-bezier(.2,.6,.2,1)] focus-visible:ring-2 focus-visible:ring-[--color-ring] disabled:opacity-50 disabled:cursor-not-allowed; }
  .input-base { @apply w-full border border-[--color-border] bg-white text-[--color-foreground] placeholder:text-[--color-muted] focus:outline-none focus:ring-2 focus:ring-[--color-ring]; }
}

.dark {
  --background:  oklch(0.145 0 0);
  --foreground:  oklch(0.985 0 0);
  --card:  oklch(0.205 0 0);
  --card-foreground:  oklch(0.985 0 0);
  --popover:  oklch(0.205 0 0);
  --popover-foreground:  oklch(0.985 0 0);
  --primary:  oklch(0.922 0 0);
  --primary-foreground:  oklch(0.205 0 0);
  --secondary:  oklch(0.269 0 0);
  --secondary-foreground:  oklch(0.985 0 0);
  --muted:  oklch(0.269 0 0);
  --muted-foreground:  oklch(0.708 0 0);
  --accent:  oklch(0.269 0 0);
  --accent-foreground:  oklch(0.985 0 0);
  --destructive:  oklch(0.704 0.191 22.216);
  --border:  oklch(1 0 0 / 10%);
  --input:  oklch(1 0 0 / 15%);
  --ring:  oklch(0.556 0 0);
  --chart-1:  oklch(0.488 0.243 264.376);
  --chart-2:  oklch(0.696 0.17 162.48);
  --chart-3:  oklch(0.769 0.188 70.08);
  --chart-4:  oklch(0.627 0.265 303.9);
  --chart-5:  oklch(0.645 0.246 16.439);
  --sidebar:  oklch(0.205 0 0);
  --sidebar-foreground:  oklch(0.985 0 0);
  --sidebar-primary:  oklch(0.488 0.243 264.376);
  --sidebar-primary-foreground:  oklch(0.985 0 0);
  --sidebar-accent:  oklch(0.269 0 0);
  --sidebar-accent-foreground:  oklch(0.985 0 0);
  --sidebar-border:  oklch(1 0 0 / 10%);
  --sidebar-ring:  oklch(0.556 0 0);
}

@layer base {
  * {
    @apply border-border outline-ring/50;
  }
  body {
    @apply bg-background text-foreground;
  }
}

```

---

## 🧰 Core Components

The agent must **always** build UIs with these reusable primitives.

### 🧭 Section

### 🪶 Button

### 🗂️ Card

---

## 🧾 Design Brief Schema

When no user design context is given, the agent must self-generate a **DesignBrief** JSON that defines global tone and design tokens:

```json
{
  "brand": { "name": "App", "tone": "friendly", "density": "roomy" },
  "layout": { "container": "max-w-screen-xl", "sectionY": { "sm": 12, "md": 16 } },
  "typography": { "font": "Inter", "scale": [36, 28, 22, 18, 16, 14] },
  "radius": "xl",
  "elevation": "soft",
  "palette": { "primary": "indigo", "surface": "white", "muted": "zinc" },
  "components": { "buttons": "shadcn", "cards": "shadcn", "forms": "tailwind-forms" }
}
```

---

## 🧩 Composition Rules

1. **Every page** must start with a `<Nav>`
2. **Content** must be wrapped in `<Section>` with `container max-w-screen-xl`.
3. **Use grid/flex layout** — avoid arbitrary margins.
4. **Spacing scale:** 2, 4, 6, 8, 12, 16, 24.
5. **Cards** for grouping content, **Buttons** for CTAs.
6. **No full-width text**; use readable line widths and `prose`.
7. **All interactive elements** require hover + focus-visible states.
8. **Responsive breakpoints:**

   * Mobile: 1 column
   * Tablet: 2 columns
   * Desktop: 3–4 columns max
9. **Vertical rhythm** — sections separated by consistent `py-12 md:py-16`.
10. **Dark mode support** — class-based, invert neutral palette.

---

## 🧮 Visual QA Rubric (1–5 Scale)

The agent must self-assess and **not output** until it scores ≥ 4 in all categories.

| Category                   | Description                                               |
| -------------------------- | --------------------------------------------------------- |
| **Spacing & Rhythm**       | Uses consistent 8pt grid, even gaps, and vertical flow    |
| **Hierarchy**              | Clear titles, subtext, and primary vs. secondary elements |
| **Alignment**              | Elements align on grid; consistent gutters                |
| **Consistency**            | Shared component patterns (radii, shadows, typography)    |
| **Contrast**               | Meets WCAG AA; adequate light/dark mode balance           |
| **Responsiveness**         | Layout adapts gracefully to all breakpoints               |
| **Interaction States**     | Hover, focus, disabled covered                            |
| **Empty / Loading States** | Provided for all async or data views                      |
| **Visual Balance**         | Proper breathing space; no edge-to-edge cramming          |

---

## 🚫 Design Don’ts

* ❌ Full-bleed text or inputs touching viewport edges
* ❌ Random color combinations not in palette
* ❌ Inline style overrides (except for dynamic props)
* ❌ More than two different border radii on one page
* ❌ Opaque hard shadows or over-saturated gradients
* ❌ Cramped or inconsistent padding

---

## ✅ Design Do’s

* ✅ Use predefined primitives (`Section`, `Card`, `Button`, `Nav`)
* ✅ Follow consistent `container max-w-screen-xl`
* ✅ Keep text hierarchy clear with `text-2xl md:text-3xl font-semibold`
* ✅ Animate with `framer-motion` for entry/fade-in transitions
* ✅ Add `EmptyState` and `LoadingState` components for robustness

---

## 🧠 Behavior Rules for the Agent

1. **Generate → Critique → Revise Loop**

   * Generate UI code
   * Critique per Visual QA rubric
   * Revise automatically until ≥4
2. **Prefer Composition over Nesting**

   * Build small composable blocks; avoid deep DOM nesting
3. **Use Semantic HTML** (`header`, `main`, `section`, `footer`)
4. **Always Provide Accessibility Attributes** (`aria-*`, `role`, `alt`)
5. **Avoid Vendor Lock-in** — use Tailwind primitives + optional `shadcn/ui`

---

## 🧰 Linting & CI Rules

* Use `eslint-plugin-tailwindcss`
* Fail build if:

  * No `container` in main layout
  * More than 2 distinct radii
  * Text smaller than `text-sm`
  * Hardcoded colors outside config palette





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

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

:root { --radius: 12px; }

body {
  @apply bg-[hsl(0_0%_99%)] text-foreground antialiased;
}

.prose { @apply max-w-none; }
```

---

## 🧰 Core Components

The agent must **always** build UIs with these reusable primitives.

### 🧭 Section

```tsx
export function Section({ children, className="" }) {
  return (
    <section className={`py-12 md:py-16 ${className}`}>
      <div className="container max-w-screen-xl">{children}</div>
    </section>
  );
}
```

### 🪶 Button

```tsx
import { cva, type VariantProps } from "class-variance-authority";
import { twMerge } from "tailwind-merge";

const button = cva(
  "inline-flex items-center justify-center rounded-xl text-sm font-medium transition-all duration-200 ease-smooth focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50 disabled:cursor-not-allowed",
  {
    variants: {
      variant: {
        primary: "bg-indigo-600 text-white hover:bg-indigo-700",
        secondary: "bg-white text-zinc-900 border border-border hover:bg-zinc-50",
        ghost: "hover:bg-zinc-100 text-zinc-700"
      },
      size: {
        sm: "h-9 px-3",
        md: "h-10 px-4",
        lg: "h-11 px-5"
      }
    },
    defaultVariants: { variant: "primary", size: "md" }
  }
);

export function Button({ className, variant, size, ...props }) {
  return <button className={twMerge(button({ variant, size }), className)} {...props} />;
}
```

### 🗂️ Card

```tsx
export function Card({ children, className="" }) {
  return <div className={`rounded-xl border border-border bg-card shadow-soft ${className}`}>{children}</div>;
}
export const CardHeader = ({ children }) => <div className="p-5 border-b">{children}</div>;
export const CardContent = ({ children }) => <div className="p-5 space-y-4">{children}</div>;
```

### 🏷️ PageHeader

```tsx
export function PageHeader({ title, subtitle, actions }) {
  return (
    <div className="mb-6">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-2xl md:text-3xl font-semibold tracking-tight">{title}</h1>
          {subtitle && <p className="text-zinc-600">{subtitle}</p>}
        </div>
        {actions}
      </div>
    </div>
  );
}
```

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

The agent must map this schema to Tailwind utilities (e.g. `text-2xl font-semibold`, `shadow-soft`, `rounded-xl`).

---

## 🧩 Composition Rules

1. **Every page** must start with a `<PageHeader>`
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

* ✅ Use predefined primitives (`Section`, `Card`, `Button`, `PageHeader`)
* ✅ Follow consistent `container max-w-screen-xl`
* ✅ Use `shadow-soft`, `rounded-xl`, `space-y-*`
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

  * Missing `PageHeader`
  * No `container` in main layout
  * More than 2 distinct radii
  * Text smaller than `text-sm`
  * Hardcoded colors outside config palette

---

## 💬 Example System Prompt Snippet

> Use the **UI Manifest** design standards.
>
> * Start every page with `<PageHeader>` and at least one `<Section>`.
> * Follow Tailwind 8pt spacing, Inter font, indigo primary.
> * Compose from primitives (Section, Card, Button).
> * Enforce Visual QA Rubric (≥4).
> * Generate code → self-review → fix → output final.
> * Avoid full-bleed layouts and inconsistent radii.
> * Add loading/empty/error states.


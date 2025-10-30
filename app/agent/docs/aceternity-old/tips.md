# Aceternity UI — Tips & Best Practices

- **Use the shadcn CLI** for every component install: `npx shadcn@latest add @aceternity/<package>` ensures dependencies, files, and CSS tokens are configured consistently.
- **Check extra CSS requirements.** Many background effects require keyframes or CSS variables in `app/globals.css` (e.g., Background Ripple Effect, Gradient Animation). Copy the provided snippets immediately after installation.
- **Keep utilities up to date.** Install `motion`, `clsx`, and `tailwind-merge`, and expose the `cn` helper so components can merge class names cleanly.
- **Leverage props.** Most components expose rich props for colour palettes, animation speed, interaction callbacks, etc. Consult the component page before overriding styles manually.
- **Combine components.** Layer background effects (Aurora, Dotted Glow, Sparkles) with hero layouts, text animations, CTA buttons, and scroll reveals to build immersive sections rapidly.
- **Mind performance.** When composing multiple animated layers, benchmark on low-power devices. Use Framer Motion’s `LazyMotion` or conditional rendering where appropriate.
- **Document usage.** Record installed Aceternity components in your architecture/plan so future agents do not reinstall or forget required CSS.


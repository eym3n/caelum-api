# Tailwind CSS v4 Compatibility Guide for AI Agents

This guide helps avoid common mistakes when generating projects with Tailwind CSS v4.

## Critical Issues to Avoid

### 1. **Opacity Modifiers with CSS Variables**
❌ **Don't use opacity modifiers with arbitrary CSS variable values in @apply**
```css
/* This will FAIL in Tailwind v4 */
.input-base { 
  @apply placeholder:text-[color:var(--color-foreground)]/60;
}
.btn-primary { 
  @apply hover:bg-[color:var(--color-brand)]/90;
}
```

✅ **Use color-mix() directly in CSS instead**
```css
.input-base { 
  @apply /* other classes */;
}
.input-base::placeholder {
  color: color-mix(in oklab, var(--color-foreground) 60%, transparent);
}

.btn-primary { 
  @apply /* other classes */;
}
.btn-primary:hover {
  background-color: color-mix(in oklab, var(--color-brand) 90%, transparent);
}
```

### 2. **@apply Inside @utility Directives**
❌ **Don't use @apply inside @utility**
```css
@utility btn { 
  @apply inline-flex items-center; /* FAILS */
}
```

✅ **Use actual CSS properties**
```css
@utility btn { 
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  font-weight: 500;
}
```

### 3. **Custom Classes with Opacity Modifiers**
When Tailwind v4 detects a class pattern with opacity modifiers (`/90`, `/60`, etc.) combined with arbitrary CSS variable values that doesn't exist, you must define it explicitly in `@layer utilities`. This commonly happens with:
- Hover states: `hover:bg-[color:var(--custom)]/90`
- Placeholder states: `placeholder:text-[color:var(--custom)]/60`
- Focus states: `focus:ring-[color:var(--custom)]/50`
- Any variant with opacity + CSS variable

```css
@layer utilities {
  /* Escape special characters: : becomes \:, [ becomes \[, etc. */
  .hover\:bg-\[color\:var\(--custom\)\]\/90:hover {
    background-color: color-mix(in oklab, var(--custom) 90%, transparent);
  }
  
  .placeholder\:text-\[color\:var\(--custom\)\]\/60::placeholder {
    color: color-mix(in oklab, var(--custom) 60%, transparent);
  }
}
```

### 4. **Responsive Variants in @utility**
❌ **Don't nest @utility inside @media**
```css
@media (min-width: 768px) {
  @utility section-y { /* FAILS */ }
}
```

✅ **Define base utility, then add responsive variants in @layer utilities**
```css
@utility section-y { 
  padding-top: 3rem;
  padding-bottom: 3rem;
}

@layer utilities {
  @media (min-width: 768px) {
    .section-y {
      padding-top: 5rem;
      padding-bottom: 5rem;
    }
  }
}
```

## Quick Reference: Converting Tailwind Classes to CSS

When you need to convert Tailwind classes to CSS for use in `@utility`:

| Tailwind Class | CSS Property |
|----------------|--------------|
| `relative` | `position: relative;` |
| `inline-flex` | `display: inline-flex;` |
| `items-center` | `align-items: center;` |
| `justify-center` | `justify-content: center;` |
| `gap-2` | `gap: 0.5rem;` |
| `font-medium` | `font-weight: 500;` |
| `rounded-full` | `border-radius: 9999px;` |
| `px-3 py-1` | `padding: 0.25rem 0.75rem;` |
| `text-xs` | `font-size: 0.75rem; line-height: 1rem;` |
| `py-12` | `padding-top: 3rem; padding-bottom: 3rem;` |
| `mx-auto` | `margin-left: auto; margin-right: auto;` |
| `max-w-7xl` | `max-width: 80rem;` |

## General Principles

1. **Opacity modifiers (`/90`, `/60`) don't work with arbitrary CSS variable values** - Use `color-mix()` directly in CSS instead
2. **@utility directives cannot contain @apply** - Always use actual CSS properties
3. **Missing class errors require explicit definitions** - Define custom classes in `@layer utilities` with proper escaping
4. **@utility cannot be nested in @media** - Define base utility, then add responsive variants separately
5. **Arbitrary values with CSS variables need special handling** - When combining variants, pseudo-classes, and opacity, define explicitly

## Common Error Patterns and Solutions

| Error Pattern | Root Cause | Solution |
|--------------|------------|----------|
| `The '[variant]:[property]-[color:var(--custom)]/[opacity]' class does not exist` | Opacity modifier with CSS variable not supported | Define explicitly in `@layer utilities` using `color-mix()` |
| `@apply is not supported within nested at-rules like @utility` | @apply cannot be used inside @utility | Replace `@apply` with actual CSS properties |
| `Syntax error: [class] does not exist` | Custom class pattern detected but not defined | Define the exact class name in `@layer utilities` with proper escaping |
| Errors about opacity modifiers in @apply | Opacity syntax incompatible with CSS variables | Move opacity handling to separate CSS rules using `color-mix()` |

## Key Takeaways

- **Tailwind v4 has stricter rules** - Many patterns that worked in v3 require explicit definitions
- **CSS variables + opacity = use color-mix()** - The `/90` syntax doesn't work with arbitrary CSS variable values
- **@utility requires raw CSS** - Cannot use @apply, must write actual CSS properties
- **When in doubt, define explicitly** - If Tailwind complains about a missing class, define it in `@layer utilities`
- **Escape special characters** - When defining custom classes, escape `:`, `[`, `]`, `/`, `(` with backslashes


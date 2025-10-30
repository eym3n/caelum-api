# Aceternity UI Component Catalogue

Install any component with:

```bash
npx shadcn@latest add @aceternity/<package>
```

Replace `<package>` with the desired entry below. Check each component’s documentation for props and extra CSS requirements.

## Backgrounds & Effects

| Component | Description | Package |
| --- | --- | --- |
| Dotted Glow Background | Pulsating dot grid with configurable gap, radius, and glow. | `@aceternity/dotted-glow-background` |
| Background Ripple Effect | Interactive ripple grid. Requires custom keyframes in `globals.css`. | `@aceternity/background-ripple-effect` |
| Sparkles | Animated sparkle overlay with configurable particle density, colour, and speed. | `@aceternity/sparkles` |
| Background Gradient | Animated gradient field for cards or sections. | `@aceternity/background-gradient` |
| Gradient Animation | Multi-direction gradient animation. Requires additional CSS variables/keyframes. | `@aceternity/background-gradient-animation` |
| Wavy Background | Animated wave lines ideal for hero bands. | `@aceternity/wavy-background` |
| Background Boxes | Subtle motion grid of boxes. | `@aceternity/background-boxes` |
| Background Beams | Animated beams sweeping across the background. | `@aceternity/background-beams` |
| Background Beams With Collision | Beam animation with collision interactions. | `@aceternity/background-beams-with-collision` |
| Background Lines | SVG line wave animation. | `@aceternity/background-lines` |
| Aurora Background | Aurora-style gradient glow. | `@aceternity/aurora-background` |
| Meteors | Shooting meteor background effect. | `@aceternity/meteors` |
| Glowing Stars | Star field with glowing points. | `@aceternity/glowing-stars` |
| Shooting Stars | Star field including animated shooting stars. | `@aceternity/shooting-stars` |
| Vortex | Swirling vortex background. | `@aceternity/vortex` |
| Spotlight / Spotlight New | Pointer-following spotlight effect. | `@aceternity/spotlight`, `@aceternity/spotlight-new` |
| Canvas Reveal Effect | Canvas-based reveal-on-scroll effect. | `@aceternity/canvas-reveal-effect` |
| SVG Mask Effect | Reveals content using an SVG mask. | `@aceternity/svg-mask-effect` |
| Tracing Beam | Animated beam tracing element edges. | `@aceternity/tracing-beam` |
| Lamp Effect | Spotlight lamp wash over elements. | `@aceternity/lamp-effect` |
| Grid and Dot Backgrounds | Collection of grid/dot patterns. | `@aceternity/grid-and-dot-backgrounds` |
| Glowing Effect | Soft glow halo for components. | `@aceternity/glowing-effect` |
| Google Gemini Effect | Gradient animation inspired by Google Gemini. | `@aceternity/google-gemini-effect` |

## Card Components

| Component | Description | Package |
| --- | --- | --- |
| Pixelated Canvas | Pixelates an image with mouse distortion. | `@aceternity/pixelated-canvas` |
| 3D Card Effect | Perspective hover elevation. | `@aceternity/3d-card-effect` |
| Evervault Card | Evervault-inspired card styling. | `@aceternity/evervault-card` |
| Card Stack | Fan-out/stack interactions on hover or click. | `@aceternity/card-stack` |
| Card Hover Effect | Animated hover states. | `@aceternity/card-hover-effect` |
| Wobble Card | Playful wobble animation. | `@aceternity/wobble-card` |
| Expandable Card | Expands to reveal hidden content. | `@aceternity/expandable-card` |
| Card Spotlight | Movable spotlight highlight. | `@aceternity/card-spotlight` |
| Focus Cards | Focused hover state with blur for siblings. | `@aceternity/focus-cards` |
| Infinite Moving Cards | Continuous marquee of cards. | `@aceternity/infinite-moving-cards` |
| Draggable Card | Tiltable, draggable card with bounds. | `@aceternity/draggable-card` |
| Comet Card | Perplexity-inspired 3D tilt card. | `@aceternity/comet-card` |
| Glare Card | Animated glare highlight on hover. | `@aceternity/glare-card` |
| Direction Aware Hover | Hover reaction based on cursor entry direction. | `@aceternity/direction-aware-hover` |

## Scroll & Parallax

| Component | Description | Package |
| --- | --- | --- |
| Parallax Scroll | Scroll-triggered parallax effect. | `@aceternity/parallax-scroll` |
| Sticky Scroll Reveal | Sticky sections that reveal content on scroll. | `@aceternity/sticky-scroll-reveal` |
| Macbook Scroll | Laptop reveal demo with scroll. | `@aceternity/macbook-scroll` |
| Container Scroll Animation | Scroll animation for containers. | `@aceternity/container-scroll-animation` |
| Hero Parallax | Hero-specific parallax effect set. | `@aceternity/hero-parallax` |

## Text Components

| Component | Description | Package |
| --- | --- | --- |
| Layout Text Flip | Animates words while flipping layout. | `@aceternity/layout-text-flip` |
| Colourful Text | Animated colour-filtered text. | `@aceternity/colourful-text` |
| Text Generate Effect | Character-by-character text reveal. | `@aceternity/text-generate-effect` |
| Typewriter Effect | Typing and deleting animation. | `@aceternity/typewriter-effect` |
| Flip Words | Rotates through multiple words. | `@aceternity/flip-words` |
| Text Hover Effect | Gradient outline animation on hover. | `@aceternity/text-hover-effect` |
| Container Text Flip | Resizing container text flipper. | `@aceternity/container-text-flip` |
| Hero Highlight | Animated highlight for hero headings. | `@aceternity/hero-highlight` |
| Text Reveal Card | Mask-based text reveal card. | `@aceternity/text-reveal-card` |

## Buttons

| Component | Description | Package |
| --- | --- | --- |
| Tailwind CSS Buttons | Collection of Tailwind button variants. | `@aceternity/tailwind-buttons` |
| Hover Border Gradient | Gradient border animation on hover. | `@aceternity/hover-border-gradient` |
| Moving Border | Animated border motion. | `@aceternity/moving-border` |
| Stateful Button | Loading + success state transitions. | `@aceternity/stateful-button` |

## Loaders

| Component | Description | Package |
| --- | --- | --- |
| Multi Step Loader | Multi-stage loader animation. | `@aceternity/multi-step-loader` |
| Loader | Simple spinner loader. | `@aceternity/loader` |

## Navigation

| Component | Description | Package |
| --- | --- | --- |
| Floating Navbar | Floating, scroll-responsive navbar. | `@aceternity/floating-navbar` |
| Navbar Menu | Navbar with interactive underline transitions. | `@aceternity/navbar-menu` |
| Sidebar | Animated sidebar navigation. | `@aceternity/sidebar` |
| Floating Dock | Mac-style navigation dock. | `@aceternity/floating-dock` |
| Tabs | Animated tab navigation. | `@aceternity/tabs` |
| Resizable Navbar | Width transitions on scroll. | `@aceternity/resizable-navbar` |
| Sticky Banner | Sticky promo banner. | `@aceternity/sticky-banner` |

## Inputs & Forms

| Component | Description | Package |
| --- | --- | --- |
| Signup Form | Animated sign-up form. | `@aceternity/signup-form` |
| Placeholders And Vanish Input | Input with vanishing placeholder. | `@aceternity/placeholders-and-vanish-input` |
| File Upload | Drag & drop uploader with micro interactions. | `@aceternity/file-upload` |

## Overlays & Popovers

| Component | Description | Package |
| --- | --- | --- |
| Animated Modal | Motion-powered modal transitions. | `@aceternity/animated-modal` |
| Animated Tooltip | Tooltip with motion entry/exit. | `@aceternity/animated-tooltip` |
| Link Preview | Hover to preview a link. | `@aceternity/link-preview` |

## Carousels & Sliders

| Component | Description | Package |
| --- | --- | --- |
| Images Slider | Basic image slider. | `@aceternity/images-slider` |
| Carousel | Customisable carousel with micro interactions. | `@aceternity/carousel` |
| Apple Cards Carousel | Apple-style product carousel. | `@aceternity/apple-cards-carousel` |
| Testimonials | Minimal testimonial slider. | `@aceternity/testimonials` |

## Layout & Grid

| Component | Description | Package |
| --- | --- | --- |
| Layout Grid | Responsive animated grid. | `@aceternity/layout-grid` |
| Bento Grid | Bento-box layout patterns. | `@aceternity/bento-grid` |
| Container Cover | Wraps children with beams/space effect. | `@aceternity/container-cover` |

## Data & Visualisation

| Component | Description | Package |
| --- | --- | --- |
| GitHub Globe | Interactive 3D globe for markers. | `@aceternity/github-globe` |
| World Map | Interactive data map. | `@aceternity/world-map` |
| Timeline | Timeline visualisation. | `@aceternity/timeline` |
| Compare | Before/after comparison slider. | `@aceternity/compare` |
| Codeblock | Syntax-highlighted code block. | `@aceternity/codeblock` |

## Cursor & Pointer

| Component | Description | Package |
| --- | --- | --- |
| Following Pointer | Element trails the pointer. | `@aceternity/following-pointer` |
| Pointer Highlight | Highlights content under the pointer. | `@aceternity/pointer-highlight` |
| Lens | Magnified lens around the cursor. | `@aceternity/lens` |

## 3D Components

| Component | Description | Package |
| --- | --- | --- |
| 3D Pin | Animated pin marker. | `@aceternity/3d-pin` |
| 3D Marquee | 3D marquee of text/elements. | `@aceternity/3d-marquee` |

## Sections & Blocks

| Component | Description | Package |
| --- | --- | --- |
| Feature Sections | Collection of feature section layouts. | `@aceternity/feature-sections` |
| Cards Sections | Card-driven landing page sections. | `@aceternity/cards-sections` |
| Hero Sections | Ready-made hero layouts. | `@aceternity/hero-sections` |



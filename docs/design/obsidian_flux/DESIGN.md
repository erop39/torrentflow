---
name: Obsidian Flux
colors:
  surface: '#10131b'
  surface-dim: '#10131b'
  surface-bright: '#363942'
  surface-container-lowest: '#0b0e16'
  surface-container-low: '#181c23'
  surface-container: '#1c2028'
  surface-container-high: '#272a32'
  surface-container-highest: '#31353d'
  on-surface: '#e0e2ed'
  on-surface-variant: '#c1c6d7'
  inverse-surface: '#e0e2ed'
  inverse-on-surface: '#2d3039'
  outline: '#8b90a0'
  outline-variant: '#414755'
  surface-tint: '#adc6ff'
  primary: '#adc6ff'
  on-primary: '#002e69'
  primary-container: '#4b8eff'
  on-primary-container: '#00285c'
  inverse-primary: '#005bc1'
  secondary: '#e6feff'
  on-secondary: '#003739'
  secondary-container: '#00f4fe'
  on-secondary-container: '#006c71'
  tertiary: '#ffb4a2'
  on-tertiary: '#621100'
  tertiary-container: '#ff562c'
  on-tertiary-container: '#560e00'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#d8e2ff'
  primary-fixed-dim: '#adc6ff'
  on-primary-fixed: '#001a41'
  on-primary-fixed-variant: '#004493'
  secondary-fixed: '#63f7ff'
  secondary-fixed-dim: '#00dce5'
  on-secondary-fixed: '#002021'
  on-secondary-fixed-variant: '#004f53'
  tertiary-fixed: '#ffdad2'
  tertiary-fixed-dim: '#ffb4a2'
  on-tertiary-fixed: '#3c0700'
  on-tertiary-fixed-variant: '#8a1d00'
  background: '#10131b'
  on-background: '#e0e2ed'
  surface-variant: '#31353d'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  title-md:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '500'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  label-sm:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.05em
  stats-number:
    fontFamily: Inter
    fontSize: 28px
    fontWeight: '700'
    lineHeight: 32px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 8px
  sidebar-width: 80px
  container-padding: 24px
  gutter-md: 16px
  margin-lg: 32px
---

## Brand & Style

The design system is engineered for power users who manage high-volume data streams. The brand personality is technical, high-performance, and immersive, evoking the feeling of a futuristic command center. 

The aesthetic leverages **Glassmorphism** and **Modern Dark** principles. It utilizes deep, multi-layered obsidian and navy backgrounds to create a sense of infinite depth. High-contrast neon accents provide immediate visual feedback on system status and data velocity. The interface is characterized by translucent surfaces, subtle back-glows, and precision-engineered typography that remains legible against dark, complex backdrops.

## Colors

The palette is anchored in **Deep Obsidian (#05070A)** for the primary background, with **Navy Surface (#0D1117)** used for elevated containers. 

- **Primary (Electric Blue):** Used for active states, primary actions, and branding.
- **Secondary (Cyan/Neon):** Used for progress indicators and data visualization.
- **Success (Emerald Green):** Indicates completed downloads or healthy RSS feeds.
- **Warning (Vibrant Orange):** Highlights bandwidth limits or pending actions.
- **Error (Radiant Red):** Indicates broken trackers or disk errors.

Transparency is a core pillar; background colors should be applied with 60-80% opacity when paired with a backdrop-filter (blur) to achieve the glass effect.

## Typography

The system utilizes **Inter** for all primary UI elements to ensure maximum legibility and a modern, neutral tone. For technical data, hash strings, and status labels, **JetBrains Mono** is used to reinforce the "developer/technical" utility of the tracker.

**Hierarchy Rules:**
- Large display titles use a tighter letter spacing to maintain a compact, high-end feel.
- Body text uses a standard weight (400) for readability against dark backgrounds.
- All technical labels are uppercase with increased tracking for rapid scanning.

## Layout & Spacing

The layout follows a **Fixed Sidebar / Fluid Content** model. 
- **Sidebar:** A narrow, high-blur glass rail on the left (80px) containing icon-only navigation.
- **Main Canvas:** A fluid area that uses a 12-column grid for desktop, collapsing to a single column for mobile.
- **Spacing Rhythm:** Based on an 8px linear scale. Containers should maintain a 24px internal padding to ensure the glass effects have "room to breathe."

On mobile devices, the sidebar transitions to a bottom navigation bar, and horizontal margins reduce from 32px to 16px.

## Elevation & Depth

This design system does not use traditional drop shadows. Instead, depth is communicated through **Translucency** and **Inner Glows**.

- **Layer 0 (Background):** Deepest navy, solid.
- **Layer 1 (Cards):** 70% opacity navy with a 20px backdrop-blur. 
- **Layer 2 (Modals/Popovers):** 85% opacity with a subtle 1px "white-to-transparent" top border to simulate light catching the edge of a glass pane.
- **Glows:** High-priority elements (like active progress bars) feature a subtle outer bloom (10-15px spread) using the primary color at 20% opacity.

## Shapes

The shape language is sophisticated and modern. All primary containers and cards use a **16px (rounded-lg)** corner radius to soften the technical aesthetic. Buttons and smaller input elements use an **8px (rounded-md)** radius. High-precision elements like progress bar fills and status pips use fully circular (pill) caps.

## Components

### Buttons
- **Primary:** Gradient fill (Electric Blue to Cyan), white text, subtle outer glow on hover.
- **Secondary:** Ghost style with a 1px semi-transparent border and high-blur background.

### Cards & Containers
- Cards feature a "Glass" effect: `backdrop-filter: blur(12px)`.
- Borders should be 1px wide, using a linear gradient (top-left to bottom-right) from `rgba(255,255,255,0.15)` to `rgba(255,255,255,0)`.

### Inputs
- Darkened fields (`#05070A` at 40% opacity) with a subtle inner shadow to create an "inset" look. Focus states trigger a 1px neon border glow.

### Progress Bars
- Background track is a semi-transparent neutral. The "Fill" is a vibrant neon gradient. Add a small glow effect at the leading edge of the progress indicator to simulate movement.

### Status Chips
- Small, uppercase labels with a low-opacity background tint matching the status color (e.g., Green for "Seeding", Orange for "Paused").
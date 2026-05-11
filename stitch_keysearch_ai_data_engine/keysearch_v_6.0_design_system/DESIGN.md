---
name: KeySearch V 6.0 Design System
colors:
  surface: '#f8f9ff'
  surface-dim: '#cbdbf5'
  surface-bright: '#f8f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#eff4ff'
  surface-container: '#e5eeff'
  surface-container-high: '#dce9ff'
  surface-container-highest: '#d3e4fe'
  on-surface: '#0b1c30'
  on-surface-variant: '#44474d'
  inverse-surface: '#213145'
  inverse-on-surface: '#eaf1ff'
  outline: '#75777e'
  outline-variant: '#c5c6cd'
  surface-tint: '#515f78'
  primary: '#000000'
  on-primary: '#ffffff'
  primary-container: '#0d1c32'
  on-primary-container: '#76849f'
  inverse-primary: '#b9c7e4'
  secondary: '#00677f'
  on-secondary: '#ffffff'
  secondary-container: '#00d2ff'
  on-secondary-container: '#00566a'
  tertiary: '#6c5e00'
  on-tertiary: '#ffffff'
  tertiary-container: '#bfab3d'
  on-tertiary-container: '#493f00'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#d6e3ff'
  primary-fixed-dim: '#b9c7e4'
  on-primary-fixed: '#0d1c32'
  on-primary-fixed-variant: '#39475f'
  secondary-fixed: '#b6ebff'
  secondary-fixed-dim: '#47d6ff'
  on-secondary-fixed: '#001f28'
  on-secondary-fixed-variant: '#004e60'
  tertiary-fixed: '#fae36f'
  tertiary-fixed-dim: '#dcc756'
  on-tertiary-fixed: '#211b00'
  on-tertiary-fixed-variant: '#524700'
  background: '#f8f9ff'
  on-background: '#0b1c30'
  surface-variant: '#d3e4fe'
typography:
  display:
    fontFamily: Inter
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  h1:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.01em
  h2:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  h3:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-md:
    fontFamily: JetBrains Mono
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
  label-sm:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
  h1-mobile:
    fontFamily: Inter
    fontSize: 28px
    fontWeight: '600'
    lineHeight: 36px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  2xl: 48px
  3xl: 64px
  container-max: 1440px
  gutter: 24px
---

## Brand & Style

This design system establishes a high-performance, developer-centric aesthetic for professional SEO data processing. The style is **Corporate Tech**, blending the accessibility of modern Python-based data tools (like Streamlit) with the robustness required for enterprise-grade analytics.

The brand personality is authoritative, precise, and efficient. It avoids excessive decoration in favor of structural clarity and functional accents. The visual narrative focuses on "The Pipeline"—visualizing the flow of data from raw input to actionable insight. 

Key visual principles include:
- **Clarity over Complexity:** High information density handled through generous whitespace and rigorous alignment.
- **Technical Vibrancy:** A deep, professional foundation punctuated by high-contrast "electric" accents to highlight data states and calls to action.
- **Precision Engineering:** Subtle use of depth and refined borders to suggest a sophisticated, modular architecture.

## Colors

The palette is anchored in **Deep Tech Blue**, providing a sophisticated, low-fatigue foundation for data-heavy workflows. 

- **Primary & Neutrals:** We utilize a "Slate" scale for secondary text and borders, ensuring a soft but professional contrast against the clean white background.
- **Accents:** **Electric Cyan** is the primary driver for interactivity and progress indicators, reflecting the "high-tech" nature of the tool. **Python Yellow** is used sparingly as a secondary accent for specific data highlights or branding moments to maintain the tool's heritage.
- **Semantic States:** Standardized success (emerald), warning (amber), and error (rose) colors are calibrated to sit harmoniously alongside the Electric Cyan accent without causing visual vibration.

## Typography

The design system utilizes **Inter** as the primary typeface for its exceptional legibility and neutral, modern character. It scales effortlessly from complex data tables to high-level dashboard headers.

To lean into the Python-based technical nature of the tool, **JetBrains Mono** is introduced for labels, status indicators, and data values. This creates a functional distinction between "narrative" text and "data" outputs.

**Hierarchy Rules:**
- Use **Display** and **H1** for page titles and major section headings.
- **Body-md** is the default for all paragraph text and form inputs.
- **Label-sm** (Mono) should be used for metadata, table headers, and technical timestamps.

## Layout & Spacing

This design system employs a **Fluid Grid** logic within a max-width container to ensure readability on ultra-wide monitors common in data analysis environments.

- **Grid System:** A 12-column grid with a 24px gutter. On mobile, this reflows to a 4-column grid with 16px margins.
- **Rhythm:** An 8px linear scale (with 4px increments for tight components) drives all padding and margin decisions. 
- **Data Density:** Dashboard layouts should utilize `spacing-md` (16px) for internal card padding to maintain a "Streamlit-like" compactness while ensuring professional breathing room.
- **Sidebars:** Navigation is handled via a fixed left-hand rail (240px) which can collapse to an icon-only view (64px) to maximize data workspace.

## Elevation & Depth

To maintain a "High-Tech" feel, depth is communicated through **Tonal Layering** supplemented by **Ambient Shadows**. 

- **Level 0 (Background):** The base layer is `#F8FAFC`, providing a neutral canvas.
- **Level 1 (Cards/Surface):** Primary content containers are pure white (`#FFFFFF`) with a 1px border in `#E2E8F0`. 
- **Level 2 (Interactive/Floating):** Elements like dropdowns, tooltips, or active modals use a soft, diffused shadow: `0 4px 12px rgba(10, 25, 47, 0.08)`.
- **Level 3 (Modals):** Large overlays use a higher elevation shadow with a 15% opacity Deep Tech Blue tint to ground the element in the brand's primary color.

**Transitions:** Hover states on interactive elements should involve a subtle "lift" (moving from Level 1 to a slight shadow) rather than dramatic color shifts.

## Shapes

The shape language is consistently **Rounded**, striking a balance between the clinical sharp edges of traditional enterprise software and the overly bubbly nature of consumer apps.

- **Standard (0.5rem):** Applied to buttons, input fields, and small cards.
- **Large (1rem):** Used for main content containers and dashboard widgets.
- **Pill (Full):** Reserved exclusively for status tags (e.g., "Running," "Completed") and search bars to make them instantly recognizable as distinct functional units.

## Components

### Buttons & Inputs
- **Primary Button:** Deep Tech Blue background with white text. High-contrast Electric Cyan focus ring.
- **Secondary Button:** Ghost style with a 1px border in Deep Tech Blue and a subtle gray hover state.
- **Inputs:** Clean white backgrounds with 1px slate borders. Focus state uses a 2px Electric Cyan glow. Labels are positioned above the field in **Inter Semi-Bold**.

### Data Tables
- **Header:** Light gray background (`#F1F5F9`) with **JetBrains Mono** uppercase labels.
- **Rows:** Subtle zebra striping. On-hover highlight using a 2% opacity Electric Cyan tint.
- **Cell Content:** Numerical data should be right-aligned and set in monospaced font for vertical scanning.

### Pipeline Status Indicators
- A custom horizontal stepper component.
- **Pending:** Dotted slate border.
- **Active:** Solid Electric Cyan border with a subtle "pulse" animation.
- **Completed:** Solid Emerald background with a white checkmark.

### Cards
- White surfaces with `rounded-lg` corners. 
- Headers should include a 1px bottom border to separate titles from the body content.
- Use Python Yellow sparingly in cards to highlight "Key Insights" or "Recommendations."
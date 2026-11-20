# Design direction: Reading Helper

Status: v2 redesign, 2026-11-20. Written for the team (Viktoriia, Aidan, MDE reviewers). Scope: `web/` only.

## 1. The problem
The first version works and passes WCAG checks, but it is plain: white cards on pale grey, one weight of border,
one flat navy button, no personality. Teachers are adult professionals who open this between lessons. It should feel
**calm, warm and competent**: not childish (no confetti, no cartoon primary colors), not corporate-cold (no grey
dashboards), and not bare.

## 2. Research
I searched for current (2025-2026) references across four groups. **Confidence matters here:** several searches
returned thin or secondary sources, so each item says what I could verify and what is my own judgment.

| # | Reference | What it does well (and what we take) | Confidence |
|---|---|---|---|
| 1 | [GOV.UK Design System](https://design-system.service.gov.uk/) and its 2025 brand refresh ([what's new](https://design-system.service.gov.uk/community/whats-new), [updated type scale](https://design-system.service.gov.uk/get-started/new-type-scale)) | Plain language, one question per page, strong focus states, a type scale revised for accessibility (v6). The 2025 refresh updated header, footer and service navigation. **Take:** a clear service-navigation bar, one main action per screen, generous line height, form patterns (labels above fields, errors summarized). | Verified that the refresh and type-scale update exist; specific values not checked |
| 2 | [U.S. Web Design System (USWDS)](https://designsystem.digital.gov/) | Published accessibility conformance report (44 components assessed against VPAT 2.5, 2025) and per-component accessibility tests; monthly releases. **Take:** treat accessibility as a per-component test, which is what our Playwright + axe suite does per screen. | Verified |
| 3 | [NHS service manual design system](https://service-manual.nhs.uk/design-system) | Calm, trustworthy public-service look: restrained blue, white space, clear headings, no decoration for its own sake. **Take:** tone. | Verified it exists (v10); visual details from memory |
| 4 | [Singapore Government Design System](https://designsystem.tech.gov.sg/) | Shared tokens for color, type and components, with room for a product to keep its own identity. **Take:** the token approach we already use, extended. | Verified |
| 5 | Khan Academy's reimagined classroom experience ([blog](https://blog.khanacademy.org/?p=21322), [teacher changes](https://support.khanacademy.org/hc/en-us/articles/46056253778061-What-s-changing-for-teachers-in-the-reimagined-Khan-Academy-experience)) | A teacher dashboard organized around the tasks teachers do most, with simpler navigation and saved materials. **Take:** home screen = tasks, not features. (We already do this.) | Verified description; I did not see the UI itself |
| 6 | Linear's UI redesign ([how we redesigned the Linear UI](https://linear.app/now/how-we-redesigned-the-linear-ui)) | Rebuilt foundations for hierarchy, balance and density; a display face for headings and a text face for body; separation by subtle borders. **Take:** hierarchy through type weight and spacing rather than boxes everywhere; a display/text pairing (we already have Lexend + Atkinson). It is a dense dev tool, so we do **not** take its density. | Verified (2024 post, still referenced in 2026) |
| 7 | Material 3 Expressive research ([Google Design](https://design.google/library/expressive-material-design-google-research)) | Google reports 46 studies with 18,000+ participants: well-applied expressive design (color, shape, size, motion, containment) helped people spot the key action faster. **Take:** use size and color to make the one primary action obvious; keep it moderate (we are not going maximalist). | Verified as Google's own claim; not independently verified |
| 8 | Notion Calendar's 2025 UI update ([AlternativeTo report](https://alternativeto.net/news/2025/7/notion-calendar-gets-ui-upgrade-with-better-colors-and-icons)) and community analyses of its style | Warm neutrals instead of cold greys, near-invisible grid lines, soft tinted fills instead of heavy borders. **Take:** a warm cream tint on large surfaces; tinted fills for status. | Update verified; the palette details are reverse-engineered by third parties, so treat as approximate |
| 9 | Duolingo ([illustration guide](https://design.duolingo.com/illustration)) and Headspace brand work | Rounded, simple shapes with a consistent rhythm; a mascot that is rarely static; illustration owned by one in-house style. **Take:** simple geometric rules and subtle life in the mascot. **Do not take:** the playfulness and saturation. Our audience is adult professionals. | Verified for Duolingo; Headspace is third-party commentary |
| 10 | Awwwards 2025 winners with warm palettes (e.g. a Sept 2025 Site of the Day using burnt orange) | Only a weak signal: warm hues and tasteful motion are current. The search returned listing pages, not write-ups. **Take:** nothing specific; this reference is listed for completeness, not relied on. | Low |

Also checked: guidance on layered shadows. Sources disagree (Stripe-style layered shadows versus Linear-style
near-flat borders). The consistent advice is to **pick one depth strategy and apply it everywhere**. We choose
borders plus a very light two-layer shadow for cards, and stronger shadows only for floating layers (the Sources
panel, menus).

I looked for the `frontend-design` skill; it is not installed in this environment. I applied the
`design:accessibility-review` checklist instead (see `docs/ACCESSIBILITY_REVIEW.md`).

## 3. Direction: "Quiet study"
A warm reading room, not a dashboard. Navy stays the anchor; warmth comes from cream surfaces and one golden accent;
depth comes from layered cards; life comes from restrained motion and one small mascot.

### Color (tokens extend `web/src/styles/tokens.css`; existing tokens unchanged)
| Token | Value | Use |
|---|---|---|
| `--color-primary` | `#1F4E8C` | Anchor: primary buttons, links, key borders (unchanged) |
| `--color-ink` / `--color-muted` | `#15233A` / `#4A5872` | Text (unchanged) |
| `--color-bg` | `#F4F6FA` | Page background (unchanged) |
| `--color-warm` | `#FBF5E8` | Hero and "Idea for your class" surfaces (new) |
| `--color-warm-2` | `#F5E7C8` | Warm borders and dividers (new) |
| `--color-tint` | `#EAF0F9` | "Research says" surface, quiet panels (new) |
| `--color-tint-2` | `#D3E0F2` | Tint borders (new) |
| `--color-highlight` | `#F5C842` | The one warm accent: highlights, mascot beak, underline accents (unchanged) |
Rules: warm accent is decoration and emphasis only, never the only signal; text on tinted surfaces stays at or above
7:1 where possible (ink on `--color-warm` is about 14:1).

### Type
Lexend for headings, Atkinson Hyperlegible for body (unchanged). Fluid heading scale:
h1 `clamp(1.9rem, 1.4rem + 2vw, 2.75rem)` weight 600, tight leading (1.15) and a slight negative tracking;
h2 1.5rem; eyebrow labels 0.8rem uppercase with 0.08em tracking in muted ink; body 17px / 1.55. The user's
"Text size" setting still scales everything through the root font size.

### Space, shape and depth
8px grid; section rhythm 32px (mobile) / 48px (desktop). Radius 16px for cards, 12px for controls. Cards: 1px border +
`0 1px 2px` and `0 4px 12px` faint navy-tinted shadows (two layers). Interactive cards lift 2px on hover. Floating
layers (Sources panel) get a deeper third shadow. High-contrast mode drops shadows and uses solid black borders.

### Layout
Home gets a greeting hero (cream surface, mascot, one sentence, the ask box as the main action) above the two task
cards. Answers keep the evidence label first; "Research says" sits on the cool tint, "Idea for your class" on the
warm cream, so the two are distinguishable by surface and by label, never by color alone.

### Motion (all of it is decoration; nothing relies on it)
Tokens: ease `cubic-bezier(0.2, 0.7, 0.2, 1)`, durations 120ms (feedback), 200ms (hover), 320ms (entrances/panels).
- Page and card entrance: fade + 8px rise, children staggered 40ms.
- Hover/press: 2px lift on interactive cards; buttons darken and press to 98%.
- Sources panel slides in from the right (320ms) over a fading overlay.
- Mascot: blink every ~5s and a slow 4s bob; "thinking" tilts the head and pulses three dots.
- Loading: calm pulsing dots plus the thinking mascot, with the same text for screen readers.
- Everything is switched off by the OS `prefers-reduced-motion` setting **and** the in-app "Less moving and animation"
  switch (one global rule on `html[data-motion="reduce"]`).

### Where the mascot appears
Home greeting, loading, no-research and other empty states, sign-in, and first-time onboarding. **Never** in an
answer, a citation, a source list or the evidence label. Decorative SVGs are `aria-hidden`.

## 4. Mascot
MASCOT_SECTION_PLACEHOLDER

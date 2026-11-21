# Accessibility review: teacher web app (WCAG 2.1 AA)

Date: 2026-11-20. Scope: Home, Answer (+ Sources panel), Group plan, Make a story, Settings, Class board,
plus shared components and the shell. Method: `design:accessibility-review` checklist, applied with measurements
(contrast math, Playwright + axe on every screen at 1280px and 375px, 320px reflow at extra-large text, keyboard
checks in tests). **Not done: a real screen-reader pass (VoiceOver/NVDA). Please do one before the pilot.**

## Fixed during the review
| # | Finding | WCAG | Fix |
|---|---|---|---|
| 1 | Horizontal scroll at 320px with extra-large text on Home (44px) and Settings (24px) | 1.4.10 | Grid items now `min-width: 0`; reflow test for 10 screens |
| 2 | Settings switches were 26px high | 2.5.5 | The real checkbox now covers the whole 48px row |
| 3 | Citation/"Show exact passage" labels did not contain their visible text | 2.5.3 | Names start with the visible text |
| 4 | Focus was not returned to the citation after closing the Sources panel | 2.4.3 | Opener is remembered and refocused |
| 5 | Focus jumped to the heading on first load | 2.4.3 | Only moves on a real page change |
| 6 | axe sampled mid-transition colors on buttons | 1.4.3 | Removed color transitions |

## Passing, measured
Text: ink on bg 14.6:1, muted on white 7.2:1, white on primary 8.3:1, notice text 10.3:1.
Non-text (1.4.11): control borders 4.8:1, "Idea" card border 5.1:1. Decorative card borders (1.2:1) carry no meaning.
Status is never color alone: evidence label = words + 3 bars + sr text; story marks = underline style + sr text;
toggles = check mark + On/Off words. Skip link, landmarks, one h1 per screen, focus ring 3px, focus moves to h1
on navigation, dialog traps focus and closes with Escape, reduced motion honored (OS and in-app).

## Open items (not blockers)
| # | Item | Severity | Note |
|---|---|---|---|
| A | Whole answer sits in one `aria-live="polite"` region, so a screen reader may read it all at once | Minor | Test with a real reader; if noisy, announce only a short "Answer ready" status |
| B | Read aloud uses the browser voice; quality and availability vary | Minor | Hidden when unsupported |
| C | Spanish selectable but content is English | Minor | Says so on screen |
| D | Class board has no keyboard shortcuts (arrows) | Minor | Buttons are 64px and operable |
| E | High-contrast mode verified by axe on Home only | Minor | Extend the check to every screen |
| F | No automated check of 200% browser zoom besides the 320px reflow test | Minor | Equivalent per 1.4.10 |

## v2 redesign addendum (2026-11-20)
Re-checked after the redesign, sign-in and motion work. Playwright + axe: 0 serious/critical on all 14 screens and the
6 public screens at 1280px and 375px (136 tests); 320px reflow at extra-large text on 10 screens.
New surfaces, measured: ink on cream 14.5:1, muted on cream 6.6:1, muted on tint 6.3:1, links on tint 7.3:1,
notice text on cream 10.5:1; non-text: "Idea" border on cream 4.7:1, primary border on tint 7.3:1 (needs 3:1).
Forms follow the GOV.UK pattern: labels above fields, hints and errors tied with `aria-describedby`, an error summary
that takes focus and links to each field, `autocomplete` tokens (username, current-password, new-password, one-time-code),
one sign-in failure message that does not say which part was wrong, a show/hide password button with `aria-pressed`.
Admin tabs use the ARIA tab pattern with arrow keys. Motion: entrances, hover lift, panel slide and mascot animation
all stop under `prefers-reduced-motion` and the in-app switch (tested); none of it carries meaning.
Note: tests run with reduced motion on (axe otherwise samples colors mid-fade); a dedicated test turns motion on and
checks the animation exists. **Still not done: a real screen-reader pass.** Also check by eye: the sticky header at
200% zoom does not cover focused fields (it is ~64px tall; `scroll-padding-top` is not set yet).

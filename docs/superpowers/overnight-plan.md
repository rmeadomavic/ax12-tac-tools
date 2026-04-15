# Overnight Improvement Plan — 2026-04-15

Kyle is gone for 12 hours. Here's what I'm doing:

## 1. Code Review
- web_launcher.py is 800+ lines, single file — review for bugs, edge cases, cleanup
- install.sh — review for robustness
- tools.json — verify all commands and requirements are correct

## 2. Visual Overhaul (Anduril/Palantir Polish)
- Current UI is functional but basic green-on-black terminal look
- Need: smooth transitions, better typography, proper spacing, subtle glow effects
- Think Palantir Gotham / Anduril Lattice — dark, clean, confident, futuristic
- Output view needs polish — scrolling, status indicators
- Settings page needs cleanup
- Setup wizard should feel premium

## 3. Ranger Voice Pass
- All docs sound AI-generated — README, GETTING_STARTED, tak-setup
- Need Kyle's voice: direct, no fluff, operator-to-operator
- Remove marketing language, remove "capabilities:" lists, remove bold-everything pattern
- Keep it short and useful

## 4. Edge Cases & Robustness
- Tools that hang with no output need a timeout message
- Server restart/zombie process handling
- Better error messages for pre-flight failures
- Settings page UX improvements

## 5. Brainstorm Doc
- Ideas for future features (not implementing, just documenting)
- What would make this truly mission-ready for SORCC operators
- Hydra/Argus integration ideas (available but not foregrounded)

## Execution Order
1. Code review (agent)
2. Brainstorm future ideas (write doc)
3. Visual overhaul (biggest impact)
4. Voice pass on docs
5. Push everything, verify on AX12

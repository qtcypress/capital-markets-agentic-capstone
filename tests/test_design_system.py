"""The stylesheet, checked the way any other contract is checked.

A design system that is only enforced by taste drifts back to hard-coded hex
within a month, and a contrast failure is invisible to the person who
introduced it — they can read it fine on their own screen. So the two rules
that actually matter are asserted here:

* every foreground/background pair the console puts on screen clears WCAG AA;
* colour comes from tokens, not from hex typed into a rule.

These run in milliseconds and need no browser. `tests/test_ui.py` covers what
the tokens look like once a browser has applied them.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

CSS = Path(__file__).resolve().parent.parent / "app" / "web" / "styles.css"
SOURCE = CSS.read_text(encoding="utf-8")

AA_NORMAL = 4.5
AA_LARGE = 3.0


# ---------------------------------------------------------------------------
# Contrast
# ---------------------------------------------------------------------------
def _luminance(hex_colour: str) -> float:
    parts = [int(hex_colour[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in parts]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(foreground: str, background: str) -> float:
    high, low = sorted((_luminance(foreground), _luminance(background)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def _strip_comments(css: str) -> str:
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def _tokens(block: str) -> dict[str, str]:
    """Pull `--name: #RRGGBB` pairs out of one :root block, following aliases.

    `--accent-soft: var(--accent-50)` is a token like any other; resolving it
    here is what lets the contrast table name the token a rule actually uses
    rather than the one it happens to point at this week.
    """
    direct = {name: value.upper()
              for name, value in re.findall(r"--([\w-]+):\s*(#[0-9A-Fa-f]{6})\s*;", block)}
    for name, target in re.findall(r"--([\w-]+):\s*var\(--([\w-]+)\)\s*;", block):
        if target in direct:
            direct[name] = direct[target]
    return direct


def _block(theme: str) -> dict[str, str]:
    if theme == "light":
        body = SOURCE.split("@media (prefers-color-scheme: dark)")[0]
    else:
        body = SOURCE.split("@media (prefers-color-scheme: dark)")[1].split("/* ---")[0]
    return _tokens(body)


LIGHT = _block("light")
DARK = _block("dark")

# (foreground token, background token, minimum) — every pair the console renders.
PAIRS = [
    ("text", "surface", AA_NORMAL),
    ("text", "bg", AA_NORMAL),
    ("text-2", "surface", AA_NORMAL),
    ("muted", "surface", AA_NORMAL),
    ("muted", "surface-2", AA_NORMAL),
    ("muted-2", "surface", AA_LARGE),      # placeholders and empty-state hints only
    ("accent", "surface", AA_NORMAL),      # links, case ids, active tab
    ("accent", "accent-soft", AA_NORMAL),  # chips and selected pills
    ("ok", "ok-soft", AA_NORMAL),
    ("warn", "warn-soft", AA_NORMAL),
    ("danger", "danger-soft", AA_NORMAL),
    ("info", "info-soft", AA_NORMAL),
    ("neutral", "surface", AA_LARGE),
]


@pytest.mark.parametrize("theme,tokens", [("light", LIGHT), ("dark", DARK)])
@pytest.mark.parametrize("foreground,background,minimum", PAIRS)
def test_every_pair_on_screen_clears_wcag_aa(theme, tokens, foreground, background, minimum):
    fg, bg = tokens.get(foreground), tokens.get(background)
    assert fg and bg, f"{theme}: missing token {foreground!r} or {background!r}"
    got = contrast(fg, bg)
    assert got >= minimum, (
        f"{theme}: --{foreground} ({fg}) on --{background} ({bg}) is {got:.2f}:1, "
        f"needs {minimum}:1")


def test_the_primary_button_fill_clears_aa_against_its_own_label():
    """Why the button is #D6320A and not the brand #EC3705.

    The brand orange reaches only 4.11:1 against white — close enough to look
    fine to whoever picks it, and short of AA for the person who has to read it.
    A half-step darker clears it while still reading as the same colour."""
    fill = re.search(r"button\.primary,\s*button\.danger\s*\{[^}]*background:\s*(#[0-9A-Fa-f]{6})",
                     SOURCE, re.S)
    assert fill, "the primary button no longer has a solid fill — check this rule still holds"
    assert contrast(fill.group(1).upper(), "#FFFFFF") >= AA_NORMAL


def test_the_brand_gradient_never_sits_behind_text():
    """Its amber end is 2.33:1 on white. It belongs on rails, not on fills.

    Every `background: var(--brand-grad)` must therefore be a pseudo-element
    rail or a soft tint — never the background of an element with a label."""
    assert contrast("#FE8D08", "#FFFFFF") < AA_NORMAL, "amber got lighter; revisit this rule"
    for rule in re.findall(r"([^{}]+)\{[^}]*background:\s*var\(--brand-grad\)[^}]*\}", SOURCE):
        selector = rule.strip().splitlines()[-1].strip()
        assert "::before" in selector or "::after" in selector, (
            f"{selector!r} fills an element with the brand gradient; text on its amber end "
            f"would be unreadable. Use a ::before rail or a solid fill.")


# ---------------------------------------------------------------------------
# Token discipline
# ---------------------------------------------------------------------------
def test_colour_comes_from_tokens_not_from_hex_typed_into_rules():
    """Three exceptions, each with a reason written beside it in the stylesheet:
    the primary button's AA-corrected fill and its hover, and the code block,
    which is a fixed dark chrome in both themes."""
    marker = "3. base */"
    body = _strip_comments(SOURCE.split(marker, 1)[1])
    stray = {h.upper() for h in re.findall(r"#[0-9A-Fa-f]{6}", body)}
    allowed = {"#D6320A", "#BF2C08", "#0B0C28", "#DFE1F4", "#22245C", "#FFFFFF"}
    assert not (stray - allowed), (
        f"hard-coded colours outside the token block: {sorted(stray - allowed)}. "
        f"Add a token instead — that is what makes the dark theme free.")


def test_both_themes_define_the_same_tokens():
    """A token defined only in light mode silently inherits the light value on a
    dark background, which is exactly the bug nobody notices in review."""
    semantic = {k for k in LIGHT if k.split("-")[0] in
                {"ok", "warn", "danger", "info", "accent", "text", "muted", "surface", "border", "bg", "neutral"}}
    missing = sorted(semantic - set(DARK))
    assert not missing, f"tokens with no dark-theme value: {missing}"


def test_the_palette_is_quality_thoughts():
    """The three values sampled from the logo, and no leftovers from the last one."""
    for value in ("#EC3705", "#FE8D08", "#090A4E"):
        assert value in SOURCE, f"{value} is not in the palette"
    for stale in ("#12B5A5", "#4F46E5", "#7C3AED"):
        assert stale not in SOURCE.upper(), f"{stale} is left over from the previous palette"

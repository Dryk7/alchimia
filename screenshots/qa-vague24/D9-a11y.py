"""
D9 — Audit A11y read-only (vague 24)
Mesure: lang, ARIA, contrast, reduced-motion, tap size, colorblind, large text.
Note attendue: 8.7/10.
"""
import asyncio
import json
from playwright.async_api import async_playwright

URL = "http://localhost:8770/"
OUT = "D:/alchimia/screenshots/qa-vague24/"


async def main():
    findings = {}
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            viewport={"width": 540, "height": 960},
            device_scale_factor=2,
            has_touch=True,
            is_mobile=True,
            locale="fr-FR",
        )
        page = await ctx.new_page()

        # ---- Skip onboarding via localStorage seed (read-only sur DOM, juste prep state)
        await page.goto(URL, wait_until="domcontentloaded")
        await page.evaluate("""() => {
            try {
                localStorage.setItem('foulee_onboarding_done','1');
                localStorage.setItem('foulee_tutorial_done','1');
                localStorage.setItem('foulee_tos_accepted','1');
            } catch(e){}
        }""")
        await page.goto(URL, wait_until="networkidle")
        await page.wait_for_timeout(1500)

        # 1) HTML lang
        lang = await page.evaluate("document.documentElement.lang || ''")
        findings["html_lang"] = lang

        # 2) ARIA coverage on buttons (incl. role=button)
        aria_buttons = await page.evaluate("""() => {
            const sel = 'button, [role="button"], [onclick], a';
            const all = Array.from(document.querySelectorAll(sel))
              .filter(el => el.offsetParent !== null);
            const labelled = all.filter(el => {
                const al = el.getAttribute('aria-label');
                const txt = (el.innerText || el.textContent || '').trim();
                const t = el.getAttribute('title');
                const aldby = el.getAttribute('aria-labelledby');
                return (al && al.trim()) || txt.length > 0 || (t && t.trim()) || aldby;
            });
            const unlabelled = all.filter(el => !labelled.includes(el))
              .map(el => ({tag: el.tagName, cls: el.className, id: el.id}));
            return {total: all.length, labelled: labelled.length, unlabelled: unlabelled.length, samples: unlabelled.slice(0,8)};
        }""")
        findings["aria_buttons"] = aria_buttons

        # 3) aria-live regions
        live = await page.evaluate("""() => {
            const live = document.querySelectorAll('[aria-live], [role="status"], [role="alert"], [role="log"]');
            return {count: live.length, kinds: Array.from(live).map(l => l.getAttribute('aria-live') || l.getAttribute('role'))};
        }""")
        findings["aria_live"] = live

        # 4) Focus management & focus visible
        focus = await page.evaluate("""() => {
            const css = Array.from(document.styleSheets).flatMap(s => {
                try { return Array.from(s.cssRules||[]).map(r => r.cssText); } catch(e) { return []; }
            }).join('\\n');
            return {
                focus_visible_rules: (css.match(/:focus-visible/g)||[]).length,
                focus_rules: (css.match(/:focus[^-]/g)||[]).length,
                outline_none: (css.match(/outline:\\s*none|outline:\\s*0/g)||[]).length
            };
        }""")
        findings["focus_css"] = focus

        # 5) Contrast ratios sur surfaces principales
        contrast = await page.evaluate("""() => {
            function lum(rgb) {
                const a = rgb.map(v => {
                    v /= 255;
                    return v <= 0.03928 ? v/12.92 : Math.pow((v+0.055)/1.055, 2.4);
                });
                return 0.2126*a[0]+0.7152*a[1]+0.0722*a[2];
            }
            function parseRgb(s) {
                const m = s.match(/rgba?\\((\\d+),\\s*(\\d+),\\s*(\\d+)/);
                return m ? [+m[1],+m[2],+m[3]] : null;
            }
            function ratio(c1, c2) {
                const L1 = lum(c1), L2 = lum(c2);
                const a = Math.max(L1,L2)+0.05, b = Math.min(L1,L2)+0.05;
                return a/b;
            }
            const samples = [];
            const sel = 'button, .btn, .hud, .stat, h1, h2, h3, p, .label, .toast, .modal, .card, span, div';
            const els = Array.from(document.querySelectorAll(sel))
              .filter(el => el.offsetParent !== null && (el.innerText||'').trim().length > 1)
              .slice(0, 60);
            for (const el of els) {
                const cs = getComputedStyle(el);
                const fg = parseRgb(cs.color);
                let bg = parseRgb(cs.backgroundColor);
                let bgEl = el;
                while (bg && bg.length === 4 && bg[3] === 0 && bgEl.parentElement) {
                    bgEl = bgEl.parentElement;
                    bg = parseRgb(getComputedStyle(bgEl).backgroundColor);
                }
                if (!fg || !bg) continue;
                const r = ratio(fg, bg);
                const fs = parseFloat(cs.fontSize);
                const bold = (parseInt(cs.fontWeight)||400) >= 600;
                const large = fs >= 24 || (fs >= 18.66 && bold);
                samples.push({
                    txt: (el.innerText||'').trim().slice(0,30),
                    ratio: +r.toFixed(2),
                    fontSize: fs,
                    large: large,
                    passAA: large ? r >= 3 : r >= 4.5,
                    passAAA: large ? r >= 4.5 : r >= 7
                });
            }
            const fails = samples.filter(s => !s.passAA);
            return {
                tested: samples.length,
                AA_pass: samples.filter(s => s.passAA).length,
                AAA_pass: samples.filter(s => s.passAAA).length,
                AA_fail_samples: fails.slice(0, 10)
            };
        }""")
        findings["contrast"] = contrast

        # 6) prefers-reduced-motion respect (recherche dans CSS)
        prm = await page.evaluate("""() => {
            const css = Array.from(document.styleSheets).flatMap(s => {
                try { return Array.from(s.cssRules||[]).map(r => r.cssText); } catch(e) { return []; }
            }).join('\\n');
            return {
                media_query_present: css.includes('prefers-reduced-motion'),
                anim_count: (css.match(/animation:/g)||[]).length,
                transition_count: (css.match(/transition:/g)||[]).length
            };
        }""")
        findings["reduced_motion"] = prm

        # 7) Tap target sizes
        taps = await page.evaluate("""() => {
            const sel = 'button, [role="button"], a, [onclick]';
            const els = Array.from(document.querySelectorAll(sel)).filter(el => el.offsetParent !== null);
            const sizes = els.map(el => {
                const r = el.getBoundingClientRect();
                return {w: Math.round(r.width), h: Math.round(r.height), ok44: r.width>=44 && r.height>=44, ok48: r.width>=48 && r.height>=48};
            });
            return {
                total: sizes.length,
                pass_44: sizes.filter(s => s.ok44).length,
                pass_48: sizes.filter(s => s.ok48).length,
                fail_44_samples: sizes.filter(s => !s.ok44).slice(0, 8)
            };
        }""")
        findings["tap_targets"] = taps

        # 8) Large-text mode / a11y toggles existants
        a11y_toggles = await page.evaluate("""() => {
            const text = document.body.innerText.toLowerCase();
            const opt = ['large text','grand texte','grande police','daltonien','colorblind','réduire mouvement','reduce motion','contraste','accessib'];
            const found = opt.filter(o => text.includes(o));
            return {found_keywords: found};
        }""")
        findings["a11y_keywords"] = a11y_toggles

        # 9) Recherche dans le source HTML pour confirmer features
        html_src = await page.content()
        findings["src_signals"] = {
            "has_aria_label": "aria-label" in html_src,
            "aria_label_count": html_src.count("aria-label"),
            "has_role": "role=" in html_src,
            "role_count": html_src.count("role="),
            "has_focus_visible": ":focus-visible" in html_src,
            "has_prm": "prefers-reduced-motion" in html_src,
            "has_high_contrast": "high-contrast" in html_src or "highContrast" in html_src,
            "has_large_text": "large-text" in html_src or "largeText" in html_src or "fontScale" in html_src,
            "has_colorblind": "colorblind" in html_src or "daltonien" in html_src or "colorBlind" in html_src,
            "screen_reader_only": ".sr-only" in html_src or "visually-hidden" in html_src,
        }

        # 10) Test reduced-motion via emulation
        await ctx.close()
        ctx2 = await browser.new_context(
            viewport={"width": 540, "height": 960},
            reduced_motion="reduce",
            is_mobile=True,
            locale="fr-FR",
        )
        page2 = await ctx2.new_page()
        await page2.goto(URL, wait_until="networkidle")
        await page2.wait_for_timeout(1000)
        rm_test = await page2.evaluate("""() => {
            const styles = Array.from(document.querySelectorAll('*'))
              .slice(0, 200)
              .map(el => getComputedStyle(el).animationDuration)
              .filter(d => d && d !== '0s');
            return {animated_elements: styles.length, sample_durations: styles.slice(0,5)};
        }""")
        findings["reduced_motion_runtime"] = rm_test

        await browser.close()

    with open(OUT + "D9-a11y-findings.json", "w", encoding="utf-8") as f:
        json.dump(findings, f, indent=2, ensure_ascii=False)
    print(json.dumps(findings, indent=2, ensure_ascii=False))


asyncio.run(main())

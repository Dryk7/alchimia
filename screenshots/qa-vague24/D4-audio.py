"""
D4-AUDIO — Audit READ-ONLY richesse audio FOULÉE
- Compte SFX distincts dans le code
- Compte presets BGM
- Vérifie ProcBGM API et adaptive layers
- Tente d'évaluer currentPreset à différents biomes
- Note finale sur 10
"""
import re
import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]  # D:/alchimia
INDEX = ROOT / "index.html"
SHOTS = Path(__file__).resolve().parent
SHOTS.mkdir(parents=True, exist_ok=True)

src = INDEX.read_text(encoding="utf-8", errors="ignore")

# --- STATIC ANALYSIS -------------------------------------------------------
sfx_funcs = re.findall(r"\n\s*function\s+(sfx\w+)\s*\(", src)
sfx_funcs = sorted(set(sfx_funcs))

# Compte "blip(...)" calls = mini-SFX one-shots
blip_calls = len(re.findall(r"\bblip\s*\(", src))
osc_calls = len(re.findall(r"createOscillator\s*\(", src))

# BGM presets dans ProcBGM
bgm_presets = re.findall(r"const\s+(INTRO|EARLY|STADIUM|CHILL|COSMIC|LUNAR|BOSS|FINAL|VICTORY)\s*=\s*\{", src)
bgm_presets = sorted(set(bgm_presets))

# Adaptive API
has_setIntensity = "setIntensity" in src
has_setTempo = "setTempo" in src
has_setVolume = "ProcBGM" in src and "setVolume" in src

# Signature jingles ?
has_intro_jingle = "ProcBGM.play('intro'" in src or 'ProcBGM.play("intro"' in src
has_km100_signature = bool(re.search(r"km\s*[>=]+\s*100", src, re.I)) and "blip" in src
has_boss_defeat_sfx = "sfxGrand" in src or "victory" in src.lower()
has_achievement_sfx = "achievement" in src.lower() and "blip" in src
has_kmBell = "sfxKmBell" in src

# Mute / volume control
has_mute = "STATE.audio" in src or "mute" in src.lower()
has_volume_slider = "bgmUserVolume" in src

# Spatial / stereo
has_panner = "createStereoPanner" in src or "PannerNode" in src
has_stereo = has_panner

# Fade vs cut
has_fade = "setTargetAtTime" in src or "linearRampToValue" in src

# Adaptive music based on context
adaptive_signals = {
    "stamina ratio": "stamina / Math.max" in src and "setIntensity" in src,
    "biome switch":  "syncBgmToBiome" in src,
    "tempo by stamina": "setTempo" in src and "sRatio" in src,
    "sprint kick layer": "sfxSprintKick" in src,
    "ducking sidechain": "bgmDuck" in src,
}

# --- RUNTIME PROBE ---------------------------------------------------------
runtime = {}
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 540, "height": 960})
        page = ctx.new_page()
        page.goto("http://localhost:8770", wait_until="domcontentloaded", timeout=15000)
        page.wait_for_timeout(2500)

        # Skip onboarding rapidement
        try:
            page.evaluate("localStorage.setItem('alchimia.onboarded','1')")
            page.evaluate("try{document.querySelectorAll('.intro-skip,#start-btn,#splash button').forEach(b=>b.click&&b.click())}catch(e){}")
        except Exception:
            pass
        page.wait_for_timeout(800)

        # Click sur la zone de jeu pour user-gesture (audio context)
        try:
            page.mouse.click(270, 700)
            page.wait_for_timeout(300)
            page.mouse.click(270, 700)
        except Exception:
            pass
        page.wait_for_timeout(1500)

        runtime["ProcBGM_exists"] = page.evaluate("typeof ProcBGM !== 'undefined'")
        runtime["isPlaying_t0"] = page.evaluate("(typeof ProcBGM!=='undefined' && ProcBGM.isPlaying && ProcBGM.isPlaying()) || false")
        runtime["preset_t0"]    = page.evaluate("(typeof ProcBGM!=='undefined' && ProcBGM.currentPreset && ProcBGM.currentPreset()) || null")

        # Force play chill puis sample currentPreset
        try:
            page.evaluate("typeof ProcBGM!=='undefined' && ProcBGM.play && ProcBGM.play('chill', 0.3)")
            page.wait_for_timeout(500)
            runtime["preset_after_chill"] = page.evaluate("ProcBGM.currentPreset()")
            page.evaluate("ProcBGM.play('intro', 0.3)")
            page.wait_for_timeout(400)
            runtime["preset_after_intro"] = page.evaluate("ProcBGM.currentPreset()")
            page.evaluate("ProcBGM.play('stadium', 0.3)")
            page.wait_for_timeout(400)
            runtime["preset_after_stadium"] = page.evaluate("ProcBGM.currentPreset()")
            page.evaluate("ProcBGM.play('early', 0.3)")
            page.wait_for_timeout(400)
            runtime["preset_after_early"] = page.evaluate("ProcBGM.currentPreset()")
            # Test adaptive API
            runtime["has_setIntensity_rt"] = page.evaluate("typeof ProcBGM.setIntensity === 'function'")
            runtime["has_setTempo_rt"]    = page.evaluate("typeof ProcBGM.setTempo === 'function'")
            page.evaluate("ProcBGM.setIntensity(1.2); ProcBGM.setTempo(1.1)")
            runtime["adaptive_call_ok"] = True
            page.evaluate("ProcBGM.stop && ProcBGM.stop()")
        except Exception as e:
            runtime["error"] = str(e)

        page.screenshot(path=str(SHOTS / "D4-audio-state.png"))
        browser.close()
except Exception as e:
    runtime["fatal"] = str(e)

# --- SCORE -----------------------------------------------------------------
n_sfx = len(sfx_funcs)
n_bgm = len(bgm_presets)
adaptive_count = sum(1 for v in adaptive_signals.values() if v)

# Note (0-10) :
# - SFX volume (target 50)
# - BGM variety (target 10)
# - Adaptive (target 5 signaux)
# - Polish (mute, volume, fade, signature)
sfx_score    = min(2.0, n_sfx / 50 * 2.0)          # max 2 si >=50
bgm_score    = min(2.0, n_bgm / 10 * 2.0)          # max 2 si >=10
adapt_score  = min(2.0, adaptive_count / 5 * 2.0)  # max 2 si >=5
polish_score = (
    (0.5 if has_mute else 0) +
    (0.5 if has_volume_slider else 0) +
    (0.5 if has_fade else 0) +
    (0.5 if has_intro_jingle else 0) +
    (0.5 if has_kmBell else 0) +
    (0.5 if has_stereo else 0)
)
mem_score    = 0.5 if has_intro_jingle else 0  # un thème reconnaissable ?
note = round(sfx_score + bgm_score + adapt_score + polish_score + mem_score, 1)
note = min(10.0, note)

report = {
    "sfx_distinct_functions": n_sfx,
    "sfx_function_names": sfx_funcs,
    "blip_oneshot_calls": blip_calls,
    "createOscillator_calls": osc_calls,
    "bgm_presets": bgm_presets,
    "bgm_count": n_bgm,
    "adaptive_signals": adaptive_signals,
    "has_setIntensity": has_setIntensity,
    "has_setTempo": has_setTempo,
    "has_mute": has_mute,
    "has_volume_slider": has_volume_slider,
    "has_stereo_panner": has_stereo,
    "has_fade_ramps": has_fade,
    "has_intro_jingle": has_intro_jingle,
    "has_kmBell": has_kmBell,
    "runtime": runtime,
    "scores": {
        "sfx": sfx_score, "bgm": bgm_score, "adaptive": adapt_score,
        "polish": polish_score, "memorability": mem_score,
    },
    "NOTE_AUDIO": note,
}
print(json.dumps(report, indent=2, ensure_ascii=False))
(SHOTS / "D4-audio-report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

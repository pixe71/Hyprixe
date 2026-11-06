"""Colour quality contracts; tiny deterministic images, no new dependency.

Pillow is already required for wallpaper validation. Colour transformations
themselves use only the Python standard library in common/theme/engine.py.
"""
import colorsys
import contextlib
import io
import json
import os
from pathlib import Path
import random
import shutil
import tempfile
import unittest
from unittest.mock import patch

import test_dynamic_theme as dynamic
from test_dynamic_theme import engine, RESOURCES


# Raw-palette fixtures exercise normalization independently from extraction.
# The same colours also generate 64x40 images for real Wallust/visual tests.
SWATCHES = {
    'very-dark': ('#030407', '#0b1020', '#121b35', '#211f34'),
    'very-light': ('#ffffff', '#fafaf9', '#f6f8ff', '#f7eeeb'),
    'monochrome-blue': ('#081b38', '#153e77', '#2663ab', '#80b3e4'),
    'monochrome-red': ('#381015', '#80232e', '#bd4553', '#e68b96'),
    'monochrome-green': ('#0a2417', '#1f5a34', '#3b8a52', '#86b48e'),
    'neon': ('#ff00d4', '#00ff7b', '#0073ff', '#f6ff00'),
    'pastel': ('#e5c9ea', '#c5e5dd', '#c8d9f3', '#f3d3b6'),
    'near-grayscale': ('#505151', '#777879', '#a9aaaa', '#d3d2d2'),
    'low-contrast': ('#697f87', '#6a8088', '#6b8189', '#6c828a'),
    'mostly-white': ('#ffffff', '#ffffff', '#fdfdfd', '#2a7caa'),
    'pure-black': ('#000000',) * 4,
    'pure-white': ('#ffffff',) * 4,
    'pale-yellow': ('#fffde8', '#fff2b0', '#e9d783', '#f5e5a4'),
}


def raw(colors):
    return dict(background=colors[0], foreground=colors[-1],
                colors=[colors[i % len(colors)] for i in range(16)])


def fixture(path, colors):
    from PIL import Image
    image = Image.new('RGB', (64, 40))
    variation = .50 if (min(engine.luminance(c) for c in colors) < .15
                        or max(engine.lch(c)[1] for c in colors) > .18) else .025
    pixels = []
    for y in range(40):
        for x in range(64):
            color = colors[x * len(colors) // 64]
            # Coloured images get a brightness gradient for genuine extraction.
            # Pale/low-contrast fixtures retain their narrow range; Wallust may
            # legitimately reject these, exercising the existing fallback.
            shade = 1 - variation * y / 39
            pixels.append(tuple(round(v * 255 * shade) for v in engine.rgb(color)))
    image.putdata(pixels)
    image.save(path)
    return path


class PerceptualColourTests(unittest.TestCase):
    def test_oklab_reference_primaries_and_round_trip(self):
        references = {'#ff0000': (.627955, .224863, .125846),
                      '#00ff00': (.866440, -.233888, .179498),
                      '#0000ff': (.452014, -.032457, -.311528)}
        for color, expected in references.items():
            for actual, target in zip(engine.oklab(color), expected):
                self.assertAlmostEqual(actual, target, places=5)
        for colors in SWATCHES.values():
            for color in colors:
                recovered = engine.tinted(*engine.lch(color))
                self.assertLessEqual(max(abs(a-b) for a, b in zip(engine.rgb(color), engine.rgb(recovered))), 1/255)

    def test_gamut_mapping_preserves_requested_lightness_and_hue(self):
        for degree in range(0, 360, 5):
            color = engine.tinted(.8, .35, degree/360)
            lightness, chroma, hue = engine.lch(color)
            self.assertAlmostEqual(lightness, .8, delta=.003)
            self.assertLess(chroma, .35)
            self.assertLess(engine.hue_distance(hue, degree/360), .004)


class RefinedPaletteTests(unittest.TestCase):
    def setUp(self):
        self.base = engine.defaults(RESOURCES)

    def palette(self, name):
        return engine.normalize(raw(SWATCHES[name]), self.base)

    def test_extreme_images_have_dark_ordered_low_chroma_surfaces(self):
        with tempfile.TemporaryDirectory() as folder:
            for name, colors in SWATCHES.items():
                with self.subTest(wallpaper=name):
                    image = fixture(Path(folder) / (name + '.png'), colors)
                    self.assertLess(image.stat().st_size, 4096)
                    palette = self.palette(name)
                    previous = 0
                    for role, low, high in (('background', .21, .24), ('surface', .295, .325), ('surface_alt', .36, .39)):
                        lightness, chroma, _ = engine.lch(palette[role])
                        self.assertTrue(low <= lightness <= high)
                        self.assertLessEqual(chroma, .025)
                        self.assertGreater(engine.luminance(palette[role]), previous)
                        previous = engine.luminance(palette[role])
                    self.assertLessEqual(previous, .065)
                    self.assertNotEqual(palette['background'], '#000000')

    def test_all_semantic_text_selection_and_accent_pairs_have_contrast(self):
        for name in SWATCHES:
            with self.subTest(wallpaper=name):
                p = self.palette(name)
                for text in ('foreground', 'foreground_muted'):
                    for background in ('background', 'surface', 'surface_alt'):
                        self.assertGreaterEqual(engine.contrast(p[text], p[background]), 4.5)
                for background in ('selection', 'workspace', 'border_secondary'):
                    self.assertGreaterEqual(engine.contrast(p['foreground'], p[background]), 4.5)
                for accent in ('accent', 'accent_alt'):
                    self.assertGreaterEqual(engine.contrast(p[accent], p['surface_alt']), 4.5)
                    self.assertGreaterEqual(engine.contrast(p['background'], p[accent]), 4.5)

    def test_perceptual_separation_and_restrained_chroma(self):
        for name in SWATCHES:
            with self.subTest(wallpaper=name):
                p = self.palette(name)
                for a, b, minimum in (('background', 'surface', .075), ('surface', 'surface_alt', .055),
                                     ('accent', 'accent_alt', .075), ('foreground', 'foreground_muted', .12)):
                    self.assertGreaterEqual(engine.distance(p[a], p[b]), minimum)
                for role in ('accent', 'accent_alt'):
                    lightness, chroma, _ = engine.lch(p[role])
                    self.assertTrue(.77 <= lightness <= .855)
                    self.assertTrue(.035 <= chroma <= .135)
                self.assertLessEqual(engine.lch(p['foreground_muted'])[1], .017)
                self.assertLessEqual(engine.lch(p['border'])[1], .028)
                self.assertLessEqual(engine.lch(p['border_focus'])[1], .068)
                self.assertNotEqual(p['foreground'], '#ffffff')

    def test_raw_alternative_is_preferred_over_invented_hue(self):
        colors = ('#3366cc', '#298b70', '#493da0', '#a1a3a4')
        p = engine.normalize(raw(colors), self.base)
        primary_hue = engine.lch(p['accent'])[2]
        alternate_hue = engine.lch(p['accent_alt'])[2]
        usable = [engine.lch(c)[2] for c in colors if engine.lch(c)[1] >= .025
                  and engine.hue_distance(primary_hue, engine.lch(c)[2]) >= .10]
        self.assertTrue(usable)
        self.assertLess(min(engine.hue_distance(alternate_hue, h) for h in usable), .005)

    def test_monochrome_alternative_is_analogous_but_distinct(self):
        for name in ('monochrome-blue', 'monochrome-red', 'monochrome-green', 'pure-black', 'pure-white'):
            p = self.palette(name)
            separation = engine.hue_distance(engine.lch(p['accent'])[2], engine.lch(p['accent_alt'])[2])
            self.assertTrue(.10 < separation < .17)
            self.assertGreaterEqual(engine.distance(p['accent'], p['accent_alt']), .075)

    def test_dull_brown_does_not_displace_a_usable_wallpaper_colour(self):
        p = engine.normalize(raw(('#634b35', '#306b9e', '#111111', '#eeeeee')), self.base)
        self.assertLess(engine.hue_distance(engine.lch(p['accent'])[2], engine.lch('#306b9e')[2]), .005)

    def test_blue_red_green_keep_different_hues_and_tinted_surfaces(self):
        palettes = [self.palette('monochrome-' + name) for name in ('blue', 'red', 'green')]
        self.assertEqual(len({p['background'] for p in palettes}), 3)
        for i, a in enumerate(palettes):
            for b in palettes[i+1:]:
                self.assertGreater(engine.distance(a['accent'], b['accent']), .10)

    def test_achromatic_images_use_restrained_reference_hue(self):
        for name in ('pure-black', 'pure-white', 'near-grayscale'):
            p = self.palette(name)
            self.assertLess(engine.hue_distance(engine.lch(p['accent'])[2], engine.lch(self.base['accent'])[2]), .005)

    def test_status_hues_are_stable_semantic_and_readable(self):
        previous = None
        for name in SWATCHES:
            p = self.palette(name)
            status = {r: p[r] for r in ('success', 'warning', 'error')}
            if previous:
                self.assertEqual(status, previous)
            previous = status
            for role, color in status.items():
                self.assertLess(engine.hue_distance(engine.lch(color)[2], engine.lch(self.base[role])[2]), .005)
                self.assertGreaterEqual(engine.contrast(color, p['surface_alt']), 4.5)
            red, green, blue = engine.rgb(p['error'])
            self.assertGreater(red, green)
            self.assertGreater(red, blue)
            red, green, blue = engine.rgb(p['success'])
            self.assertGreater(green, red)
            self.assertGreater(green, blue)

    def test_quantized_monochrome_hue_sweep_and_seeded_palettes_are_valid(self):
        for degree in range(360):
            color = engine.hexcolor(colorsys.hsv_to_rgb(degree/360, 1, 1))
            engine.validate_palette(engine.normalize(raw((color,)), self.base), self.base)
        rng = random.Random(125)
        for _ in range(400):
            colors = tuple(f'#{rng.randrange(1 << 24):06x}' for _ in range(16))
            engine.validate_palette(engine.normalize(raw(colors), self.base), self.base)

    def test_normalization_is_deterministic_and_raw_order_independent(self):
        for colors in SWATCHES.values():
            expected = engine.normalize(raw(colors), self.base)
            for permutation in (colors[::-1], colors[1:] + colors[:1], colors):
                self.assertEqual(engine.normalize(raw(permutation), self.base), expected)

    def test_validator_rejects_collapsed_roles_and_neon_surfaces(self):
        p = self.palette('neon')
        for changes in ({'accent_alt': p['accent']}, {'surface': p['background']},
                        {'foreground_muted': p['foreground']}, {'surface': '#402070'},
                        {'error': '#323232'}, {'selection': '#e0e0e0'}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                engine.validate_palette(dict(p, **changes), self.base)

    def test_component_contrasts_include_existing_translucent_layers(self):
        for name in SWATCHES:
            with self.subTest(wallpaper=name):
                p = self.palette(name)
                # Brightest backdrop is conservative for these bright texts.
                bar = engine.blend(p['background'], '#ffffff', .76)
                module = engine.blend(p['surface'], bar, .32)
                workspace = p['workspace']
                hover = engine.blend(p['border_secondary'], bar, .45)
                rofi = engine.blend(p['surface'], '#ffffff', .82)
                selected = engine.blend(p['selection'], rofi, .92)
                rofi_input = engine.blend(p['surface_alt'], rofi, .40)
                # Hyprlock wallpaper brightness is .8, inner field alpha .60.
                lock_input = engine.blend(p['background'], '#cccccc', .60)
                # Weakest SDDM gradient alpha .082, card .69, input .69.
                sddm_overlay = engine.blend(p['background'], '#ffffff', .082)
                card = engine.blend(p['background'], sddm_overlay, .69)
                sddm_input = engine.blend(p['surface'], card, .69)
                for bg in (module, workspace, hover, selected, rofi_input, lock_input, sddm_input):
                    self.assertGreaterEqual(engine.contrast(p['foreground'], bg), 4.5)
                for role in ('accent', 'accent_alt', 'success', 'warning', 'error'):
                    self.assertGreaterEqual(engine.contrast(p[role], hover), 4.5)
                self.assertGreaterEqual(engine.contrast(p['background'], p['error']), 4.5)
                # Kitty selection/cursor and SDDM selection/pressed button.
                self.assertGreaterEqual(engine.contrast(p['background'], p['accent']), 4.5)
                self.assertGreaterEqual(engine.contrast(p['foreground'], p['background']), 4.5)

    def test_templates_and_static_styles_keep_correct_text_and_status_roles(self):
        for name in SWATCHES:
            p = self.palette(name)
            outputs = engine.render(RESOURCES, p)
            kitty = dict(line.split() for line in outputs['kitty.conf'].splitlines())
            for text, bg in (('foreground', 'background'), ('cursor_text_color', 'cursor'),
                             ('selection_foreground', 'selection_background')):
                self.assertGreaterEqual(engine.contrast(kitty[text], kitty[bg]), 4.5)
            self.assertIn('selected: ' + p['selection'], outputs['rofi.rasi'])
            self.assertIn('urgent: ' + p['error'], outputs['rofi.rasi'])
            self.assertIn('$hx_error = rgba(' + p['error'][1:], outputs['hyprlock.conf'])
            with tempfile.TemporaryDirectory() as folder:
                path = Path(folder)
                for filename, text in outputs.items():
                    (path / filename).write_text(text)
                engine.validate_outputs(path, native=False)
        waybar = (dynamic.ROOT / 'common/config/hypr/waybar/style/Frosted-Glass.css').read_text()
        self.assertRegex(waybar, r'#battery\.warning[^\{]*\{\s*color: @hx_warning;')
        self.assertRegex(waybar, r'#battery\.critical[^\{]*\{\s*color: @hx_error;')
        self.assertRegex(waybar, r'#workspaces button\.urgent\s*\{\s*background: @hx_error;')
        main = (dynamic.ROOT / 'common/sddm/themes/hyprixe-frosted/Main.qml').read_text()
        button = (dynamic.ROOT / 'common/sddm/themes/hyprixe-frosted/components/GlassButton.qml').read_text()
        self.assertIn('selectedTextColor: dynamicTheme.paint("background", "white")', main)
        self.assertIn('control.down ? control.theme.paint("background", "#e6f1f4")', button)

    def test_generated_extreme_palettes_accept_available_native_parsers(self):
        for name in ('neon', 'very-light', 'monochrome-red'):
            with self.subTest(wallpaper=name), tempfile.TemporaryDirectory() as folder:
                path = Path(folder)
                for filename, text in engine.render(RESOURCES, self.palette(name)).items():
                    (path / filename).write_text(text)
                engine.validate_outputs(path)


class PaletteStabilityTests(unittest.TestCase):
    # Reuse the isolated runtime harness without inheriting/rerunning its suite.
    setUp = dynamic.TransactionTests.setUp
    generate = dynamic.TransactionTests.generate

    def test_same_image_keeps_palette_after_refresh_cache_deletion_and_login(self):
        for name, colors in SWATCHES.items():
            with self.subTest(wallpaper=name):
                image = fixture(self.root / (name + '.png'), colors)
                self.extract.return_value = raw(colors)
                self.generate(image, force=True)
                expected = (self.engine.current / 'palette.json').read_bytes()
                state = self.engine.load_state()
                self.engine.transact(force=True, apply=False, reload=False)
                self.assertEqual((self.engine.current / 'palette.json').read_bytes(), expected)
                shutil.rmtree(self.engine.cache)
                # A fresh process performs the same init/restore transaction.
                recovered = engine.Engine(self.resources)
                with patch.object(recovered, 'extract', return_value=raw(colors)), \
                     patch.object(recovered, 'version', return_value=engine.WALLUST_VERSION):
                    recovered.transact(apply=False, reload=False, initialize=True)
                self.assertEqual((recovered.current / 'palette.json').read_bytes(), expected)
                self.assertEqual(recovered.load_state(), state)

    def test_min_forest_palette_remains_exact_reference_for_original_and_copy(self):
        expected = engine.defaults(self.resources)
        for image in (self.reference, self.root / 'renamed forest.jpg'):
            if image != self.reference:
                shutil.copyfile(self.reference, image)
            self.generate(image, force=True)
            self.assertEqual(json.loads((self.engine.current / 'palette.json').read_text()), expected)

    @unittest.skipUnless(shutil.which('wallust'), 'real pinned Wallust is optional in source-only tests')
    def test_real_wallust_extreme_images_repeat_deterministically_or_use_fallback(self):
        runtime = engine.Engine(self.resources)
        # self.engine.version is mocked, runtime.version is the real executable.
        if runtime.version() != engine.WALLUST_VERSION:
            self.skipTest('needs the pinned Wallust 3.5.1')
        successes = []
        for name, colors in SWATCHES.items():
            with self.subTest(wallpaper=name):
                image = fixture(self.root / (name + '.png'), colors)
                palettes, sources = [], []
                for _ in range(2):
                    with contextlib.redirect_stderr(io.StringIO()):
                        meta = runtime.transact(image, enabled=True, apply=False, reload=False, force=True)
                    palettes.append((runtime.current / 'palette.json').read_bytes())
                    sources.append(meta['source'])
                    engine.validate_palette(json.loads(palettes[-1]), runtime.base)
                self.assertEqual(palettes[0], palettes[1])
                self.assertEqual(sources[0], sources[1])
                if sources[0] == 'wallust':
                    successes.append(name)
        self.assertIn('neon', successes)
        self.assertGreaterEqual(len(successes), 4)


if __name__ == '__main__':
    unittest.main()

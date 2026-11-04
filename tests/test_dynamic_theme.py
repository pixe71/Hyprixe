"""Semantic palette, real formats, transactions and generated tiny images."""
import contextlib
import io
import json
import multiprocessing
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

from support import ROOT
sys.path.insert(0, str(ROOT / 'common/theme'))
import engine

RESOURCES = ROOT / 'common/theme'
# Generated at test time: 32x32 RGB gradients, no binary wallpaper fixtures.
SWATCHES = {'dark-blue': (12, 35, 90), 'forest': (25, 95, 45),
            'red-orange': (220, 65, 30), 'purple': (115, 45, 165),
            'very-light': (248, 246, 242), 'monochrome': (110, 111, 110)}


def fixture(path, color):
    from PIL import Image
    image = Image.new('RGB', (32, 32))
    image.putdata([tuple(max(0, min(255, round(v * (.35 + x / 32) + y * 2))) for v in color)
                   for y in range(32) for x in range(32)])
    image.save(path)
    return path


def raw(color):
    value = engine.hexcolor(v / 255 for v in color)
    return {'background': '#101010', 'foreground': '#eeeeee', 'colors': [value] * 16}


def acquire_lock(resources, started, acquired):
    started.set()
    with engine.Engine(Path(resources)).locked():
        acquired.set()


class PaletteTests(unittest.TestCase):
    def test_six_synthetic_palettes_are_dark_semantic_and_readable(self):
        base = engine.defaults(RESOURCES)
        for name, color in SWATCHES.items():
            with self.subTest(name=name):
                palette = engine.normalize(raw(color), base)
                self.assertEqual(set(palette), set(base))
                engine.validate_palette(palette, base)
                self.assertLess(engine.luminance(palette['background']), .06)
                for surface in ('background', 'surface', 'surface_alt'):
                    self.assertGreaterEqual(engine.contrast(palette['foreground_muted'], palette[surface]), 4.5)
                self.assertGreaterEqual(engine.contrast(palette['accent'], palette['surface_alt']), 4.5)
                self.assertGreaterEqual(engine.contrast(palette['border'], palette['background']), 3)

    def test_mapping_tracks_hue_but_preserves_status_meanings(self):
        base = engine.defaults(RESOURCES)
        blue = engine.normalize(raw(SWATCHES['dark-blue']), base)
        green = engine.normalize(raw(SWATCHES['forest']), base)
        self.assertNotEqual(blue['accent'], green['accent'])
        for role in ('success', 'warning', 'error'):
            # Contrast correction may lighten a status colour, preserving hue.
            blue_hue = engine.colorsys.rgb_to_hls(*engine.rgb(blue[role]))[0]
            green_hue = engine.colorsys.rgb_to_hls(*engine.rgb(green[role]))[0]
            self.assertAlmostEqual(blue_hue, green_hue, delta=.01)

    def test_default_palette_matches_v11_reference(self):
        base = engine.defaults(RESOURCES)
        self.assertEqual(base['background'], '#122434')
        self.assertEqual(base['accent'], '#7ed6ff')
        engine.validate_palette(base, base)

    def test_invalid_raw_colours_and_roles_are_rejected(self):
        base = engine.defaults(RESOURCES)
        for value in ('red', '#fff', '#aabbcc; exec malicious', None):
            data = raw(SWATCHES['forest']); data['colors'][0] = value
            with self.assertRaises(ValueError):
                engine.normalize(data, base)
        with self.assertRaises(ValueError):
            engine.validate_palette(dict(base, background='#ffffff'), base)
        with self.assertRaises(ValueError):
            engine.validate_palette(dict(base, accent='invalid'), base)


class TransactionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='hyprixe theme tests ')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        env = {f'XDG_{name}_HOME': str(self.root / name.lower()) for name in ('CACHE', 'STATE', 'DATA')}
        env['HOME'] = str(self.root)
        self.environment = patch.dict(os.environ, env)
        self.environment.start(); self.addCleanup(self.environment.stop)
        self.resources = self.root / 'resources'
        shutil.copytree(RESOURCES, self.resources, ignore=shutil.ignore_patterns('__pycache__'))
        fallback = self.resources / 'fallback'; fallback.mkdir()
        for name, text in engine.render(self.resources, engine.defaults(self.resources)).items():
            (fallback / name).write_text(text)
        self.engine = engine.Engine(self.resources)
        self.reference = self.engine.data / 'wallpapers/min_forest.jpg'
        self.reference.parent.mkdir(parents=True)
        shutil.copyfile(ROOT / 'common/wallpapers/min_forest.jpg', self.reference)
        self.image = fixture(self.root / 'forest with spaces.png', SWATCHES['forest'])
        self.extract = patch.object(self.engine, 'extract', return_value=raw(SWATCHES['forest'])).start()
        self.version = patch.object(self.engine, 'version', return_value=engine.WALLUST_VERSION).start()
        self.apply = patch.object(self.engine, 'apply_image').start()
        self.reload = patch.object(self.engine, 'reload', return_value=[]).start()
        validator = engine.validate_outputs
        self.validate = patch('engine.validate_outputs', side_effect=lambda directory, native=True: validator(directory, native=False)).start()
        self.addCleanup(patch.stopall)

    def generate(self, wallpaper=None, **kwargs):
        if self.engine.load_state() is None:
            kwargs.setdefault('enabled', True)  # Existing tests explicitly opt in.
        return self.engine.transact(wallpaper or self.image, **kwargs)

    def test_successful_extraction_and_single_presentation(self):
        meta = self.generate()
        self.assertEqual(meta['source'], 'wallust')
        self.assertEqual(self.engine.read(), meta)
        self.assertEqual(meta['wallpaper_hash'], engine.sha(self.image))
        self.extract.assert_called_once()
        self.apply.assert_called_once_with(self.image)
        self.reload.assert_called_once()
        self.assertEqual(self.engine.load_state()['wallpaper'], str(self.image))

    def test_disabled_preference_survives_corrupt_fragment_and_refresh(self):
        self.extract.side_effect = ValueError('Wallust failed')
        for name in ('waybar.css', 'metadata.json'):
            with self.subTest(corrupt=name):
                self.generate(enabled=False)
                (self.engine.current / name).write_text('corrupt')
                self.engine.transact(force=True, apply=False, reload=False)
                self.assertFalse(self.engine.load_state()['enabled'])
                self.assertFalse(self.engine.read()['enabled'])
        self.extract.assert_not_called()

    def test_selected_wallpaper_and_preference_survive_complete_cache_deletion(self):
        for enabled in (True, False):
            with self.subTest(enabled=enabled):
                self.generate(enabled=enabled, force=True)
                saved = self.engine.load_state()
                state_bytes = (self.engine.state / 'theme.json').read_bytes()
                shutil.rmtree(self.engine.cache.parent)
                recovered = engine.Engine(self.resources)
                self.assertEqual(recovered.load_state(), saved)
                self.assertEqual(recovered.wallpaper(), self.image)
                self.assertEqual(recovered.cache_status(saved), 'missing')
                with patch.object(recovered, 'extract', return_value=raw(SWATCHES['forest'])), \
                     patch.object(recovered, 'version', return_value=engine.WALLUST_VERSION):
                    recovered.transact(force=True, apply=False, reload=False)
                self.assertEqual(recovered.load_state(), saved)
                self.assertEqual((recovered.state / 'theme.json').read_bytes(), state_bytes)
                self.assertEqual(recovered.cache_status(saved), 'valid')

    def test_status_reads_disabled_state_without_creating_missing_cache(self):
        self.generate(enabled=False)
        shutil.rmtree(self.engine.cache.parent)
        output = io.StringIO()
        with patch('engine.Engine', return_value=self.engine), contextlib.redirect_stdout(output):
            self.assertEqual(engine.main(['status']), 0)
        self.assertIn('dynamic theming: disabled', output.getvalue())
        self.assertIn('current wallpaper: ' + str(self.image), output.getvalue())
        self.assertIn('wallpaper hash: ' + engine.sha(self.image), output.getvalue())
        self.assertIn('cache: missing', output.getvalue())
        self.assertFalse(self.engine.cache.exists())

    def test_corrupt_state_fails_closed_without_recovering_enabled_from_cache(self):
        self.generate()
        path = self.engine.state / 'theme.json'
        for content in ('{broken', '[]', '{"format": 2, "enabled": "false"}'):
            with self.subTest(content=content):
                path.write_text(content)
                before = self.engine.current.resolve()
                with self.assertRaisesRegex(ValueError, 'Persistent theme state'):
                    self.engine.transact(force=True, apply=False, reload=False)
                self.assertEqual(path.read_text(), content)
                self.assertEqual(self.engine.current.resolve(), before)
                with patch('engine.Engine', return_value=self.engine), contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(engine.main(['status']), 1)

    def test_missing_selected_image_uses_fallback_without_losing_selection_or_mode(self):
        self.generate(enabled=False)
        saved = self.engine.load_state()
        self.image.unlink()
        with contextlib.redirect_stderr(io.StringIO()) as errors:
            meta = self.engine.transact(force=True, apply=False, reload=False)
        self.assertIn('wallpaper unavailable', errors.getvalue())
        self.assertEqual(self.engine.load_state(), saved)
        self.assertEqual(meta['wallpaper'], str(self.reference))
        self.assertFalse(meta['enabled'])
        self.extract.assert_not_called()

    def test_explicit_disable_persists_even_when_generation_fails(self):
        self.generate()
        (self.resources / 'templates/waybar.css').write_text('@unknown_role@')
        with self.assertRaises(ValueError):
            self.engine.transact(enabled=False, force=True, apply=False, reload=False)
        self.assertFalse(self.engine.load_state()['enabled'])

    def test_preference_update_and_wallpaper_state_use_atomic_writes(self):
        self.generate(enabled=False)
        saved = (self.engine.state / 'theme.json').read_bytes()
        original_replace = engine.os.replace
        def fail_state(source, destination):
            if Path(destination) == self.engine.state / 'theme.json':
                raise OSError('state rename interrupted')
            return original_replace(source, destination)
        with patch('engine.os.replace', side_effect=fail_state):
            with self.assertRaises(OSError):
                self.engine.transact(enabled=True, force=True, apply=False, reload=False)
        self.assertEqual((self.engine.state / 'theme.json').read_bytes(), saved)
        self.assertFalse(list(self.engine.state.glob('.tmp-*')))

    def test_failed_apply_does_not_save_new_wallpaper_or_hash(self):
        self.generate(enabled=False)
        saved = self.engine.load_state()
        other = fixture(self.root / 'other.png', SWATCHES['purple'])
        self.reload.side_effect = [ValueError('reload failed'), []]
        with self.assertRaises(ValueError):
            self.engine.transact(other)
        self.assertEqual(self.engine.load_state(), saved)

    def legacy(self, *, corrupt_fragment=False, corrupt_metadata=False, enabled=False):
        self.generate(enabled=enabled)
        persistent = self.engine.state / 'theme.json'
        persistent.unlink()
        persistent.symlink_to(self.engine.current / 'metadata.json')
        meta = self.engine.current / 'metadata.json'
        contents = json.loads(meta.read_text()); contents.pop('state_hash', None)
        meta.write_text(json.dumps(contents))
        (self.engine.state / 'wallpaper').symlink_to(self.engine.current / 'wallpaper-path')
        if corrupt_fragment:
            (self.engine.current / 'waybar.css').write_text('corrupt')
        if corrupt_metadata:
            (self.engine.current / 'metadata.json').write_text('{broken')

    def test_legacy_symlinks_migrate_disabled_even_with_corrupt_colours(self):
        self.legacy(corrupt_fragment=True)
        self.engine.transact(force=True, apply=False, reload=False)
        persistent = self.engine.state / 'theme.json'
        self.assertFalse(persistent.is_symlink())
        self.assertEqual(self.engine.load_state(), {'format': 2, 'enabled': False,
                         'wallpaper': str(self.image), 'wallpaper_hash': engine.sha(self.image)})
        self.assertFalse((self.engine.state / 'wallpaper').is_symlink())

    def test_unreadable_legacy_preference_is_migrated_disabled(self):
        self.legacy(corrupt_metadata=True, enabled=True)
        with contextlib.redirect_stderr(io.StringIO()):
            self.engine.transact(force=True, apply=False, reload=False)
        self.assertFalse(self.engine.load_state()['enabled'])
        self.assertEqual(self.engine.load_state()['wallpaper'], str(self.image))

    def test_dangling_legacy_state_does_not_enable_theming(self):
        self.legacy(enabled=False)
        shutil.rmtree(self.engine.cache.parent)
        with contextlib.redirect_stderr(io.StringIO()):
            self.engine.transact(force=True, apply=False, reload=False)
        self.assertFalse(self.engine.load_state()['enabled'])

    def test_only_enable_changes_an_existing_disabled_preference(self):
        self.generate(enabled=False)
        with patch('engine.Engine', return_value=self.engine):
            for arguments in (['apply', str(self.image)], ['refresh'], ['default'], ['init']):
                with self.subTest(command=arguments):
                    self.assertEqual(engine.main(arguments), 0)
                    self.assertFalse(self.engine.load_state()['enabled'])
            self.assertEqual(engine.main(['enable']), 0)
            self.assertTrue(self.engine.load_state()['enabled'])

    def test_apply_refresh_and_default_preserve_an_enabled_preference(self):
        self.generate(enabled=True)
        with patch('engine.Engine', return_value=self.engine):
            for arguments in (['apply', str(self.image)], ['refresh'], ['default']):
                with self.subTest(command=arguments):
                    self.assertEqual(engine.main(arguments), 0)
                    self.assertTrue(self.engine.load_state()['enabled'])
            self.assertEqual(self.engine.read()['source'], 'frosted-glass')
            self.assertEqual(engine.main(['refresh']), 0)
            self.assertEqual(self.engine.read()['source'], 'wallust')

    def test_first_install_init_is_the_only_implicit_initial_opt_in(self):
        with patch('engine.Engine', return_value=self.engine):
            self.assertEqual(engine.main(['init']), 0)
        self.assertTrue(self.engine.load_state()['enabled'])

    def test_apply_without_any_state_is_disabled_until_explicitly_enabled(self):
        with patch('engine.Engine', return_value=self.engine):
            self.assertEqual(engine.main(['apply', str(self.image)]), 0)
        self.assertFalse(self.engine.load_state()['enabled'])
        self.extract.assert_not_called()

    def test_reinstall_init_preserves_selection_after_cache_loss(self):
        self.generate(enabled=False)
        saved = self.engine.load_state()
        shutil.rmtree(self.engine.cache.parent)
        with patch('engine.Engine', return_value=self.engine), patch('engine.shutil.which') as executable:
            self.assertEqual(engine.main(['init']), 0)
            executable.assert_not_called()  # No active-image discovery on recovery.
        self.assertEqual(self.engine.load_state(), saved)

    def test_status_distinguishes_dynamic_default_and_invalid_cache(self):
        self.generate(enabled=True)
        with patch('engine.Engine', return_value=self.engine):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(engine.main(['status']), 0)
            self.assertIn('palette: dynamic', output.getvalue())
            self.assertIn('cache: valid', output.getvalue())
            self.generate(enabled=False)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(engine.main(['status']), 0)
            self.assertIn('palette: default', output.getvalue())
            (self.engine.current / 'waybar.css').write_text('corrupt')
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(engine.main(['status']), 0)
            self.assertIn('dynamic theming: disabled', output.getvalue())
            self.assertIn('cache: invalid', output.getvalue())
            self.assertIn('palette: unavailable', output.getvalue())

    def test_legacy_enabled_preference_migrates_without_losing_selection(self):
        self.legacy(enabled=True)
        self.engine.transact(force=True, apply=False, reload=False)
        self.assertTrue(self.engine.load_state()['enabled'])
        self.assertEqual(self.engine.load_state()['wallpaper'], str(self.image))

    def test_atomic_state_commit_failure_rolls_back_new_wallpaper_and_cache(self):
        self.generate(enabled=False)
        saved = self.engine.load_state()
        previous = self.engine.current.resolve()
        other = fixture(self.root / 'purple.png', SWATCHES['purple'])
        original_save = self.engine.save_state
        def fail_selection(candidate):
            if candidate['wallpaper'] == str(other):
                raise OSError('state commit failed')
            original_save(candidate)
        with patch.object(self.engine, 'save_state', side_effect=fail_selection):
            with self.assertRaises(OSError):
                self.engine.transact(other)
        self.assertEqual(self.engine.current.resolve(), previous)
        self.assertEqual(self.engine.load_state(), saved)
        self.assertEqual(self.apply.call_args.args, (self.image,))

    def test_persistent_lock_survives_deletion_of_cache_parent(self):
        with self.engine.locked():
            self.engine.ensure_cache()
            lock = self.engine.state / 'theme.lock'
            inode = lock.stat().st_ino
            shutil.rmtree(self.engine.cache.parent)
            self.assertEqual(lock.stat().st_ino, inode)

    def test_invalid_wallpaper_preserves_current_generation(self):
        self.generate()
        before = self.engine.current.resolve()
        bad = self.root / 'not an image.png'; bad.write_bytes(b'not an image')
        with self.assertRaisesRegex(ValueError, 'Invalid wallpaper'):
            self.generate(bad)
        self.assertEqual(self.engine.current.resolve(), before)
        self.assertEqual(self.apply.call_count, 1)

    def test_missing_wallust_and_extraction_failure_use_frosted_defaults(self):
        for failure in (ValueError('Wallust absent'), ValueError('extraction failed')):
            with self.subTest(failure=failure), contextlib.redirect_stderr(io.StringIO()):
                self.extract.side_effect = failure
                meta = self.generate(force=True)
                self.assertEqual(meta['source'], 'fallback')
                self.assertEqual(json.loads((self.engine.current / 'palette.json').read_text()), self.engine.base)

    def test_reference_calibration_is_hash_based_even_after_rename(self):
        copy = self.root / 'renamed.jpg'; shutil.copyfile(self.reference, copy)
        meta = self.generate(copy)
        self.assertEqual(meta['source'], 'wallust-calibrated')
        self.assertEqual(json.loads((self.engine.current / 'palette.json').read_text()), self.engine.base)

    def test_identical_apply_does_not_extract_reload_rewrite_or_present_again(self):
        self.generate()
        before = self.engine.current.lstat().st_mtime_ns
        self.generate()
        self.assertEqual(self.extract.call_count, 1)
        self.assertEqual(self.apply.call_count, 1)
        self.assertEqual(self.reload.call_count, 1)
        self.assertEqual(self.engine.current.lstat().st_mtime_ns, before)

    def test_login_restores_wallpaper_without_regenerating(self):
        self.generate()
        before = self.engine.current.resolve()
        self.engine.transact(restore=True)
        self.assertEqual(self.extract.call_count, 1)
        self.assertEqual(self.apply.call_count, 2)
        self.assertEqual(self.engine.current.resolve(), before)

    def test_changed_image_bytes_invalidate_hash_and_generation(self):
        old = self.generate()
        fixture(self.image, SWATCHES['purple'])
        new = self.generate()
        self.assertNotEqual(old['wallpaper_hash'], new['wallpaper_hash'])
        self.assertEqual(self.extract.call_count, 2)

    def test_revisiting_wallpaper_reuses_hash_cache(self):
        self.generate()
        other = fixture(self.root / 'blue.png', SWATCHES['dark-blue'])
        self.generate(other)
        self.generate()
        self.assertEqual(self.extract.call_count, 2)

    def test_refresh_and_template_change_invalidate_cache(self):
        self.generate()
        self.generate(force=True)
        self.assertEqual(self.extract.call_count, 2)
        template = self.resources / 'templates/hyprland.lua'
        template.write_text(template.read_text() + '\n')
        self.generate()
        self.assertEqual(self.extract.call_count, 3)

    def test_disable_survives_wallpaper_changes_and_enable_regenerates(self):
        self.generate(enabled=False)
        self.assertEqual(self.extract.call_count, 0)
        self.engine.transact(force=True)
        self.assertFalse(self.engine.read()['enabled'])
        self.assertEqual(self.extract.call_count, 0)
        self.generate(enabled=True, force=True)
        self.assertEqual(self.extract.call_count, 1)

    def test_default_is_explicit_and_does_not_extract(self):
        self.generate(use_default=True)
        self.extract.assert_not_called()
        self.assertEqual(self.engine.read()['source'], 'frosted-glass')

    def test_corrupt_output_is_detected_and_restored(self):
        self.generate()
        (self.engine.current / 'waybar.css').write_text('corrupt')
        self.assertIsNone(self.engine.read())
        self.engine.transact(apply=False, reload=False)
        self.assertIsNotNone(self.engine.read())

    def test_bad_template_preserves_previous_without_changing_wallpaper(self):
        self.generate()
        previous = self.engine.current.resolve()
        (self.resources / 'templates/waybar.css').write_text('@unknown_role@')
        with self.assertRaisesRegex(ValueError, 'Unknown semantic'):
            self.generate(force=True)
        self.assertEqual(self.engine.current.resolve(), previous)
        self.assertEqual(self.apply.call_count, 1)

    def test_invalid_template_without_cache_uses_installed_emergency_default(self):
        (self.resources / 'templates/waybar.css').write_text('broken')
        meta = self.generate()
        self.assertEqual(meta['source'], 'fallback')
        self.assertIsNotNone(self.engine.read())

    def test_wallpaper_failure_does_not_activate_prepared_generation(self):
        self.generate()
        previous = self.engine.current.resolve()
        self.apply.side_effect = ValueError('awww failure')
        other = fixture(self.root / 'blue.png', SWATCHES['dark-blue'])
        with self.assertRaises(ValueError):
            self.generate(other)
        self.assertEqual(self.engine.current.resolve(), previous)

    def test_corrupt_metadata_is_not_treated_as_a_cache_hit(self):
        self.generate()
        metadata = self.engine.current / 'metadata.json'
        data = json.loads(metadata.read_text()); del data['wallpaper_hash']
        metadata.write_text(json.dumps(data))
        self.assertIsNone(self.engine.read())
        self.engine.transact(apply=False, reload=False)
        self.assertIsNotNone(self.engine.read())

    def test_reload_failure_rolls_back_generation_and_wallpaper(self):
        old = self.generate()
        previous = self.engine.current.resolve()
        self.reload.side_effect = [ValueError('reload failed'), []]
        other = fixture(self.root / 'blue.png', SWATCHES['dark-blue'])
        with self.assertRaises(ValueError):
            self.generate(other)
        self.assertEqual(self.engine.current.resolve(), previous)
        self.assertEqual(self.apply.call_args.args, (Path(old['wallpaper']),))

    def test_first_activation_failure_keeps_importable_default_colours(self):
        self.reload.side_effect = ValueError('activation failed')
        with self.assertRaises(ValueError):
            self.generate()
        self.assertEqual(self.engine.read()['source'], 'fallback')
        self.assertEqual(json.loads((self.engine.current / 'palette.json').read_text()), self.engine.base)

    def test_image_mutation_during_extraction_is_rejected_before_presentation(self):
        def extract(*args):
            fixture(self.image, SWATCHES['purple'])
            return raw(SWATCHES['purple'])
        self.extract.side_effect = extract
        with self.assertRaisesRegex(ValueError, 'changed during'):
            self.generate()
        self.apply.assert_not_called()
        self.assertFalse(self.engine.current.exists())

    def test_all_components_publish_through_one_atomic_pointer(self):
        self.generate()
        original_publish = self.engine.publish
        previous = self.engine.current.resolve()
        def check(destination):
            self.assertEqual(self.engine.current.resolve(), previous)
            for name in engine.FILES:
                self.assertTrue((destination / name).is_file())
            original_publish(destination)
        with patch.object(self.engine, 'publish', side_effect=check):
            self.generate(force=True)
        self.assertNotEqual(self.engine.current.resolve(), previous)

    def test_atomic_file_replace_failure_keeps_original(self):
        path = self.root / 'atomic'; path.write_text('before')
        with patch('engine.os.replace', side_effect=OSError('interrupted')):
            with self.assertRaises(OSError): engine.atomic(path, 'after')
        self.assertEqual(path.read_text(), 'before')
        self.assertFalse(list(self.root.glob('.tmp-*')))

    def test_unowned_cache_and_state_are_never_overwritten(self):
        self.engine.cache.mkdir(parents=True)
        personal = self.engine.cache / 'personal'; personal.write_text('keep')
        with self.assertRaisesRegex(ValueError, 'unowned theme cache'):
            self.generate()
        self.assertEqual(personal.read_text(), 'keep')

    def test_unowned_state_is_refused_before_presentation(self):
        self.engine.state.mkdir(parents=True)
        personal = self.engine.state / 'wallpaper'; personal.write_text('my wallpaper')
        with self.assertRaisesRegex(ValueError, 'unowned state'):
            self.generate()
        self.apply.assert_not_called()
        self.assertEqual(personal.read_text(), 'my wallpaper')

    def test_transaction_lock_serializes_processes(self):
        context = multiprocessing.get_context('spawn')
        started, acquired = context.Event(), context.Event()
        with self.engine.locked():
            process = context.Process(target=acquire_lock, args=(str(self.resources), started, acquired)); process.start()
            self.assertTrue(started.wait(5))
            self.assertFalse(acquired.wait(.15))
        self.assertTrue(acquired.wait(5))
        process.join(5)
        self.assertEqual(process.exitcode, 0)


class FormatAndArchitectureTests(unittest.TestCase):
    def test_all_seven_templates_accept_native_parsers_when_available(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            for name, text in engine.render(RESOURCES, engine.defaults(RESOURCES)).items():
                (path / name).write_text(text)
            engine.validate_outputs(path)

    def test_each_format_rejects_corruption(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            outputs = engine.render(RESOURCES, engine.defaults(RESOURCES))
            for name, text in outputs.items(): (path / name).write_text(text)
            for name in engine.FILES:
                with self.subTest(component=name):
                    (path / name).write_text('invalid @unknown@')
                    with self.assertRaises(ValueError): engine.validate_outputs(path, native=False)
                    (path / name).write_text(outputs[name])

    def test_runtime_cannot_target_git_checkout(self):
        with patch.dict(os.environ, XDG_CACHE_HOME=str(ROOT / '.cache')):
            with self.assertRaisesRegex(ValueError, 'outside the Git checkout'): engine.Engine(RESOURCES)

    def test_core_is_platform_independent_and_components_never_use_raw_indices(self):
        text = (RESOURCES / 'engine.py').read_text()
        self.assertNotIn('apt-get', text)
        self.assertNotIn('dpkg', text)
        self.assertNotIn('systemctl', text)
        for template in (RESOURCES / 'templates').iterdir():
            self.assertNotRegex(template.read_text(), r'color\d+\s*\}\}')
        from source_layout import mapped_files
        self.assertTrue(any(source == RESOURCES / 'engine.py' and target == Path('hyprixe/theme/engine.py')
                            for source, _, target in mapped_files()))

    @unittest.skipUnless(shutil.which('wallust'), 'real Wallust 3.5.1 optional in source-only environments')
    def test_real_pinned_wallust_on_all_six_synthetic_images(self):
        with tempfile.TemporaryDirectory(prefix='hyprixe real wallust ') as folder:
            root = Path(folder)
            with patch.dict(os.environ, XDG_CACHE_HOME=str(root / 'cache'), XDG_STATE_HOME=str(root / 'state')):
                runtime = engine.Engine(RESOURCES)
                if runtime.version() != engine.WALLUST_VERSION:
                    self.skipTest('real extraction needs Wallust 3.5.1; installed checks enforce the pin')
                for name, color in SWATCHES.items():
                    with self.subTest(image=name):
                        image = fixture(root / (name + '.png'), color)
                        stage = root / name; stage.mkdir()
                        try:
                            extracted = runtime.extract(image, stage)
                        except ValueError:
                            # Extremely pale or monochrome input may not contain
                            # enough chroma for Wallust; exercise the real fallback.
                            meta = runtime.transact(image, enabled=True, apply=False, reload=False, force=True)
                            self.assertEqual(meta['source'], 'fallback')
                            palette = json.loads((runtime.current / 'palette.json').read_text())
                        else:
                            palette = engine.normalize(extracted, runtime.base)
                        engine.validate_palette(palette, runtime.base)


if __name__ == '__main__': unittest.main()

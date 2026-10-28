"""Launcher button and preview rendering support for the pinned Rofi 2.0.0 build.

Stock drun interprets custom actions as mode switches. Reserve three otherwise
unused actions only when our application launcher explicitly opts in. Other
Rofi invocations keep upstream behaviour, including dmenu's return codes.
The preview cover property changes only image sizing, not launcher actions.
"""
import argparse
from pathlib import Path
import sys

MARKER = '-hyprixe-launcher'
COVER_MARKER = 'hyprixe-preview-cover'
ORIGINAL = 'ModeMode retv = mode_result(sw, mretv, &input, selected_line);'
REPLACEMENT = '''ModeMode retv;
    unsigned int hyprixe_action = mretv & MENU_LOWER_MASK;
    if (find_arg("-hyprixe-launcher") >= 0 &&
        (mretv & MENU_CUSTOM_COMMAND) &&
        hyprixe_action >= 16 && hyprixe_action <= 18) {
      /* Return to the caller after closing the view; never execute shell text. */
      rofi_set_return_code(10 + hyprixe_action - 16);
      retv = MODE_EXIT;
    } else {
      retv = mode_result(sw, mretv, &input, selected_line);
    }'''
HOVER_ORIGINAL = 'RofiCursorType cursor_type = rofi_view_resolve_cursor(state, x, y);'
HOVER_REPLACEMENT = '''/* Hyprixe custom buttons have no hover state in stock Rofi 2.0.0. */
  if (find_arg("-hyprixe-launcher") >= 0) {
    widget *target = widget_find_mouse_target(
        WIDGET(state->main_window), WIDGET_TYPE_EDITBOX, x, y);
    if (target && rofi_theme_get_string(target, "action", NULL) == NULL) {
      target = NULL;
    }
    if (target != state->hyprixe_hover) {
      if (state->hyprixe_hover) {
        widget_set_state(state->hyprixe_hover, NULL);
      }
      state->hyprixe_hover = target;
      if (target) {
        widget_set_state(target, "hover");
      }
      rofi_view_queue_redraw();
    }
  }
  RofiCursorType cursor_type = rofi_view_resolve_cursor(state, x, y);'''
ENTER_ORIGINAL = '  wayland_cursor_update_for_seat(self);\n}'
ENTER_REPLACEMENT = '''  wayland_cursor_update_for_seat(self);
  if (find_arg("-hyprixe-launcher") >= 0) {
    RofiViewState *state = rofi_view_get_active();
    if (state) {
      self->button.x = wl_fixed_to_int(x);
      self->button.y = wl_fixed_to_int(y);
      self->motion.x = self->button.x;
      self->motion.y = self->button.y;
      rofi_view_handle_mouse_motion(state, self->button.x, self->button.y, FALSE);
    }
  }
}'''
LEAVE_ORIGINAL = '''    wayland->cursor.frame_cb = NULL;
  }
}

static void wayland_pointer_motion'''
LEAVE_REPLACEMENT = '''    wayland->cursor.frame_cb = NULL;
  }
  if (find_arg("-hyprixe-launcher") >= 0) {
    RofiViewState *state = rofi_view_get_active();
    if (state) {
      rofi_view_handle_mouse_motion(state, -1, -1, FALSE);
    }
    self->motion.x = -1;
    self->motion.y = -1;
  }
}

static void wayland_pointer_motion'''
COVER_ORIGINAL = '''cairo_surface_t *img = rofi_icon_fetcher_get(p->value.image.surface_id);

      if (img != NULL) {'''
COVER_REPLACEMENT = '''cairo_surface_t *img = rofi_icon_fetcher_get(p->value.image.surface_id);

      /* Keep height cropping, but cover wide launcher previews without tiling. */
      if (img != NULL && rofi_theme_get_boolean(wid, "hyprixe-preview-cover", FALSE) &&
          p->value.image.scaling == ROFI_SCALE_HEIGHT &&
          cairo_image_surface_get_width(img) < wid->w * (int)scale) {
        img = rofi_icon_fetcher_get(rofi_icon_fetcher_query_advanced(
            p->value.image.url, wid->w, -1));
      }

      if (img != NULL) {'''
PATCHES = (
    ('source/rofi.c', ORIGINAL, REPLACEMENT),
    ('include/view-internal.h', 'box *main_window;', 'box *main_window;\n  widget *hyprixe_hover;'),
    ('source/view.c', HOVER_ORIGINAL, HOVER_REPLACEMENT),
    ('source/wayland/display.c', '#include "settings.h"', '#include "settings.h"\n#include "helper.h"'),
    ('source/wayland/display.c', ENTER_ORIGINAL, ENTER_REPLACEMENT),
    ('source/wayland/display.c', LEAVE_ORIGINAL, LEAVE_REPLACEMENT),
    ('source/theme.c', COVER_ORIGINAL, COVER_REPLACEMENT),
)


def patch_source(source):
    changes = {}
    for name, original, replacement in PATCHES:
        path = Path(source) / name
        text = changes.get(path, None)
        if text is None:
            text = path.read_text()
        if replacement in text:
            continue
        if (name == 'source/rofi.c' and MARKER in text) or text.count(original) != 1:
            raise ValueError(f'Unsupported Rofi source: expected the pinned 2.0.0 content in {name}')
        changes[path] = text.replace(original, replacement)
    for path, text in changes.items():
        path.write_text(text)


def has_launcher_actions(executable):
    if not executable:
        return False
    try:
        return MARKER.encode() in Path(executable).read_bytes()
    except OSError:
        return False


def has_launcher_cover(executable):
    """Detect the visual-only preview fix without mistaking old actions for it."""
    if not executable:
        return False
    try:
        return COVER_MARKER.encode() in Path(executable).read_bytes()
    except OSError:
        return False


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--patch', required=True, type=Path)
    args = parser.parse_args()
    try:
        patch_source(args.patch)
    except (OSError, ValueError) as exc:
        print(f'ERROR: Rofi launcher preparation: {exc}', file=sys.stderr)
        sys.exit(1)

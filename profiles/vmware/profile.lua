-- Optional software rendering for vmwgfx guests; never loaded in native mode.
hl.env("LIBGL_ALWAYS_SOFTWARE", "1")
hl.env("MESA_LOADER_DRIVER_OVERRIDE", "llvmpipe")
hl.env("GALLIUM_DRIVER", "llvmpipe")
hl.config({ cursor = { no_hardware_cursors = true } })

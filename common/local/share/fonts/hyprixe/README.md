# Hyprixe Debian glyph

One-glyph subset (U+F306, Debian) of font-logos 1.4.0.
Source: https://github.com/lukas-w/font-logos and the published npm package.
Upstream font SHA256: `b1368c1cfef326907efb4a76f2f5c1948ccc2f388434ce23473bf50066784de4`.

Renamed to Hyprixe Debian to isolate it from other fonts. Only Waybar's new
Debian logo uses this family; the existing bar typography is unchanged.
The included Unlicense applies to the font. Debian is a trademark of its
respective owner; the glyph identifies the installed Debian distribution.

The font is installed below the user data/fonts directory by the scoped
Waybar deployment. No system font is replaced. FontTools is a maintainer
subsetting tool, not an installation/runtime dependency.

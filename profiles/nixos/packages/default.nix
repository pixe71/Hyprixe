{ pkgs }:

let
  wallustVersion = "3.5.1";
  wallustSource = pkgs.fetchurl {
    name = "wallust-${wallustVersion}.tar.gz";
    url = "https://static.crates.io/crates/wallust/wallust-${wallustVersion}.crate";
    hash = "sha256-Ra/ha8jBTath/yrPiFA0ZkprkXyi6odP8k61EH0xHsw=";
  };
  rofiUnwrapped = pkgs.rofi-unwrapped.overrideAttrs (old: {
    nativeBuildInputs = old.nativeBuildInputs ++ [ pkgs.python3 ];
    postPatch = (old.postPatch or "") + ''
      patchRoot=$(mktemp -d)
      install -Dm644 ${../../../common/compat/rofi_launcher.py} "$patchRoot/common/compat/rofi_launcher.py"
      install -Dm644 ${../../../scripts/source_layout.py} "$patchRoot/scripts/source_layout.py"
      python3 -B "$patchRoot/common/compat/rofi_launcher.py" --patch .
      # Image jobs can still be decoding a launcher preview when Escape
      # closes the window. Finish active jobs before releasing their data.
      substituteInPlace source/view.c \
        --replace-fail "Discard all unprocessed jobs and don't wait for current jobs in execution" \
          "Discard unprocessed jobs and wait for active jobs to finish" \
        --replace-fail 'g_thread_pool_free(tpool, TRUE, FALSE);' 'g_thread_pool_free(tpool, TRUE, TRUE);'
      substituteInPlace source/rofi.c \
        --replace-fail '  rofi_view_workers_finalize();' "" \
        --replace-fail 'static void cleanup(void) {' 'static void cleanup(void) {
        rofi_view_workers_finalize();'
    '';
  });
in
{
  wallust = pkgs.wallust.overrideAttrs (_: {
    version = wallustVersion;
    src = wallustSource;
    cargoDeps = pkgs.rustPlatform.fetchCargoVendor {
      src = wallustSource;
      name = "wallust-${wallustVersion}-vendor";
      hash = "sha256-HqHfq5JyB4xTOQEbn6+MTCWOoRcQVotSP4XDcf7kcf0=";
    };
    postPatch = ''
      # The published archive has no Git metadata. Report the release version
      # rather than the fallback VERGEN_IDEMPOTENT_OUTPUT text.
      substituteInPlace build.rs \
        --replace-fail 'let s = format!(r#""{} {}""#, clap::crate_version!(), version());' \
        'let s = format!("{:?}", clap::crate_version!());'
    '';
  });

  rofi = pkgs.rofi.override { rofi-unwrapped = rofiUnwrapped; };

  waybar = (pkgs.waybar.override { cavaSupport = false; }).overrideAttrs (old: {
    version = "0.16.0";
    src = pkgs.fetchFromGitHub {
      owner = "Alexays";
      repo = "Waybar";
      tag = "0.16.0";
      hash = "sha256-mHBaRnquV9tSt8FuaAU9/HG7B8gditQX6p3NgwiLmMY=";
    };
    patches = (old.patches or [ ]) ++ [ ./waybar-backlight.patch ];
    mesonFlags = old.mesonFlags ++ [ (pkgs.lib.mesonEnable "wwan" false) ];
  });
}

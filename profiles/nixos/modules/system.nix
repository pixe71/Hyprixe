{ config, lib, ... }:

{
  imports = [ ./sddm.nix ];

  options.programs.hyprixe.enable = lib.mkEnableOption "the Hyprixe Hyprland session";

  config = lib.mkIf config.programs.hyprixe.enable {
    programs.hyprland = {
      enable = true;
      withUWSM = true;
    };
    # programs.hyprlock.enable would also start NixOS's Hypridle unit.
    security.pam.services.hyprlock = { };
  };
}

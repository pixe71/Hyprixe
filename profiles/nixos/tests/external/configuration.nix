{ ... }:

{
  networking.hostName = "aster";
  system.stateVersion = "25.11";
  users.users.pilot = {
    isNormalUser = true;
    home = "/home/pilot-d1";
  };
  users.users.observer.isNormalUser = true;

  home-manager.useGlobalPkgs = true;
  home-manager.useUserPackages = true;
  home-manager.users.pilot = {
    home.stateVersion = "25.11";
    home.file.".existing-home-file".text = "Owned by the host\n";
    xdg = {
      enable = true;
      configHome = "/home/pilot-d1/settings";
      dataHome = "/home/pilot-d1/.data-fixture";
      cacheHome = "/home/pilot-d1/.cache-fixture";
      stateHome = "/home/pilot-d1/.state-fixture";
    };
  };
  home-manager.users.observer.home.stateVersion = "25.11";
}

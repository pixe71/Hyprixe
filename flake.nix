{
  description = "Hyprixe NixOS profile";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-26.05";
    home-manager = {
      url = "github:nix-community/home-manager/release-26.05";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    {
      self,
      nixpkgs,
      home-manager,
    }:
    let
      system = "x86_64-linux";
      tests = import ./profiles/nixos/tests {
        inherit nixpkgs home-manager system;
        hyprixe = self;
      };
    in
    {
      nixosModules.default = import ./profiles/nixos/modules/system.nix;
      homeManagerModules.default = import ./profiles/nixos/modules/home.nix;

      checks.${system} = tests.checks;
      packages.${system} = (import ./profiles/nixos/packages {
        pkgs = nixpkgs.legacyPackages.${system};
      }) // { session-vm = tests.sessionVM; };
    };
}

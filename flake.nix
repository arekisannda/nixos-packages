{
  description = "Custom Packages";

  inputs = {
    flake-parts.url = "github:hercules-ci/flake-parts";
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs =
    inputs@{ flake-parts, ... }:
    flake-parts.lib.mkFlake { inherit inputs; } {
      systems = [
        "x86_64-linux"
        "aarch64-linux"
        "aarch64-darwin"
        "x86_64-darwin"
      ];

      perSystem =
        { pkgs, ... }:

        let
          inherit (builtins)
            readDir
            listToAttrs
            attrValues
            mapAttrs
            ;

          packagesDir = ./pkgs;
          custompkgs = readDir packagesDir;

          makePackage =
            name: type:
            let
              pkgName =
                if type == "regular" && builtins.match ".*\\.nix$" name != null then
                  builtins.replaceStrings [ ".nix" ] [ "" ] name
                else
                  name;
            in
            {
              name = pkgName;
              value = pkgs.callPackage (packagesDir + "/${name}") { };
            };
        in
        {
          packages = listToAttrs (attrValues (mapAttrs makePackage custompkgs));

          devShells.default = pkgs.mkShell {
            name = "nix packages development shell";
            buildInputs = with pkgs; [
              gitleaks
              statix
              deadnix
            ];

            DEV_SHELL = "pkgs";

            shellHook = "";
          };
        };
    };
}

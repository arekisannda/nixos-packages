{
  description = "Custom Packages";

  inputs = {
    flake-parts.url = "github:hercules-ci/flake-parts";
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    nixpkgs-emacs.url = "github:NixOS/nixpkgs/nixos-unstable";

    swaydm.url = "github:arekisannda/sway-display-manager/?ref=v0.1.0";
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
        {
          pkgs,
          inputs',
          system,
          nixpkgs-emacs,
          ...
        }:

        let
          inherit (builtins)
            readDir
            listToAttrs
            attrValues
            mapAttrs
            ;

          packagesDir = ./packages;
          custompkgs = readDir packagesDir;

          makeInputPkg =
            input:
            import input {
              inherit system;
              config.allowUnfree = true;
            };

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
              value =
                let
                  overrideCall = packagesDir + "/${name}/call.nix";
                in
                if (builtins.pathExists overrideCall) then
                  import overrideCall { inherit nixpkgs-emacs; }
                else
                  pkgs.callPackage (packagesDir + "/${name}") { };
            };
        in
        {
          _module.args.pkgs = makeInputPkg inputs.nixpkgs;
          _module.args.nixpkgs-emacs = makeInputPkg inputs.nixpkgs-emacs;

          packages = listToAttrs (attrValues (mapAttrs makePackage custompkgs)) // {
            swaydm = inputs'.swaydm.packages.default;
          };

          devShells.default = pkgs.mkShell {
            name = "nix packages development shell";
            buildInputs = with pkgs; [
              gitleaks
              statix
              deadnix

              # python dependency
              isort
            ];

            DEV_SHELL = "pkgs";

            shellHook = "";
          };
        };
    };
}

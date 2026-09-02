#!/usr/bin/env -S nix repl -f

let
  flake = builtins.getFlake (toString ./.);
  inherit (flake.inputs) nixpkgs;
  system = "x86_64-linux";
  pkgs = nixpkgs.legacyPackages.${system};
in
{
  inherit flake pkgs;
}
// builtins
// nixpkgs.lib
// flake.packages.${system}
# pythonSet
// (pkgs.callPackage ./modules/packages/_lib.nix {
  inherit (flake.inputs) uv2nix pyproject-nix pyproject-build-systems;
  workspaceRoot = ./.;
})

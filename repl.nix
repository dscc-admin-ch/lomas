#!/usr/bin/env -S nix repl -f

let
  flake = builtins.getFlake (toString ./.);
  inherit (flake.inputs) nixpkgs;
  system = "x86_64-linux";
  pkgs = nixpkgs.legacyPackages.${system};
  lib = pkgs.lib;
in
{
  inherit flake pkgs;
}
// builtins
// nixpkgs.lib
// flake.packages.${system}
// (import ./devenv/lib.nix {
  inherit (flake.inputs) uv2nix pyproject-nix pyproject-build-systems;
  inherit pkgs lib;
  workspaceRoot = ./.;
})

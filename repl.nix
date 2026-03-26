#!/usr/bin/env -S nix repl -f

let
  flake = builtins.getFlake (toString ./.);
  system = "x86_64-linux";
  pkgs = flake.inputs.nixpkgs.legacyPackages.${system}.pkgs;
in
{ inherit flake; } // flake // flake.packages.${system} // builtins // pkgs // pkgs.lib

{ inputs, ... }:
{
  imports = [
    # https://flake.parts/options/flake-parts-touchup.html
    inputs.flake-parts.flakeModules.touchup
  ];
}

## They see me flakin'


`nix flake show` <- "the fuck we have here ?"

`nix develop .#py312 [of py313/py314]` <- Hoping in a (dev)shell with lomas python package in 3.[12|13|14]

### Using the integration test to have a look at generated units

zb. from `./repl.nix`
the config of the (systemd) lomas service set:
`:p flake.checks.x86_64-linux.load.containers.server.systemd.services.lomas`

which will be **rendered** once build
`:b flake.checks.x86_64-linux.load.containers.server.system.build.toplevel`

(or one-shot this from the repo root `nix eval --raw .#checks.x86_64-linux.load.containers.server.system.build.toplevel --apply 'out: builtins.readFile "${out}/etc/systemd/system/lomas.service"'`)

### formatting / treefmt

treefmt-nix wrap treefmt to format the whole project repo.

- When all works: just spam `nix fmt` (fancy alias of `nix formatter run`)
- to see what's up: `nix formatter build` to see the underlying `treefmt` bin/config
- since `nix fmt` just wraps treefmt call, all options are avail through `nix fmt -- [treefmt opt]`
  - like `nix fmt -- --ci` / `nix fmt -- [-c][-v[v]]`

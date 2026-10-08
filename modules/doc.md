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

## TODO

- provide a dockerfile+package+module see @https://codeberg.org/Blooym/porxie
- use `writeShellApplication` (runtimeInputs) [ref](https://nixos.org/manual/nixpkgs/unstable/#trivial-builder-writeShellApplication)
- Allow for raw(er) setup ? current absolute min:
  1. `lomas start --worker-api-key "deadbeef" --authenticator.authentication-type free_pass`
  2. `lomas work --worker-api-key "deadbeef" --authenticator.authentication-type free_pass`
  3. ` LOMAS_ADMIN_external_url="http://localhost:48080" LOMAS_SERVER_authenticator__authentication_type=free_pass LOMAS_SERVER_worker_api_key="deadbeef" pytest -v server/lomas_server/tests/test_worker.py`

# Structure

We use **deferred module composition** via flake-parts + import-tree evaluated in the following order:

1. nixpkgs.lib.evalModules does the lazy composition (`{config, ...}: ...` config is the reference to the final evaluation once the eval is the fixpoint)
2. flake-parts wraps the evalmodules adding/fitting flake conventions (`perSystem`/`flakeModules`/etc.)
3. import-tree imports all `.nix` files and aggregates them into defferredModule composition

Note: why config-merging fixpoint is unique ? (Scott-continuous of curry & apply ?)

{
  pkgs,
  lib,
  uv2nix,
  pyproject-nix,
  pyproject-build-systems,
  workspaceRoot,
  python3,
  ...
}:
let
  inherit (pkgs.callPackages pyproject-nix.build.util { }) mkApplication;
  fs = lib.fileset;
  # unfortunately devenv currently pull the fileset dependency recursively
  # .devenv/input-paths.txt contains
  # [...]
  # <root>/lomas
  # <root>/lomas/core/lomas_core
  # [...]
  # etc. which trigger reevaluation for ANY changes whatsoever
  devenvCorrectlyHandleFs = false;
  hacks = pkgs.callPackage pyproject-nix.build.hacks { };
in
rec {
  workspace = uv2nix.lib.workspace.loadWorkspace { inherit workspaceRoot; };

  uvOverlay = workspace.mkPyprojectOverlay {
    sourcePreference = "wheel";
  };

  editableOverlay = workspace.mkEditablePyprojectOverlay {
    root = "$REPO_ROOT";
  };

  editableSrcFilteringOverlay = final: prev: {
    lomas = prev.lomas.overrideAttrs (old: {
      src =
        if devenvCorrectlyHandleFs then
          fs.toSource rec {
            root = workspaceRoot;
            fileset = fs.unions [
              (root + "/pyproject.toml")
              (root + "/core/lomas_core/__init__.py")
              (root + "/client/lomas_client/__init__.py")
              (root + "/server/lomas_server/__init__.py")
            ];
          }
        else
          pkgs.runCommand "lomas-src" { } ''
            mkdir -p $out/lomas
            cp ${../pyproject.toml} $out/pyproject.toml
            touch $out/lomas/__init__.py
            for dep in core client server; do
              mkdir -p $out/$dep/lomas_$dep
              touch $out/$dep/lomas_$dep/__init__.py
            done
          '';
    });
    lomas-core = prev.lomas-core.overrideAttrs (old: {
      src =
        if devenvCorrectlyHandleFs then
          fs.toSource rec {
            root = workspaceRoot + "/core";
            fileset = fs.unions [
              (root + "/pyproject.toml")
              (root + "/lomas_core/__init__.py")
            ];
          }
        else
          pkgs.runCommand "lomas-core-src" { } ''
            mkdir -p $out/lomas_core
            cp ${../core/pyproject.toml} $out/pyproject.toml
            touch $out/lomas_core/__init__.py
          '';
    });
    lomas-client = prev.lomas-client.overrideAttrs (old: {
      src =
        if devenvCorrectlyHandleFs then
          fs.toSource rec {
            root = workspaceRoot + "/client";
            fileset = fs.unions [
              (root + "/pyproject.toml")
              (root + "/lomas_client/__init__.py")
            ];
          }
        else
          pkgs.runCommand "lomas-client-src" { } ''
            mkdir -p $out/lomas_client
            cp ${../client/pyproject.toml} $out/pyproject.toml
            touch $out/lomas_client/__init__.py
          '';
    });
    lomas-server = prev.lomas-server.overrideAttrs (old: {
      src =
        if devenvCorrectlyHandleFs then
          fs.toSource rec {
            root = workspaceRoot + "/server";
            fileset = fs.unions [
              (root + "/pyproject.toml")
              (root + "/lomas_server/__init__.py")
            ];
          }
        else
          pkgs.runCommand "lomas-server-src" { } ''
            mkdir -p $out/lomas_server
            cp ${../server/pyproject.toml} $out/pyproject.toml
            touch $out/lomas_server/__init__.py
          '';
    });
  };

  # add missing setuptools build requirements to theses libs
  fixBuildSystemOverlay =
    final: prev:
    lib.genAttrs [ "pandoc" ] (
      name:
      prev.${name}.overrideAttrs (old: {
        nativeBuildInputs = old.nativeBuildInputs ++ final.resolveBuildSystem { setuptools = [ ]; };
      })
    );

  fixSmartnoiseSql = final: prev: {
    "antlr4-python3-runtime" = prev."antlr4-python3-runtime".overrideAttrs (old: {
      nativeBuildInputs = old.nativeBuildInputs ++ final.resolveBuildSystem { setuptools = [ ]; };
    });
    "smartnoise-sql" = prev."smartnoise-sql".overrideAttrs (old: {
      nativeBuildInputs = old.nativeBuildInputs ++ final.resolveBuildSystem { poetry-core = [ ]; };
    });
  };

  sslOverlay = final: prev: {
    certifi = hacks.nixpkgsPrebuilt {
      # nixpkgs certifi respect the ca-bundle from pkgs.cacert as well as NIX_SSL_CERT_FILE if set
      from = python3.pkgs.certifi;
      prev = prev.certifi;
    };
  };

  pythonSets = (pkgs.callPackage pyproject-nix.build.packages { python = python3; }).overrideScope (
    lib.composeManyExtensions [
      pyproject-build-systems.overlays.wheel
      uvOverlay
      fixBuildSystemOverlay
      fixSmartnoiseSql
      sslOverlay
      # diffprivlibOverlay
      # openDpOverlay
    ]
  );

  # Fix sklearn.linear_model.LogisticRegression multi_class argument
  # deprecated in 1.7.2 and removed in 1.8.0
  diffprivlibOverlay = final: prev: {
    diffprivlib = prev.diffprivlib.overrideAttrs (old: {
      postInstall = ''
        pushd $out/lib/python*/site-packages/diffprivlib >/dev/null
        # python wheel sources
        substituteInPlace models/logistic_regression.py --replace-fail "multi_class='ovr'," ""
        popd >/dev/null
      '';
    });
  };

  # OpenDP from source
  openDpOverlay = final: prev: {
    opendp = (prev.opendp.override { sourcePreference = "sdist"; }).overrideAttrs (old: {
      # We need the Rust toolchains (as well as perl)
      buildInputs = (old.buildInputs or [ ]) ++ [ pkgs.openssl ];
      nativeBuildInputs = old.nativeBuildInputs ++ [
        (final.resolveBuildSystem {
          setuptools = [ ];
          setuptools-rust = [ ];
        })
        pkgs.rustPlatform.cargoSetupHook
        pkgs.cargo
        pkgs.rustc
        pkgs.perl # required by openssl configure
      ];
      # missing Cargo.lock
      cargoRoot = "src/opendp/rust";
      patches = [ ./add-Cargo.lock.patch ];
      cargoDeps = pkgs.rustPlatform.importCargoLock {
        lockFile = ./Cargo.lock;
      };
      # Applying source-customization
      postPatch = ''
        substituteInPlace setup.cfg --replace-fail polars==1.32.0 polars==1.36.1
        substituteInPlace src/opendp/mod.py --replace-fail 1.32.0 1.36.1
      '';
    });
  };

  pythonSet = pythonSets.overrideScope (
    lib.composeManyExtensions [
      editableOverlay
      editableSrcFilteringOverlay
    ]
  );

  lomasEnv = pythonSets.pythonPkgsHostHost.mkVirtualEnv "lomas-env" workspace.deps.default;
  lomasEnvDev = pythonSet.mkVirtualEnv "lomas-dev-env" workspace.deps.all;
  lomasClient = pythonSets.pythonPkgsHostHost.mkVirtualEnv "lomas-client" { lomas-client = [ ]; };
  lomasService = mkApplication {
    venv = lomasEnv;
    package = pythonSet.lomas-server;
  };
}

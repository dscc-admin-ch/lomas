{
  perSystem = { pkgs, ... }: {
    treefmt = {
      projectRootFile = "flake.nix";
      programs = {
        # Nix (.nix)
        nixfmt = {
          enable = true;
          width = 120;
        };
        statix.enable = true;
        deadnix.enable = true;
        deadnix.no-lambda-pattern-names = true; # don't even ...

        # Yaml/Markdown/etc (.yaml/.json/.md)
        prettier.enable = true;

        # Toml key sorting (.toml)
        toml-sort.enable = true;

        # Bash (.sh/.bash)
        shellcheck.enable = true;

        # Python (.py/.pyi)
        ruff.check = true;
        ruff.format = true;

        mypy = {
          enable = true;
          directories."" = {
            extraPythonPackages = [
              pkgs.python3.pkgs.returns
              pkgs.python3.pkgs.pydantic
            ];
          };
        };

        # Notebook (.ipynb)
        nbstripout.enable = true;
      };

      settings.formatter = {
        shellcheck.options = [
          "-s"
          "bash"
        ];

        ruff-check.options = [
          "--config"
          "pyproject.toml"
        ];
        # Ensure ruff check then format ordering
        ruff-check.priority = 1;
        ruff-format.priority = 2;

        # helm template are (ofc) invalid yaml
        prettier.excludes = [ "deploy/charts/*" ];

        nbstripout.options = [
          "--keep-output"
          "--drop-empty-cells"
        ];
      };
    };
  };
}

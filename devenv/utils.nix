lib: {
  wrapScript =
    script:
    let
      pwd = if script ? pwd then "$DEVENV_ROOT/${script.pwd}" else "$DEVENV_ROOT";
    in
    {
      exec = ''
        set -e
        pushd "${pwd}" > /dev/null
        echo "[INFO]: Changed directory to ${pwd}"
        ${script.exec}
        popd > /dev/null
      '';
    };

  # transform attribute set into pydantic wierd list-parseable format:
  # Examples
  ## listToPydanticEnvVar "myPrefix" [{user = "alice"; pin = 1234} {user = "bob"; pin = 789}];
  # => {
  # myPrefix__0__USER = "alice";
  # myPrefix__0__PIN = 1234;
  # myPrefix__1__USER = "obb";
  # myPrefix__1__PIN = 789;
  # }
  listToPydanticEnvVar =
    prefix: listOfAttrSets:
    lib.mergeAttrsList (
      lib.imap0 (
        idx: (lib.concatMapAttrs (name: value: { "${prefix}__${toString idx}__${lib.toUpper name}" = value; }))
      ) listOfAttrSets
    );

  clientIdSecret = lib.types.submodule {
    options.client_id = lib.mkOption {
      type = lib.types.str;
    };
    options.client_secret = lib.mkOption {
      type = lib.types.str;
    };
  };
}

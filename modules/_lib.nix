{ lib, ... }:
{
  portStr = with lib.types; coercedTo port toString str;

  clientIdSecret = lib.types.submodule {
    options.client_id = lib.mkOption {
      type = lib.types.str;
    };
    options.client_secret = lib.mkOption {
      type = lib.types.str;
    };
    options.redirect_uri = lib.mkOption {
      default = null;
      type = lib.types.nullOr lib.types.str;
    };
  };
}

{
  pkgs,
  lib,
  config,
  ...
}:
let
  cfg = config.lomas.caddy;

  inherit (lib)
    types
    mkIf
    mkOption
    mkEnableOption
    ;

  Caddyfile-formatted =
    pkgs.runCommand "Caddyfile-formatted"
      {
        Caddyfile = config.services.caddy.config;
        passAsFile = [ "Caddyfile" ];
      }
      ''
        mkdir -p $out
        cp --no-preserve=mode $CaddyfilePath $out/Caddyfile
        ${lib.getExe cfg.package} fmt --overwrite $out/Caddyfile
      '';
in
{
  options.lomas.caddy = {
    enable = mkEnableOption "Enable Caddy Reverse Proxy";

    package = mkOption {
      type = types.package;
      default = pkgs.caddy.withPlugins {
        plugins = [ "github.com/greenpau/caddy-security@v1.1.31" ];
        hash = "sha256-hKPBEGm3wV6t3t1MGqO/yrJIGZf5BhUNlF1erOqW1Wc=";
      };
    };

    debug = mkOption {
      type = types.bool;
      default = false;
      description = "Enable caddy debug log/mode";
    };

    vhost = mkOption {
      type = types.str;
      default = ":8080";
      description = "RProxy virtual Host";
    };
  };

  config = mkIf cfg.enable {
    # add caddy in our env, allows to debug with: caddy run --config $Caddyfile
    packages = [ cfg.package ];
    env.Caddyfile = "${Caddyfile-formatted}/Caddyfile";

    services.caddy = {
      enable = true;
      package = cfg.package;
      config = ''
        {
          debug ${if cfg.debug then "on" else "off"}
          auto_https disable_redirects

          order authenticate before respond
          order authorize before basicauth

          security {
            oauth identity provider keycloak {
              driver generic
              delay_start 10
              retry_attempts 5
              retry_interval 10
              realm ${config.lomas.realm}
              client_id ${config.env.LOMAS_KC_SETUP_LOMAS_GATEWAY_CLIENT_ID}
              client_secret ${config.env.LOMAS_KC_SETUP_LOMAS_GATEWAY_CLIENT_SECRET}
              scopes openid email profile
              metadata_url ${config.env.LOMAS_CLIENT_KEYCLOAK_URL}/realms/lomas/.well-known/openid-configuration
            }

            authentication portal kcportal {
              crypto default token lifetime 3600
              crypto key sign-verify {env.JWT_SHARED_KEY}
              enable identity provider keycloak
              # cookie domain localhost
              ui {
                links {
                  "Admin Dashboard" ${config.env.LOMAS_GATEWAY_URL}${config.lomas.dashboard.baseUrl} icon "las la-star"
                  "Swagger" ${config.env.LOMAS_GATEWAY_URL}/api/docs icon "las la-star"
                }
              }
              transform user {
                match origin ${config.lomas.realm}
                action add role authp/user
              }
            }

            authorization policy kcpolicy {
              set auth url ${config.env.LOMAS_KC_SETUP_LOMAS_GATEWAY_URL}
              allow roles authp/admin authp/user
              crypto key verify {env.JWT_SHARED_KEY}
            }
          }

        }

        (security) {
          # Unusual URL rewrite
          try_files {path} {path}/ /index.*
          # deny all access to these folders
          @denied_folders path_regexp /(\.github|cache|bin|logs|backup.*|test.*|content|core|image.*|js|css|php|config|lib|assets|rel|priv|tracker)/.*$
          respond @denied_folders "Access denied" 403
          # deny running scripts inside core system folders
          @denied_system_scripts path_regexp /(core|content|test|system|vendor)/.*\.(txt|xml|md|html|yaml|php|pl|py|cgi|twig|sh|bat|yml|js)$
          respond @denied_system_scripts "Access denied" 403
          # deny running scripts inside user folder
          @denied_user_folder path_regexp /user/.*\.(txt|md|yaml|php|pl|py|cgi|twig|sh|bat|yml|js)$
          respond @denied_user_folder "Access denied" 403
          # deny access to specific files in the root folder
          @denied_root_folder path_regexp /(index.php.*|wp-admin.php|wp-login.php|wp-config.php.*|xmlrpc.php|config.production.json|config.development.json|index.js|package.json|renovate.json|.*lock|mix.*|ghost.js|startup.js|\.editorconfig|\.eslintignore|\.eslintrc.json|\.gitattributes|\.gitignore|\.gitmodules|\.npmignore|Gruntfile.js|LICENSE|MigratorConfig.js|LICENSE.txt|composer.lock|composer.json|nginx.conf|web.config|htaccess.txt|\.htaccess)
          respond @denied_root_folder "Access denied" 403
          # block bad crawlers
          @badbots header User-Agent "aesop_com_spiderman, alexibot, backweb, batchftp, bigfoot, blackwidow, blowfish, botalot, buddy, builtbottough, bullseye, cheesebot, chinaclaw, cosmos, crescent, curl, custo, da, diibot, disco, dittospyder, dragonfly, drip, easydl, ebingbong, erocrawler, exabot, eyenetie, filehound, flashget, flunky, frontpage, getright, getweb, go-ahead-got-it, gotit, grabnet, grafula, harvest, hloader, hmview, httplib, humanlinks, ilsebot, infonavirobot, infotekies, intelliseek, interget, iria, jennybot, jetcar, joc, justview, jyxobot, kenjin, keyword, larbin, leechftp, lexibot, lftp, libweb, likse, linkscan, linkwalker, lnspiderguy, lwp, magnet, mag-net, markwatch, memo, miixpc, mirror, missigua, moget, nameprotect, navroad, backdoorbot, nearsite, netants, netcraft, netmechanic, netspider, nextgensearchbot, attach, nicerspro, nimblecrawler, npbot, openfind, outfoxbot, pagegrabber, papa, pavuk, pcbrowser, pockey, propowerbot, prowebwalker, psbot, pump, queryn, recorder, realdownload, reaper, reget, true_robot, repomonkey, rma, internetseer, sitesnagger, siphon, slysearch, smartdownload, snake, snapbot, snoopy, sogou, spacebison, spankbot, spanner, sqworm, superbot, superhttp, surfbot, asterias, suzuran, szukacz, takeout, teleport, telesoft, thenomad, tighttwatbot, titan, urldispatcher, turingos, turnitinbot, *vacuum*, vci, voideye, libwww-perl, widow, wisenutbot, wwwoffle, xaldon, xenu, zeus, zyborg, anonymouse, *zip*, *mail*, *enhanc*, *fetch*, *auto*, *bandit*, *clip*, *copier*, *master*, *reaper*, *sauger*, *quester*, *whack*, *picker*, *catch*, *vampire*, *hari*, *offline*, *track*, *craftbot*, *download*, *extract*, *stripper*, *sucker*, *ninja*, *clshttp*, *webspider*, *leacher*, *collector*, *grabber*, *webpictures*, *seo*, *hole*, *copyright*, *check*"
          respond @badbots "Access denied" 403
        }

        (public-header) {
          header {
            # disable FLoC tracking
            Permissions-Policy interest-cohort=()
            # enable HSTS
            Strict-Transport-Security max-age=31536000;
            # disable clients from sniffing the media type
            X-Content-Type-Options nosniff
            # clickjacking protection
            X-Frame-Options DENY
            # keep referrer data off of HTTP connections
            Referrer-Policy no-referrer-when-downgrade
            X-Clacks-Overhead "GNU Terry Pratchett"
          }
        }

        ${cfg.vhost} {
          import security
          import public-header

          @auth_route path /auth /auth/*

          route @auth_route {
            authenticate with kcportal
          }

          route {
            authorize with kcpolicy

            @api path /api /api/* /openapi.json
            handle @api {
              uri strip_prefix /api
              reverse_proxy http://${config.lomas.host}:${toString config.lomas.port}
            }

            @admin_dashboard path ${config.lomas.dashboard.baseUrl} ${config.lomas.dashboard.baseUrl}/*
            handle @admin_dashboard {
              reverse_proxy http://${config.lomas.dashboard.host}:${toString config.lomas.dashboard.port}
            }

            redir /grafana /grafana/
            handle_path /grafana/* {
              reverse_proxy http://${config.lomas.telemetry.services.grafana.host}:${toString config.lomas.telemetry.services.grafana.port}
            }

            redir /rabbitmq /rabbitmq/
            handle_path /rabbitmq* {
              reverse_proxy http://${config.lomas.rabbitmq.host}:${toString config.lomas.rabbitmq.portManagement}
            }

            route {
              redir * /auth/login
            }
          }

        }
      '';
    };
  };
}

{
  pkgs,
  env,
  postgres_port,
  postgres_addr,
  kc_http_port,
  kc_https_port,
  kc_management_port,
  kc_hostname,
  ...
}:
let
  cert = pkgs.runCommand "selfSignedCerts" { buildInputs = [ pkgs.openssl ]; } ''
    openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -nodes -subj '/CN=${kc_hostname}'
    mkdir -p $out
    cp key.pem cert.pem $out
  '';
  confFile = pkgs.writeText "keycloak.conf" ''
    db=postgres
    db-password=${env.KC_HOME_DIR}/db_password
    db-url-database=keycloak
    db-url-host=${postgres_addr}
    db-url-port=${toString postgres_port}
    db-url-properties=
    db-username=keycloak
    hostname=${kc_hostname}
    hostname-backchannel-dynamic=false
    http-relative-path=/
    https-certificate-file=${env.KC_HOME_DIR}/ssl/cert.pem
    https-certificate-key-file=${env.KC_HOME_DIR}/ssl/key.pem
    https-port=${toString kc_https_port}
    http-enabled=true
    http-port=${toString kc_http_port}
    http-management-port=${toString kc_management_port}
    https-management-certificate-file=
    https-management-certificate-key-file=
    health-enabled=true
  '';
  keycloakPkg = pkgs.keycloak.override { inherit confFile; };
in
{
  exec = ''
    set -o errexit -o pipefail -o nounset -o errtrace
    shopt -s inherit_errexit
    umask u=rwx,g=,o=

    mkdir -p ${env.KC_HOME_DIR}/themes
    ln -fs ${keycloakPkg}/providers ${env.KC_HOME_DIR}/
    ln -fs ${keycloakPkg}/lib ${env.KC_HOME_DIR}/

    install -D -m 0600 ${confFile} ${env.KC_HOME_DIR}/conf/keycloak.conf
    echo $KC_BOOTSTRAP_ADMIN_PASSWORD > ${env.KC_HOME_DIR}/db_password

    mkdir -p ${env.KC_HOME_DIR}/ssl
    cp -u ${cert}/{cert,key}.pem ${env.KC_HOME_DIR}/ssl/
    ${keycloakPkg}/bin/kc.sh --verbose start --optimized
  '';

  process-compose = {
    depends_on.postgres.condition = "process_healthy";
    readiness_probe = {
      http_get = {
        scheme = "http";
        host = "127.0.0.1";
        port = kc_management_port;
        path = "/health/ready";
      };
      initial_delay_seconds = 15;
      failure_threshold = 10;
    };
  };
}

{ config, kubenix, ... }:
{
  kubernetes.helm.releases.rabbitmq = {
    chart = kubenix.lib.helm.fetch {
      repo = "https://charts.bitnami.com/bitnami";
      chart = "rabbitmq";
      version = "15.5.0";
      sha256 = "sha256-eL5nzyA3U1kHSf9qNuL8U2s//WUHXA7nzuJnqnb1DIs=";
    };

    # arbitrary attrset passed as values to the helm release
    values = {
      namespaceOverride = config.namespace;
      global.security.allowInsecureImages = true;
      auth = {
        username = "guest";
        password = "guest";
        securePassword = true;
        updatePassword = false;
        existingPasswordSecret = "";
        existingSecretPasswordKey = "";
        tls.enabled = false;
      };
      containerPorts = {
        amqp = 5672;
        manager = 15672;
      };
      plugins = "rabbitmq_management rabbitmq_peer_discovery_k8s";
      extraConfiguration = ''
        heartbeat = 1800
      '';
      clustering.enabled = false;
      resourcesPreset = "small";

      pdb.create = false;
      serviceAccount.create = false;
      rbac.create = false;
      networkPolicy.enabled = false;
      metrics.enabled = false;
    };
  };

}

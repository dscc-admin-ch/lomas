{ config, kubenix, ... }:
{
  kubernetes.helm.releases.rustfs = {
    chart = kubenix.lib.helm.fetch {
      repo = "https://charts.rustfs.com/";
      chart = "rustfs";
      version = "0.0.90";
      sha256 = "sha256-QoBu6mNbuJeF8DZLTQfG+QhZP/mU2ZD/uq6TZbPbqpU=";
    };

    namespace = config.namespace;

    values = {
      mode.standalone.enabled = true;
      mode.distributed.enabled = false;
      storageclass.name = "rook-ceph-block";
      ingress.enabled = false;
    };
  };

}

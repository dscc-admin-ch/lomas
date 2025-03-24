# Helper script to setup lomas devenv into an onyxia vscode-python pod
# Usage from the outside, having .kube/config setup:
# cat scripts/onyxia.sh | kubectl exec --stdin <vscode-python-...> -- /bin/bash
# From a running container (vscode) terminal
# ./scripts/onyxia.sh

set -euo pipefail

export USER=${PROJECT_USER:-onyxia}

workdir=$(mktemp -d)
trap 'rm -rf "$workdir"' EXIT

add_config() {
  echo "$1" >> "$workdir/nix.conf"
}

add_config "max-jobs = auto"
add_config "experimental-features = nix-command flakes"
add_config "trusted-users = root ${USER}"
add_config "build-users-group ="
sudo mkdir -p /etc/nix
sudo chmod 0755 /etc/nix
sudo cp "$workdir/nix.conf" /etc/nix/nix.conf

sh <(curl -L https://nixos.org/nix/install) --yes --no-daemon --no-channel-add --nix-extra-conf-file "$workdir/nix.conf"

. $HOME/.nix-profile/etc/profile.d/nix.sh

NIX_BIN=$HOME/.nix-profile/bin

echo "fixing godamn .bashrc"
cat >> $HOME/.bashrc << EOF
export USER=${USER}
source $HOME/.nix-profile/etc/profile.d/nix.sh
EOF

echo "installing devenv & direnv"
$NIX_BIN/nix profile install nixpkgs#{dir,dev}env

if [[ -d "$WORKSPACE_DIR" && ! -e "$WORKSPACE_DIR/lomas" ]]; then
  echo "cloning lomas"
  cd "$WORKSPACE_DIR"
  git clone -b develop https://github.com/dscc-admin-ch/lomas
  cd lomas
  $NIX_BIN/direnv allow
  $NIX_BIN/devenv shell
elif [[ -e "$WORKSPACE_DIR/lomas" ]];then
  $NIX_BIN/direnv allow
  $NIX_BIN/devenv shell
fi

#!/usr/bin/env bash
set -euo pipefail

# simplify bootstraping script from https://github.com/cachix/install-nix-action/blob/master/install-nix.sh

# Create a temporary workdir
workdir=$(mktemp -d)
trap 'rm -rf "$workdir"' EXIT

# Configure Nix
add_config() {
  echo "$1" >> "$workdir/nix.conf"
}

# Set jobs to number of cores
add_config "max-jobs = auto"

# Allow nix profile / flake commands
add_config "experimental-features = nix-command flakes"

# Allow binary caches for user
add_config "trusted-users = root ${USER:-}"

# Nix installer flags
installer_options=(
  --no-channel-add
  --nix-extra-conf-file "$workdir/nix.conf"
)

# only use the nix-daemon settings if systemd is supported
if [[ -e /run/systemd/system ]]; then
  installer_options+=( --daemon )
else
  installer_options+=( --no-daemon )
  # "fix" the following error when running nix*
  # error: the group 'nixbld' specified in 'build-users-group' does not exist
  add_config "build-users-group ="
  sudo mkdir -p /etc/nix
  sudo chmod 0755 /etc/nix
  sudo cp "$workdir/nix.conf" /etc/nix/nix.conf
fi

echo "installer options: ${installer_options[*]}"

# There is --retry-on-errors, but only newer curl versions support that
curl_retries=5
while ! curl -sS -o "$workdir/install" -v --fail -L "${INPUT_INSTALL_URL:-https://releases.nixos.org/nix/nix-2.31.3/install}"
do
  sleep 1
  ((curl_retries--))
  if [[ $curl_retries -le 0 ]]; then
    echo "curl retries failed" >&2
    exit 1
  fi
done

sh "$workdir/install" "${installer_options[@]}"

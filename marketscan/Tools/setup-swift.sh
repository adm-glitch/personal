#!/usr/bin/env bash
#
# Installs the Swift toolchain needed to build and test Packages/MarketScanCore.
#
# Intended for the Claude Code cloud environment's **setup script**, where the
# result is cached (~7 days) so sessions start ready instead of re-downloading
# ~1 GB. Safe to run directly too; it is idempotent.
#
# Requires `download.swift.org` on the environment's network allowlist
# (docs/PLAN.md §2).
set -euo pipefail

SWIFT_VERSION="${SWIFT_VERSION:-6.3}"
DEST="${SWIFT_DEST:-/opt/swift}"

if [ -x "${DEST}/usr/bin/swift" ]; then
    echo "Swift already present at ${DEST}:"
    "${DEST}/usr/bin/swift" --version
    exit 0
fi

TARBALL="swift-${SWIFT_VERSION}-RELEASE-ubuntu24.04.tar.gz"
URL="https://download.swift.org/swift-${SWIFT_VERSION}-release/ubuntu2404/swift-${SWIFT_VERSION}-RELEASE/${TARBALL}"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

echo "==> Installing runtime dependencies"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq || true
apt-get install -y -qq --no-install-recommends \
    binutils git gnupg2 libc6-dev libcurl4-openssl-dev libedit2 \
    libgcc-13-dev libpython3-dev libsqlite3-0 libstdc++-13-dev \
    libxml2-dev libz3-dev pkg-config tzdata zlib1g-dev unzip

echo "==> Downloading Swift ${SWIFT_VERSION}"
curl -fL --retry 4 --retry-delay 3 --retry-all-errors \
     -o "${WORK}/${TARBALL}" "$URL"

echo "==> Extracting to ${DEST}"
rm -rf "$DEST"
mkdir -p "$DEST"
tar -xzf "${WORK}/${TARBALL}" --strip-components=1 -C "$DEST"

# Login shells pick this up; non-login shells still need the explicit export,
# so callers should not rely on it alone.
printf 'export PATH="%s/usr/bin:$PATH"\n' "$DEST" > /etc/profile.d/swift.sh
chmod +x /etc/profile.d/swift.sh

echo "==> Verifying"
"${DEST}/usr/bin/swift" --version
echo "==> Done. Add to PATH with: export PATH=\"${DEST}/usr/bin:\$PATH\""

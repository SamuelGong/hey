#!/usr/bin/env bash
set -euo pipefail

# Check if redis-server (Debian name) or redis (RHEL/Fedora service name) is already installed
if command -v redis-server >/dev/null 2>&1 || command -v redis-cli >/dev/null 2>&1; then
    echo "Redis is already installed."
    exit 0
fi

echo "Redis is not installed. Installing now..."

if [[ "$(uname -s)" == "Darwin" ]]; then
    # macOS
    if ! command -v brew >/dev/null 2>&1; then
        echo "Homebrew is not installed. Please install Homebrew first: https://brew.sh/"
        exit 1
    fi
    brew update
    brew install redis

elif [[ -r /etc/os-release ]]; then
    # Linux
    . /etc/os-release   # loads variables: ID, ID_LIKE, etc.

    # Helper: return 0 if $1 is contained in $ID or $ID_LIKE
    has_like() {
        local needle="${1,,}"             # argument lowercased
        local id_lc="${ID,,}"             # ID lowercased
        local like_lc="${ID_LIKE:-}"      # ID_LIKE lowercased (may be empty)
        [[ "$id_lc" == "$needle" ]] && return 0
        [[ "$like_lc" == *"$needle"* ]] && return 0
        return 1
    }

    if has_like debian || has_like ubuntu; then
        # Debian/Ubuntu
        sudo apt-get update
        sudo apt-get install -y redis-server

    elif has_like rhel || has_like centos || has_like fedora || has_like openeuler; then
        # RHEL/CentOS/AlmaLinux/Rocky/Fedora/openEuler
        PKG_MGR=""
        if command -v dnf >/dev/null 2>&1; then
            PKG_MGR="dnf"
        elif command -v yum >/dev/null 2>&1; then
            PKG_MGR="yum"
        fi
        if [[ -z "$PKG_MGR" ]]; then
            echo "Could not find yum/dnf on this system."
            exit 1
        fi

        # Optional: enable EPEL on older RHEL/CentOS if needed
        if has_like rhel || has_like centos; then
            if ! rpm -qa | grep -qi epel-release; then
                sudo "$PKG_MGR" install -y epel-release || true
            fi
        fi

        sudo "$PKG_MGR" install -y redis

    elif has_like suse || has_like opensuse; then
        # (open)SUSE
        sudo zypper refresh
        sudo zypper install -y redis

    else
        echo "Unsupported Linux distribution ($ID). Please install Redis manually."
        exit 1
    fi
else
    echo "Unsupported OS. Please install Redis manually."
    exit 1
fi

echo "Redis installation complete."

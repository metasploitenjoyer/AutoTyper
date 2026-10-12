#!/usr/bin/env bash
# Builds AutoTyper-macOS.dmg (run on a Mac):   bash Files/build_macos.sh
exec bash "$(dirname "$0")/installer/macos/build_macos.sh" "$@"

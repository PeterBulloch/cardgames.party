# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project
uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html). The version lives in
[`VERSION`](VERSION); see [CONTRIBUTING.md](CONTRIBUTING.md#releasing) for how to cut a release.

## [Unreleased]

## [0.1.0] - 2026-09-27

First versioned release.

### Added

- Lobbies: create (name, optional password, game, max players) and join by name, as a
  player, dealer or observer. Lobbies expire after 60 minutes idle or empty.
- Server-authoritative game state pushed over a WebSocket, filtered per viewer so players
  only see their own hand. Snapshots are versioned so clients drop stale updates.
- Texas Hold'em with enforced turn order: rotating button, small and big blinds, hole-card
  deal order, required burns, and automatic stage progression.
- Chips and pots: no-limit betting, all-ins with side pots, manual pot award with split pots,
  editable stacks and pots, configurable blinds with optional automatic doubling.
- Showdown hand evaluation with winners and hand names.
- Multi-step undo for any game action.
- Card entry by NFC scan or a visual suit/rank picker.
- Observer "hide hands" public view for shared screens.
- Production deployment: plain-HTTP container behind any HTTPS-terminating proxy, with a
  health check reporting the version.
- NFC tag scanner and writer page at `/scanner`.
- LAN hosting over HTTPS using local-ip.sh certificates (`scripts/start.ps1`).

[Unreleased]: https://github.com/PeterBulloch/Playing-Cards-Scanner/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/PeterBulloch/Playing-Cards-Scanner/releases/tag/v0.1.0

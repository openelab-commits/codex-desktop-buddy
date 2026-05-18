# Codex Usage Stick Plugin

This local Codex plugin starts a BLE bridge that sends Codex usage data to a
StickS3 running the matching Codex Usage Stick firmware.

The plugin is local-first:

- It reads local Codex usage files.
- It starts one background bridge process.
- It sends compact usage packets over BLE.
- It writes diagnostics under `~/.codex/codex-usage-bridge/`.
- It does not send data to an external server.

## Hooks

The plugin registers:

```text
SessionStart
UserPromptSubmit
```

Both hooks run:

```sh
python3 "$PLUGIN_ROOT/scripts/hook_entry.py"
```

The hook is synchronous because async plugin hooks are not supported yet. It
returns quickly: `hook_entry.py` writes a log line and asks `start_bridge.py` to
start or reuse the background bridge.

## Install From Codex UI

Open:

```text
Settings -> Plugins -> Add plugin marketplace
```

Fill the dialog like this:

```text
Source:
openelab-commits/claude-desktop-buddy-GIF

Git ref:
main

Sparse path:
leave empty
```

If this lives in your own fork, use your fork's `owner/repo`.

## CLI Fallback

```bash
/Applications/Codex.app/Contents/Resources/codex plugin marketplace add openelab-commits/claude-desktop-buddy-GIF --ref main
```

For local development:

```bash
/Applications/Codex.app/Contents/Resources/codex plugin marketplace add /path/to/claude-desktop-buddy-GIF
```

## Enable Hooks

Enable plugin hooks:

```bash
/Applications/Codex.app/Contents/Resources/codex features enable plugin_hooks
```

If needed, enable the plugin in `~/.codex/config.toml`:

```toml
[plugins."codex-usage-stick@codex-usage-stick-marketplace"]
enabled = true
```

Restart Codex after changing plugin settings. Approve the hook trust prompt
when Codex shows it.

## Included Skill

This plugin includes Codex skills for status, troubleshooting, and pet asset generation:

```text
skills/codex-usage-stick/SKILL.md
skills/codex-usage-pet/SKILL.md
```

They are installed with the plugin. No separate skill installation is required.

## Dependency

```bash
python3 -m pip install bleak
```

## Runtime Files

```text
~/.codex/codex-usage-bridge/config.json
~/.codex/codex-usage-bridge/hook.log
~/.codex/codex-usage-bridge/bridge.log
~/.codex/codex-usage-bridge/bridge.pid
```

## Config

Default `config.json`:

```json
{
  "name": "Codex-",
  "address": null,
  "interval": 5.0,
  "scan_timeout": 8.0,
  "restart_delay": 5.0,
  "verbose": true,
  "no_approval_proxy": true
}
```

Use `address` if macOS BLE name caching makes name scanning unreliable.

## Commands

Check status:

```bash
python3 plugins/codex-usage-stick/scripts/start_bridge.py --status
```

Start:

```bash
python3 plugins/codex-usage-stick/scripts/start_bridge.py
```

Stop:

```bash
python3 plugins/codex-usage-stick/scripts/start_bridge.py --stop
```

Run in foreground:

```bash
python3 plugins/codex-usage-stick/scripts/start_bridge.py --foreground
```

Manual hook test:

```bash
python3 plugins/codex-usage-stick/scripts/hook_entry.py --event ManualTest
```

## Verify

After submitting a Codex prompt:

```bash
tail -n 20 ~/.codex/codex-usage-bridge/hook.log
```

Expected:

```text
"event": "UserPromptSubmit"
```

Then check BLE packets:

```bash
tail -n 40 ~/.codex/codex-usage-bridge/bridge.log
```

Expected:

```text
sent {"state":"busy","tokens":...,"primary":...,"secondary":...}
```

## Limitation

Hardware approve/deny for Codex permission prompts is not enabled in this
version. The usage display bridge is the supported path.

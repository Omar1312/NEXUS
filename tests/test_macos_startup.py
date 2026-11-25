from __future__ import annotations

import plistlib
from pathlib import Path

from nexus.platforms.macos.startup import MacStartupAnalyzer


def test_launch_agent_scan_is_read_only_and_current_user_only(tmp_path, monkeypatch):
    home = tmp_path / "user"
    folder = home / "Library" / "LaunchAgents"
    folder.mkdir(parents=True)
    binary = tmp_path / "agent"
    binary.write_text("agent", encoding="utf-8")
    plist = folder / "com.example.agent.plist"
    plist.write_bytes(plistlib.dumps({
        "Label": "com.example.agent",
        "ProgramArguments": [str(binary), "--background"],
        "RunAtLoad": True,
    }))
    (folder / "broken.plist").write_bytes(b"not a plist")
    monkeypatch.setattr(Path, "home", lambda: home)

    result = MacStartupAnalyzer().scan()

    assert len(result.entries) == 1
    entry = result.entries[0]
    assert entry.name == "com.example.agent"
    assert entry.scope == "User"
    assert entry.kind == "launchagent"
    assert entry.file_exists
    assert "--background" in entry.command
    assert len(result.errors) == 1
    assert plist.exists()


def test_empty_or_missing_launch_agents_is_supported(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    result = MacStartupAnalyzer().scan()
    assert result.entries == ()
    assert result.errors == ()

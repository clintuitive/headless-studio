"""Plugin-hosting helpers."""

from __future__ import annotations

import os
import struct

def load_plugin(*args, **kwargs):
    """Load the optional host only when a plugin is actually requested."""
    from pedalboard import load_plugin as host_load
    return host_load(*args, **kwargs)

DEFAULT_NAM_VST3 = os.path.expanduser(
    "~/Library/Audio/Plug-Ins/VST3/NeuralAmpModeler.vst3"
)


def load_nam(model_path: str, plugin_path: str = DEFAULT_NAM_VST3):
    """Load Neural Amp Modeler with a capture selected headlessly.

    NAM stores the capture path inside its VST3 component-state chunk rather
    than exposing it as an automatable parameter.  This function updates that
    length-prefixed field in a fresh preset and returns the loaded plugin.
    """
    plugin = load_plugin(os.path.expanduser(plugin_path))
    preset = bytes(plugin.preset_data)
    if preset[:4] != b"VST3":
        raise ValueError(f"Unexpected NAM preset header from {plugin_path}")

    list_offset = struct.unpack("<q", preset[40:48])[0]
    component, tail = preset[48:list_offset], preset[list_offset:]
    marker = b"###NeuralAmpModeler###"
    marker_offset = component.find(marker)
    if marker_offset < 0:
        raise ValueError("NAM state marker not found in VST3 preset")

    cursor = marker_offset + len(marker)
    version_length = struct.unpack("<i", component[cursor:cursor + 4])[0]
    cursor += 4 + version_length
    model_length = struct.unpack("<i", component[cursor:cursor + 4])[0]
    encoded_path = os.path.abspath(model_path).encode()
    new_component = (
        component[:cursor]
        + struct.pack("<i", len(encoded_path))
        + encoded_path
        + component[cursor + 4 + model_length:]
    )

    entry_count = struct.unpack("<i", tail[4:8])[0]
    entries = bytearray()
    for index in range(entry_count):
        entry = tail[8 + index * 20:8 + (index + 1) * 20]
        entry_id = entry[:4]
        if entry_id == b"Comp":
            offset, size = 48, len(new_component)
        else:
            _, size = struct.unpack("<qq", entry[4:20])
            offset = 48 + len(new_component)
        entries.extend(entry_id + struct.pack("<qq", offset, size))

    plugin.preset_data = (
        preset[:40]
        + struct.pack("<q", 48 + len(new_component))
        + new_component
        + b"List"
        + struct.pack("<i", entry_count)
        + bytes(entries)
    )
    return plugin

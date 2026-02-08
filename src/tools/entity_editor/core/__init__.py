"""Core module for Entity Editor."""
from .signal_hub import SignalHub, get_signal_hub
from .history_manager import HistoryManager
from .snapshot_command import EntitySnapshotCommand
from .command import (
    Command, AddBodyPartCommand, RemoveBodyPartCommand, RemoveBodyPartsCommand, ModifyBodyPartCommand,
    MoveBodyPartCommand, AddHitboxCommand, RemoveHitboxCommand, 
    ModifyHitboxCommand, MoveHitboxCommand
)

__all__ = [
    'SignalHub', 'get_signal_hub', 'HistoryManager', 'Command', 'EntitySnapshotCommand',
    'AddBodyPartCommand', 'RemoveBodyPartCommand', 'RemoveBodyPartsCommand', 'ModifyBodyPartCommand',
    'MoveBodyPartCommand', 'AddHitboxCommand', 'RemoveHitboxCommand',
    'ModifyHitboxCommand', 'MoveHitboxCommand'
]

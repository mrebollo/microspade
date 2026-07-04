"""
microspade — SPADE-like agents for micro:bit.

Public API::

    from microspade import (
        Agent,
        Behaviour,
        CyclicBehaviour,
        OneShotBehaviour,
        PeriodicBehaviour,
        TimeoutBehaviour,
        FSMBehaviour,
        State,
        Message,
        MessageTemplate,
        RadioTransport,
    )
"""

from microspade.agent import Agent
from microspade.artifact import Artifact, RemoteArtifactProxy
from microspade.behaviour import (
    Behaviour,
    CyclicBehaviour,
    OneShotBehaviour,
    PeriodicBehaviour,
    TimeoutBehaviour,
    FSMBehaviour,
    State,
)
from microspade.message import Message, MessageTemplate
from microspade.mailbox import Mailbox
from microspade.transport import RadioTransport
from microspade.container import container

__all__ = [
    "Agent",
    "Artifact",
    "RemoteArtifactProxy",
    "Behaviour",
    "CyclicBehaviour",
    "OneShotBehaviour",
    "PeriodicBehaviour",
    "TimeoutBehaviour",
    "FSMBehaviour",
    "State",
    "Message",
    "MessageTemplate",
    "Mailbox",
    "RadioTransport",
    "container",
]

__version__ = "0.1.0"

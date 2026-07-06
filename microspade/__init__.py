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
from microspade.behaviour import Behaviour
from microspade.cyclic_behaviour import CyclicBehaviour
from microspade.oneshot_behaviour import OneShotBehaviour
from microspade.periodic_behaviour import PeriodicBehaviour
from microspade.timeout_behaviour import TimeoutBehaviour
from microspade.fsm_behaviour import FSMBehaviour, State
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

"""Tests for Message and MessageTemplate."""

import pytest
from microspade.message import Message, MessageTemplate


# ---------------------------------------------------------------------------
# Message
# ---------------------------------------------------------------------------


class TestMessageCreation:
    def test_defaults(self):
        msg = Message()
        assert msg.to is None
        assert msg.sender is None
        assert msg.body == ""
        assert msg.performative == "inform"
        assert msg.metadata == {}

    def test_explicit_fields(self):
        msg = Message(to="a1", sender="a2", body="hello", performative="request")
        assert msg.to == "a1"
        assert msg.sender == "a2"
        assert msg.body == "hello"
        assert msg.performative == "request"

    def test_none_body_becomes_empty(self):
        msg = Message(body=None)
        assert msg.body == ""

    def test_none_performative_becomes_inform(self):
        msg = Message(performative=None)
        assert msg.performative == "inform"


class TestMessageEncodeDecode:
    def test_roundtrip(self):
        msg = Message(to="a1", sender="a2", body="hello world", performative="request")
        decoded = Message.decode(msg.encode())
        assert decoded.to == msg.to
        assert decoded.sender == msg.sender
        assert decoded.body == msg.body
        assert decoded.performative == msg.performative

    def test_none_fields_roundtrip(self):
        msg = Message(to=None, sender=None, body="test")
        decoded = Message.decode(msg.encode())
        assert decoded.to is None
        assert decoded.sender is None
        assert decoded.body == "test"

    def test_body_with_pipe_roundtrip(self):
        """Pipe characters inside the body must survive encode/decode."""
        msg = Message(to="a1", sender="a2", body="a|b|c|d", performative="inform")
        decoded = Message.decode(msg.encode())
        assert decoded is not None
        assert decoded.body == "a|b|c|d"

    def test_empty_body_roundtrip(self):
        msg = Message(to="a", sender="b", body="")
        decoded = Message.decode(msg.encode())
        assert decoded.body == ""

    def test_decode_none_returns_none(self):
        assert Message.decode(None) is None

    def test_decode_empty_string_returns_none(self):
        assert Message.decode("") is None

    def test_decode_too_few_parts_returns_none(self):
        assert Message.decode("only_one_part") is None
        assert Message.decode("a|b|c") is None  # needs 4 parts

    def test_decode_empty_to_and_sender(self):
        raw = "||inform|body"
        msg = Message.decode(raw)
        assert msg.to is None
        assert msg.sender is None
        assert msg.body == "body"

    def test_encode_format(self):
        msg = Message(to="t", sender="s", body="b", performative="p")
        assert msg.encode() == "t|s|p|b"


class TestMessageHelpers:
    def test_make_reply_swaps_to_sender(self):
        original = Message(to="a1", sender="a2", body="ping", performative="request")
        reply = original.make_reply()
        assert reply.to == "a2"
        assert reply.sender == "a1"
        assert reply.performative == "request"
        assert reply.body == ""

    def test_set_get_metadata(self):
        msg = Message()
        msg.set_metadata("lang", "en")
        assert msg.get_metadata("lang") == "en"

    def test_get_metadata_missing_returns_none(self):
        msg = Message()
        assert msg.get_metadata("missing") is None

    def test_equality_same_fields(self):
        m1 = Message(to="a", sender="b", body="x", performative="inform")
        m2 = Message(to="a", sender="b", body="x", performative="inform")
        assert m1 == m2

    def test_equality_different_body(self):
        m1 = Message(body="x")
        m2 = Message(body="y")
        assert m1 != m2

    def test_equality_non_message_type(self):
        assert Message() != "not a message"

    def test_repr_contains_classname(self):
        assert "Message" in repr(Message(to="a"))


# ---------------------------------------------------------------------------
# MessageTemplate
# ---------------------------------------------------------------------------


class TestMessageTemplate:
    def test_empty_template_matches_everything(self):
        tmpl = MessageTemplate()
        assert tmpl.match(Message(to="a", sender="b", performative="inform"))

    def test_match_to(self):
        tmpl = MessageTemplate(to="agent1")
        assert tmpl.match(Message(to="agent1"))
        assert not tmpl.match(Message(to="agent2"))
        assert not tmpl.match(Message(to=None))

    def test_match_sender(self):
        tmpl = MessageTemplate(sender="agent1")
        assert tmpl.match(Message(sender="agent1"))
        assert not tmpl.match(Message(sender="other"))

    def test_match_performative(self):
        tmpl = MessageTemplate(performative="request")
        assert tmpl.match(Message(performative="request"))
        assert not tmpl.match(Message(performative="inform"))

    def test_match_body(self):
        tmpl = MessageTemplate(body="ping")
        assert tmpl.match(Message(body="ping"))
        assert not tmpl.match(Message(body="pong"))

    def test_match_combined(self):
        tmpl = MessageTemplate(to="a1", performative="request")
        assert tmpl.match(Message(to="a1", performative="request"))
        assert not tmpl.match(Message(to="a1", performative="inform"))
        assert not tmpl.match(Message(to="a2", performative="request"))

    def test_and_template(self):
        t1 = MessageTemplate(to="a")
        t2 = MessageTemplate(performative="inform")
        combined = t1 & t2
        assert combined.match(Message(to="a", performative="inform"))
        assert not combined.match(Message(to="a", performative="request"))
        assert not combined.match(Message(to="b", performative="inform"))

    def test_or_template(self):
        t1 = MessageTemplate(performative="inform")
        t2 = MessageTemplate(performative="request")
        combined = t1 | t2
        assert combined.match(Message(performative="inform"))
        assert combined.match(Message(performative="request"))
        assert not combined.match(Message(performative="cfp"))

    def test_not_template(self):
        t = MessageTemplate(performative="inform")
        not_t = ~t
        assert not_t.match(Message(performative="request"))
        assert not not_t.match(Message(performative="inform"))

    def test_repr_nonempty(self):
        tmpl = MessageTemplate(to="x")
        assert "x" in repr(tmpl)

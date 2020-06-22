#! /usr/bin/python3
import traceback
from pyln.proto.message import Message
import collections
import os.path
import io
import struct
from .errors import SpecFileError, EventError
from .namespace import event_namespace
from .utils import check_hex
from .signature import Sig
from .bitfield import has_bit
from typing import Optional, Dict, Union, Callable, Any, List, TYPE_CHECKING, overload
if TYPE_CHECKING:
    # Otherwise a circular dependency
    from .runner import Runner, Conn


# Type for arguments: either strings, or functions to call at runtime
ResolvableStr = Union[str, Callable[['Runner', 'Event', str], str]]
ResolvableInt = Union[int, Callable[['Runner', 'Event', str], int]]
ResolvableBool = Union[int, Callable[['Runner', 'Event', str], bool]]
Resolvable = Union[Any, Callable[['Runner', 'Event', str], Any]]


class Event(object):
    """Abstract base class for events."""
    def __init__(self) -> None:
        # From help(traceback.extract_stack):
        #   Each item in the list is a quadruple (filename,
        #   line number, function name, text), and the entries are in order
        #   from oldest to newest stack frame.
        self.name = 'unknown'
        for s in reversed(traceback.extract_stack()):
            # Ignore constructor calls, like this one.
            if s[2] != '__init__':
                self.name = "{}:{}:{}".format(type(self).__name__,
                                              os.path.basename(s[0]), s[1])
                break
        self.done = False

    def action(self, runner: 'Runner') -> None:
        if runner.config.getoption('verbose'):
            print("# running {}:".format(self))
        self.done = True

    def num_undone(self) -> int:
        """Number of actions to be done in this event; usually 1."""
        if self.done:
            return 0
        return 1

    def resolve_arg(self, fieldname: str, runner: 'Runner', arg: Resolvable) -> Any:
        """If this is a string, return it, otherwise call it to get result"""
        if callable(arg):
            return arg(runner, self, fieldname)
        else:
            return arg

    def resolve_args(self, runner: 'Runner', kwargs: Dict[str, Resolvable]) -> Dict[str, Any]:
        """Take a dict of args, replace callables with their return values"""
        ret: Dict[str, str] = {}
        for field, str_or_func in kwargs.items():
            ret[field] = self.resolve_arg(field, runner, str_or_func)
        return ret

    def __repr__(self) -> str:
        return self.name


class PerConnEvent(Event):
    """An event which takes a connprivkey arg"""
    def __init__(self, connprivkey: Optional[str]):
        super().__init__()
        self.connprivkey = connprivkey

    def find_conn(self, runner: 'Runner') -> 'Conn':
        """Helper for events which have a connection"""
        conn = runner.find_conn(self.connprivkey)
        if conn is None:
            if self.connprivkey is None:
                # None means "same as last used/created"
                raise SpecFileError(self, "No current connection")
            else:
                raise SpecFileError(self, "Unknown connection {}".format(self.connprivkey))
        return conn


class Connect(Event):
    """Connect to the runner, as if a node with private key connprivkey"""
    def __init__(self, connprivkey: str):
        self.connprivkey = connprivkey
        super().__init__()

    def action(self, runner: 'Runner') -> None:
        super().action(runner)
        if runner.find_conn(self.connprivkey):
            raise SpecFileError(self, "Already have connection to {}"
                                .format(self.connprivkey))
        runner.connect(self, self.connprivkey)


class MustNotMsg(PerConnEvent):
    """Indicate that this connection must never send any of these message types."""
    def __init__(self, must_not: str, connprivkey: Optional[str] = None):
        super().__init__(connprivkey)
        self.must_not = must_not

    def matches(self, binmsg: bytes) -> bool:
        msgnum = struct.unpack('>H', binmsg[0:2])[0]
        msgtype = event_namespace.get_msgtype_by_number(msgnum)
        if msgtype:
            name = msgtype.name
        else:
            name = str(msgnum)

        return name == self.must_not

    def action(self, runner: 'Runner') -> None:
        super().action(runner)
        self.find_conn(runner).must_not_events.append(self)


class Disconnect(PerConnEvent):
    """Disconnect the runner from the node whose private key is connprivkey: default is last connection specified"""
    def __init__(self, connprivkey: Optional[str] = None):
        super().__init__(connprivkey)

    def action(self, runner: 'Runner') -> None:
        super().action(runner)
        runner.disconnect(self, self.find_conn(runner))


class Msg(PerConnEvent):
    """Feed a message to the runner (via optional given connection)"""
    def __init__(self, msgtypename: str, connprivkey: Optional[str] = None,
                 **kwargs: Union[ResolvableStr, ResolvableInt]):
        super().__init__(connprivkey)
        self.msgtype = event_namespace.get_msgtype(msgtypename)
        if not self.msgtype:
            raise SpecFileError(self, "Unknown msgtype {}".format(msgtypename))
        self.kwargs = kwargs

    def action(self, runner: 'Runner') -> None:
        super().action(runner)
        # Now we have runner, we can fill in all the message fields
        message = Message(self.msgtype, **self.resolve_args(runner, self.kwargs))
        missing = message.missing_fields()
        if missing:
            raise SpecFileError(self, "Missing fields {}".format(missing))
        binmsg = io.BytesIO()
        message.write(binmsg)
        runner.recv(self, self.find_conn(runner), binmsg.getvalue())
        msg_to_stash(runner, self, message)


class RawMsg(PerConnEvent):
    """Feed a raw binary, or raw Message to the runner (via optional given connection)"""
    def __init__(self, message: Union[Resolvable, bytes, Message], connprivkey: Optional[str] = None):
        super().__init__(connprivkey)
        self.message = message

    def action(self, runner: 'Runner') -> None:
        super().action(runner)
        msg = self.resolve_arg('binmsg', runner, self.message)
        if isinstance(msg, Message):
            buf = io.BytesIO()
            msg.write(buf)
            binmsg = buf.getvalue()
        else:
            binmsg = msg

        runner.recv(self, self.find_conn(runner), binmsg)


class ExpectMsg(PerConnEvent):
    """Wait for a message from the runner.

Args is the (usually incomplete) message which it should match.
if_match is the function to call if it matches: should raise an
exception if it's not satisfied.  ignore is a list of messages to
ignore: by default, it is gossip_timestamp_filter, query_channel_range
and query_short_channel_ids.

    """
    def _default_if_match(self, msg: Message) -> None:
        pass

    def __init__(self, msgtypename: str,
                 if_match: Callable[['ExpectMsg', Message], None] = _default_if_match,
                 ignore: List[Message] = [Message(event_namespace.get_msgtype('gossip_timestamp_filter')),
                                          Message(event_namespace.get_msgtype('query_channel_range')),
                                          Message(event_namespace.get_msgtype('query_short_channel_ids'))],
                 connprivkey: Optional[str] = None,
                 **kwargs: Union[str, Resolvable]):
        super().__init__(connprivkey)
        self.msgtype = event_namespace.get_msgtype(msgtypename)
        if not self.msgtype:
            raise SpecFileError(self, "Unknown msgtype {}".format(msgtypename))
        self.kwargs = kwargs
        self.if_match = if_match
        self.ignore = ignore

    def message_match(self, runner: 'Runner', msg: Message) -> Optional[str]:
        """Does this message match what we expect?"""
        partmessage = Message(self.msgtype, **self.resolve_args(runner, self.kwargs))

        ret = cmp_msg(msg, partmessage)
        if ret is None:
            self.if_match(self, msg)
            msg_to_stash(runner, self, msg)
        return ret

    def ignored(self, msg: Message) -> bool:
        for i in self.ignore:
            if cmp_msg(msg, i) is None:
                return True
        return False

    def action(self, runner: 'Runner') -> None:
        super().action(runner)
        conn = self.find_conn(runner)
        while True:
            binmsg = runner.get_output_message(conn, self)
            if binmsg is None:
                raise EventError(self, "Did not receive a message from runner")

            for e in conn.must_not_events:
                if e.matches(binmsg):
                    raise EventError(self, "Got msg banned by {}: {}"
                                     .format(e, binmsg.hex()))

            # Might be completely unknown to namespace.
            try:
                msg = Message.read(event_namespace, io.BytesIO(binmsg))
            except ValueError as ve:
                raise EventError(self, "Runner gave bad msg {}: {}".format(binmsg.hex(), ve))

            if self.ignored(msg):
                continue

            err = self.message_match(runner, msg)
            if err:
                raise EventError(self, "{}: message was {}".format(err, msg.to_str()))

            break


class Block(Event):
    """Generate a block, at blockheight, with optional txs.

    """
    def __init__(self, blockheight: int, number: int = 1, txs: List[ResolvableStr] = []):
        super().__init__()
        self.blockheight = blockheight
        self.number = number
        self.txs = txs

    def action(self, runner: 'Runner') -> None:
        super().action(runner)
        # Oops, did they ask us to produce a block with no predecessor?
        if runner.getblockheight() + 1 < self.blockheight:
            raise SpecFileError(self, "Cannot generate block #{} at height {}".
                                format(self.blockheight, runner.getblockheight()))

        # Throw away blocks we're replacing.
        if runner.getblockheight() >= self.blockheight:
            runner.trim_blocks(self.blockheight - 1)

        # Add new one
        runner.add_blocks(self, [self.resolve_arg('tx', runner, tx) for tx in self.txs], self.number)
        assert runner.getblockheight() == self.blockheight - 1 + self.number


class ExpectTx(Event):
    """Expect the runner to broadcast a transaction

    """
    def __init__(self, txid: ResolvableStr):
        super().__init__()
        self.txid = txid

    def action(self, runner: 'Runner') -> None:
        super().action(runner)
        runner.expect_tx(self, self.resolve_arg('txid', runner, self.txid))


class FundChannel(PerConnEvent):
    """Tell the runner to fund a channel with this peer."""
    def __init__(self, amount: ResolvableInt, connprivkey: Optional[str] = None):
        super().__init__(connprivkey)
        self.amount = amount

    def action(self, runner: 'Runner') -> None:
        super().action(runner)
        runner.fundchannel(self,
                           self.find_conn(runner),
                           self.resolve_arg('amount', runner, self.amount))


class Invoice(Event):
    def __init__(self, amount: int, preimage: ResolvableStr):
        super().__init__()
        self.preimage = preimage
        self.amount = amount

    def action(self, runner: 'Runner') -> None:
        super().action(runner)
        runner.invoice(self, self.amount,
                       check_hex(self.resolve_arg('preimage', runner, self.preimage), 64))


class AddHtlc(PerConnEvent):
    def __init__(self, amount: int, preimage: ResolvableStr, connprivkey: Optional[str] = None):
        super().__init__(connprivkey)
        self.preimage = preimage
        self.amount = amount

    def action(self, runner: 'Runner') -> None:
        super().action(runner)
        runner.addhtlc(self, self.find_conn(runner),
                       self.amount,
                       check_hex(self.resolve_arg('preimage', runner, self.preimage), 64))


class ExpectError(PerConnEvent):
    def __init__(self, connprivkey: Optional[str] = None):
        super().__init__(connprivkey)

    def action(self, runner: 'Runner') -> None:
        super().action(runner)
        error = runner.check_error(self, self.find_conn(runner))
        if error is None:
            raise EventError(self, "No error found")


class CheckEq(Event):
    """Event to check a condition is true"""
    def __init__(self, a: Resolvable, b: Resolvable):
        super().__init__()
        self.a = a
        self.b = b

    def action(self, runner: 'Runner') -> None:
        super().action(runner)
        a = self.resolve_arg('a', runner, self.a)
        b = self.resolve_arg('b', runner, self.b)
        # dummy runner generates dummy fields.
        if a != b and not runner._is_dummy():
            raise EventError(self, "{} != {}".format(a, b))


def msg_to_stash(runner: 'Runner', event: Event, msg: Message) -> None:
    """ExpectMsg and Msg save every field to the stash, in order"""
    fields = msg.to_py()

    stash = runner.get_stash(event, type(event).__name__, [])
    stash.append((msg.messagetype.name, fields))
    runner.add_stash(type(event).__name__, stash)


def cmp_obj(obj: Any, expected: Any, prefix: str) -> Optional[str]:
    """Return None if every field in expected matches a field in obj.  Otherwise return a complaint"""
    if isinstance(expected, collections.abc.Mapping):
        for k, v in expected.items():
            if k not in obj:
                return "Missing field {}".format(prefix + '.' + k)
            diff = cmp_obj(obj[k], v, prefix + '.' + k)
            if diff:
                return diff
    elif not isinstance(expected, str) and isinstance(expected, collections.abc.Sequence):
        # Should we allow expected to be shorter?
        if len(expected) != len(obj):
            return "Expected {} elements, got {} in {}: expected {} not {}".format(len(expected), len(obj),
                                                                                   prefix, expected, obj)
        for i in range(len(expected)):
            diff = cmp_obj(obj[i], expected[i], "{}[{}]".format(prefix, i))
            if diff:
                return diff
    elif isinstance(expected, str) and expected.startswith('Sig('):
        # Special handling for signature comparisons.
        if Sig.from_str(expected) != Sig.from_str(obj):
            return "{}: signature mismatch {} != {}".format(prefix, obj, expected)
    else:
        if obj != expected:
            return "{}: {} != {}".format(prefix, obj, expected)

    return None


def cmp_msg(msg: Message, expected: Message) -> Optional[str]:
    """Return None if every field in expected matches a field in msg.  Otherwise return a complaint"""
    if msg.messagetype != expected.messagetype:
        return "Expected {}, got {}".format(expected.messagetype, msg.messagetype)

    obj = msg.to_py()
    expected_obj = expected.to_py()

    return cmp_obj(obj, expected_obj, expected.messagetype.name)


@overload
def msat(sats: int) -> int:
    ...


@overload
def msat(sats: Callable[['Runner', 'Event', str], int]) -> Callable[['Runner', 'Event', str], int]:
    ...


def msat(sats: ResolvableInt) -> ResolvableInt:
    """Convert a field from statoshis to millisatoshis"""
    def _msat(runner: 'Runner', event: Event, field: str) -> int:
        if callable(sats):
            return 1000 * sats(runner, event, field)
        else:
            return 1000 * sats
    if callable(sats):
        return _msat
    else:
        return 1000 * sats


def negotiated(a_features: ResolvableStr,
               b_features: ResolvableStr,
               included: List[int] = [],
               excluded: List[int] = []) -> ResolvableBool:
    def has_feature(fbit: int, featurebits: str) -> bool:
        # Feature bits go in optional/compulsory pairs.
        altfbit = fbit ^ 1
        return has_bit(featurebits, fbit) or has_bit(featurebits, altfbit)

    def _negotiated(runner: 'Runner', event: Event, field: str) -> bool:
        a = event.resolve_arg('features', runner, a_features)
        b = event.resolve_arg('features', runner, b_features)

        for i in included:
            if not has_feature(i, a) or not has_feature(i, b):
                return False

        for e in excluded:
            if has_feature(e, a) or has_feature(e, b):
                return False

        return True

    return _negotiated

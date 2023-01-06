from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Block(_message.Message):
    __slots__ = ["block_hash", "data", "index", "prev_hash", "timestamp"]
    BLOCK_HASH_FIELD_NUMBER: _ClassVar[int]
    DATA_FIELD_NUMBER: _ClassVar[int]
    INDEX_FIELD_NUMBER: _ClassVar[int]
    PREV_HASH_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    block_hash: str
    data: _containers.RepeatedCompositeFieldContainer[Transaction]
    index: int
    prev_hash: str
    timestamp: int
    def __init__(self, index: _Optional[int] = ..., timestamp: _Optional[int] = ..., prev_hash: _Optional[str] = ..., block_hash: _Optional[str] = ..., data: _Optional[_Iterable[_Union[Transaction, _Mapping]]] = ...) -> None: ...

class Blockchain(_message.Message):
    __slots__ = ["blocks"]
    BLOCKS_FIELD_NUMBER: _ClassVar[int]
    blocks: _containers.RepeatedCompositeFieldContainer[Block]
    def __init__(self, blocks: _Optional[_Iterable[_Union[Block, _Mapping]]] = ...) -> None: ...

class Empty(_message.Message):
    __slots__ = []
    def __init__(self) -> None: ...

class GreetRequest(_message.Message):
    __slots__ = ["node_id"]
    NODE_ID_FIELD_NUMBER: _ClassVar[int]
    node_id: str
    def __init__(self, node_id: _Optional[str] = ...) -> None: ...

class GreetResponse(_message.Message):
    __slots__ = ["node_id"]
    NODE_ID_FIELD_NUMBER: _ClassVar[int]
    node_id: str
    def __init__(self, node_id: _Optional[str] = ...) -> None: ...

class HeartbeatRequest(_message.Message):
    __slots__ = ["node_id", "node_nodes"]
    NODE_ID_FIELD_NUMBER: _ClassVar[int]
    NODE_NODES_FIELD_NUMBER: _ClassVar[int]
    node_id: str
    node_nodes: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, node_id: _Optional[str] = ..., node_nodes: _Optional[_Iterable[str]] = ...) -> None: ...

class Transaction(_message.Message):
    __slots__ = ["amount", "receiver", "sender", "timestamp"]
    AMOUNT_FIELD_NUMBER: _ClassVar[int]
    RECEIVER_FIELD_NUMBER: _ClassVar[int]
    SENDER_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    amount: int
    receiver: str
    sender: str
    timestamp: int
    def __init__(self, sender: _Optional[str] = ..., receiver: _Optional[str] = ..., amount: _Optional[int] = ..., timestamp: _Optional[int] = ...) -> None: ...

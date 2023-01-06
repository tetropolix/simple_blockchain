from __future__ import annotations
from datetime import datetime
import socket
from concurrent import futures
import threading
import time

import protos.NodeRPCService_pb2_grpc as NodeRPCService_pb2_grpc
import protos.NodeRPCService_pb2 as NodeRPCService_pb2
import node
import blockchain as chain

import grpc


class NodeId:
    def __init__(self, node_id: str):
        self.node_address = node_id
        try:
            splitted = self.node_address.split(":")
            if len(splitted) == 1:
                self.node_address = self._only_port_provided(node_id)
            splitted = self.node_address.split(":")
            if len(splitted) != 2:
                raise ValueError(
                    "Unable to split node id %s to host and port part" % node_id)
            self.host = splitted[0]
            self.port = splitted[1]
            socket.inet_aton(self.host)
            if (int(self.port) < 2000 and int(self.port) > 10000):
                raise ValueError(
                    "Port %s should be number in interval <2000,10000>" % node_id)
        except socket.error:
            raise ValueError(
                "Node id %s does not contain valid ip address" % node_id)

    def _only_port_provided(self, port: str) -> str:
        if (int(port) < 2000 or int(port) > 10000):
            raise ValueError(
                "Port %s should be number in interval <2000,10000>" % port)
        return "127.0.0.1:"+port


class NodeRPCService(NodeRPCService_pb2_grpc.NodeRPCServiceServicer):
    def __init__(self, node_id: NodeId | str, nodes_manager: NodesManager, blockchain_manager: BlockchainManager):
        self.node_id = NodeId(node_id) if isinstance(node_id, str) else node_id
        self.nodes_manager = nodes_manager
        self.blockchain_manager = blockchain_manager
        self.server = None  # instance of grpc server

    @staticmethod
    def get_node_rpc_stub(node_id: NodeId) -> NodeRPCService_pb2_grpc.NodeRPCServiceStub:
        channel = grpc.insecure_channel(node_id.node_address)
        return NodeRPCService_pb2_grpc.NodeRPCServiceStub(channel)

    def Greet(self, request, context):
        return NodeRPCService_pb2.GreetResponse(node_id=self.node_id.node_address)

    def Heartbeat(self, request: NodeRPCService_pb2.HeartbeatRequest, context):
        sender = node.RemoteNode(request.node_id)
        nodes = [node.RemoteNode(n) for n in request.node_nodes]
        if (sender not in nodes):
            nodes.append(sender)
        self.nodes_manager.update_nodes_after_remote_heartbeat(nodes)
        return NodeRPCService_pb2.Empty()

    def SendTransaction(self, request: NodeRPCService_pb2.Transaction, context):
        transaction = chain.Transaction.from_grpc_message(request)
        self.blockchain_manager.add_transaction(transaction)
        return NodeRPCService_pb2.Empty()

    def SendBlock(self, request: NodeRPCService_pb2.Block, context):
        new_block = chain.Block.from_grpc_message(request)
        self.blockchain_manager.add_received_block(new_block)
        return NodeRPCService_pb2.Empty()

    def QueryBlockchain(self, request: NodeRPCService_pb2.Empty, context) -> NodeRPCService_pb2.Blockchain:
        return self.blockchain_manager.blockchain.to_grpc_message()

    def start_service(self):
        if (self.server is not None):
            self.server.stop(None)
        with futures.ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(self._start_grpc_server)

    def _start_grpc_server(self):
        # print('Start of grpc server' + str(threading.get_ident()))
        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=5))
        NodeRPCService_pb2_grpc.add_NodeRPCServiceServicer_to_server(self, self.server)
        self.server.add_insecure_port(self.node_id.node_address)
        self.server.start()
        # self.server.wait_for_termination()

    def stop_service(self):
        if (self.server is not None):
            self.server.stop(None)


class NodesManager:
    HEARTBEAT_INTERVAL = 3  # seconds

    def __init__(self, node_id: NodeId, nodes: list[node.RemoteNode]) -> None:
        self.node_id = node_id
        self.nodes = nodes
        self.heartbeat_running = False
        self.heartbeat_task = None

    def broadcast_transaction(self, transaction: chain.Transaction):
        for node in self.nodes:
            try:
                node.transact(transaction)
            except grpc.RpcError as e:
                if (e.code() == grpc.StatusCode.UNAVAILABLE):  # type: ignore
                    self.nodes.remove(node)
                    # print('Node %s is unavailable' %
                    #   node.node_id.node_address)
                    continue
                raise

    def update_nodes_after_remote_heartbeat(self, nodes: list[node.RemoteNode]):
        updated = set(self.nodes).union(set(nodes))
        if node.RemoteNode(self.node_id) in updated:
            updated.remove(node.RemoteNode(self.node_id))
        self.nodes = list(updated)

    def start_heartbeat_task(self):
        # print('Starting heartbeat task for node ' + self.node_id.node_address)
        if (self.heartbeat_task is not None and self.heartbeat_task.is_alive()):
            self.stop_heartbeat()
            self.heartbeat_task.join()
        self.heartbeat_task = threading.Thread(target=self.heartbeat)
        self.heartbeat_running_event = threading.Event()
        self.heartbeat_task.start()

    def heartbeat(self):
        while True:
            self.heartbeat_running_event.wait(NodesManager.HEARTBEAT_INTERVAL)
            if (self.heartbeat_running_event.is_set()):
                break
            for node in self.nodes:
                nodes = [node.node_id for node in self.nodes]
                try:
                    node.heartbeat(self.node_id, nodes)
                except grpc.RpcError as e:
                    if (e.code() == grpc.StatusCode.UNAVAILABLE):  # type: ignore
                        self.nodes.remove(node)
                        # print('Node %s is unavailable' %
                        #   node.node_id.node_address)
                        continue
                    raise

    def stop_heartbeat(self):
        self.heartbeat_running_event.set()


class BlockchainManager:
    def __init__(self, node: node.Node, blockchain: chain.Blockchain | None, transactions: list[chain.Transaction]):
        self.node = node
        self.blockchain = blockchain if blockchain is not None else chain.Blockchain(None)
        self.transactions = transactions

    def update_blockchain_from_peers(self):
        nodes_manager = self.node.nodes_manager
        peer_nodes = nodes_manager.nodes
        for node in peer_nodes:
            try:
                queried_blockchain = node.query_blockchain()
            except grpc.RpcError as e:
                if (e.code() == grpc.StatusCode.UNAVAILABLE):  # type: ignore
                    nodes_manager.nodes.remove(node)
                    # print('Node %s is unavailable' %
                    #   node.node_id.node_address)
                    continue
                raise
            if (len(queried_blockchain.blocks) > len(self.blockchain.blocks) and queried_blockchain.validate_blockchain()):
                self.blockchain.blocks = queried_blockchain.blocks
                print('Blockchain has been updated to blockchain state of peer %s' % node.node_id.node_address)

    def add_received_block(self, block: chain.Block):
        added = self.blockchain.add_new_block(block)
        if (added == True):
            return
        should_query_for_blockchain = self.blockchain.only_greater_index(block)
        if (should_query_for_blockchain):
            self.update_blockchain_from_peers()

    def add_transaction(self, transaction: chain.Transaction):
        nodes_manager = self.node.nodes_manager
        self.transactions.append(transaction)
        if (len(self.transactions) < chain.Blockchain.TRANSACTIONS_THRESHOLD and not self._node_is_block_creator()):  # not creator and not enough transactions
            return
        elif (len(self.transactions) >= chain.Blockchain.TRANSACTIONS_THRESHOLD and not self._node_is_block_creator()):  # not creator but enough transactions
            self.transactions = []
            return
        if (len(self.transactions) >= chain.Blockchain.TRANSACTIONS_THRESHOLD and self._node_is_block_creator()):  # creator and enough transactions
            new_block = self._block_creation()
            if new_block is None:
                return
            peer_nodes = nodes_manager.nodes
            for node in peer_nodes:
                try:
                    node.send_new_block(new_block)
                except grpc.RpcError as e:
                    if (e.code() == grpc.StatusCode.UNAVAILABLE):  # type: ignore
                        nodes_manager.nodes.remove(node)
                        # print('Node %s is unavailable' %
                        #   node.node_id.node_address)
                        continue
                    raise

    def _block_creation(self) -> chain.Block | None:
        last_block = self.blockchain.last_block()
        new_index = last_block.index + 1
        timestamp = int(datetime.now().timestamp())
        prev_hash = last_block.block_hash
        new_block = chain.Block.create_block(new_index, timestamp, self.transactions, prev_hash)
        if (not self.blockchain.add_new_block(new_block)):
            print('Adding block to blockchain was unsuccessful')
            return None
        self.transactions = []
        return new_block

    def _node_is_block_creator(self) -> bool:
        last_transaction = max(self.transactions, key=lambda t: t.timestamp)
        return last_transaction.sender == self.node.node_id.node_address

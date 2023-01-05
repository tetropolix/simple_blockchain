from __future__ import annotations
import logging
import socket
from concurrent import futures
import sys
import threading
import time

from blockchain import Blockchain, Transaction
import protos.NodeRPCService_pb2_grpc as NodeRPCService_pb2_grpc
import protos.NodeRPCService_pb2 as NodeRPCService_pb2

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


class RemoteNode():
    def __init__(self, node_id: NodeId | str):
        self.node_id = NodeId(node_id) if isinstance(node_id, str) else node_id
        self.stub = NodeRPCService.get_node_rpc_stub(self.node_id)

    def __eq__(self, other):
        if (not isinstance(other, RemoteNode)):
            return False
        return self.node_id.node_address == other.node_id.node_address

    def __hash__(self):
        return hash(self.node_id.node_address)

    def greet(self, sender: NodeId):
        self.stub.Greet(NodeRPCService_pb2.GreetRequest(
            node_id=sender.node_address))

    def heartbeat(self, sender: NodeId, nodes: list[NodeId]):
        str_nodes = [node.node_address for node in nodes]
        self.stub.Heartbeat(NodeRPCService_pb2.HeartbeatRequest(
            node_id=sender.node_address, node_nodes=str_nodes))


class NodeRPCService(NodeRPCService_pb2_grpc.NodeRPCServiceServicer):
    def __init__(self, node_id: NodeId | str, nodes_manager: NodesManager):
        self.node_id = NodeId(node_id) if isinstance(node_id, str) else node_id
        self.nodes_manager = nodes_manager
        self.server = None

    @staticmethod
    def get_node_rpc_stub(node_id: NodeId) -> NodeRPCService_pb2_grpc.NodeRPCServiceStub:
        channel = grpc.insecure_channel(node_id.node_address)
        return NodeRPCService_pb2_grpc.NodeRPCServiceStub(channel)

    def Greet(self, request, context):
        return NodeRPCService_pb2.GreetResponse(node_id=self.node_id.node_address)

    def Heartbeat(self, request, context):
        sender = RemoteNode(request.node_id)
        nodes = [RemoteNode(n) for n in request.node_nodes]
        if (sender not in nodes):
            nodes.append(sender)
        self.nodes_manager.update_nodes_after_remote_heartbeat(nodes)
        return NodeRPCService_pb2.Empty()

    def start_service(self):
        if (self.server is not None):
            self.server.stop(None)
        with futures.ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(self._start_grpc_server)

    def _start_grpc_server(self):
        print('Start of grpc server' + str(threading.get_ident()))
        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=5))
        NodeRPCService_pb2_grpc.add_NodeRPCServiceServicer_to_server(
            self, self.server)
        self.server.add_insecure_port(self.node_id.node_address)
        self.server.start()
        # self.server.wait_for_termination()

    def stop_service(self):
        if (self.server is not None):
            self.server.stop(None)


class NodesManager:
    HEARTBEAT_INTERVAL = 3  # seconds

    def __init__(self, node_id: NodeId, nodes: list[RemoteNode]) -> None:
        self.node_id = node_id
        self.nodes = nodes
        self.heartbeat_running = False
        self.heartbeat_task = None

    def update_nodes_after_remote_heartbeat(self, nodes: list[RemoteNode]):
        updated = set(self.nodes).union(set(nodes))
        if RemoteNode(self.node_id) in updated:
            print('IN SET')
            updated.remove(RemoteNode(self.node_id))
        else:
            print('NOT IN SET')
        self.nodes = list(updated)

    def start_heartbeat_task(self):
        print('Starting heartbeat task for node ' + self.node_id.node_address)
        if (self.heartbeat_task is not None and self.heartbeat_task.is_alive()):
            self.stop_heartbeat()
            self.heartbeat_task.join()
        self.heartbeat_task = threading.Thread(target=self.heartbeat)
        self.heartbeat_running = True
        self.heartbeat_task.start()

    def heartbeat(self):
        while True:
            time.sleep(NodesManager.HEARTBEAT_INTERVAL)
            print(('Current nodes for node %s : ' %
                  self.node_id.node_address) + str([n.node_id.node_address for n in self.nodes]))
            if (not self.heartbeat_running):
                break
            for node in self.nodes:
                nodes = [node.node_id for node in self.nodes]
                try:
                    node.heartbeat(self.node_id, nodes)
                except grpc.RpcError as e:
                    if (e.code() == grpc.StatusCode.UNAVAILABLE):  # type: ignore
                        self.nodes.remove(node)
                        print('Node %s is unavailable' %
                              node.node_id.node_address)
                        continue
                    raise

    def stop_heartbeat(self):
        self.heartbeat_running = False


class Node():
    def __init__(self, node_id: str, blockchain: Blockchain | None, nodes: list[RemoteNode], transactions: list[Transaction]) -> None:
        self.node_id = NodeId(node_id)
        self.blockchain = blockchain if blockchain is not None else Blockchain(
            None)
        self.transactions = transactions
        self.nodes_manager = NodesManager(
            self.node_id, nodes)
        self.node_rpc_service = NodeRPCService(
            self.node_id, self.nodes_manager)
        self.node_rpc_service.start_service()
        print('after rpc service in node init')
        self.nodes_manager.start_heartbeat_task()

    @ property
    def nodes(self):
        return self.nodes_manager.nodes

    @ classmethod
    def logger(cls):
        return logging.getLogger(cls.__name__)

    @ classmethod
    def create_node(cls, node_id: str, node_to_contact: str | None):
        nodes: list[RemoteNode] = []
        transactions: list[Transaction] = []
        if (node_to_contact is not None):  # not the first node
            remote_node = RemoteNode(node_to_contact)
            try:
                remote_node.greet(NodeId(node_id))
            except grpc.RpcError as e:
                if (e.code() == grpc.StatusCode.UNAVAILABLE):  # type: ignore
                    sys.exit("Node %s unavailable" %
                             remote_node.node_id.node_address)
                raise
            nodes.append(remote_node)
        return cls(node_id, None, nodes, transactions)

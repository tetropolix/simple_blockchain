from __future__ import annotations
import socket
from concurrent import futures
import threading
import time

import protos.NodeRPCService_pb2_grpc as NodeRPCService_pb2_grpc
import protos.NodeRPCService_pb2 as NodeRPCService_pb2
import node

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
        sender = node.RemoteNode(request.node_id)
        nodes = [node.RemoteNode(n) for n in request.node_nodes]
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
        # print('Start of grpc server' + str(threading.get_ident()))
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

    def __init__(self, node_id: NodeId, nodes: list[node.RemoteNode]) -> None:
        self.node_id = node_id
        self.nodes = nodes
        self.heartbeat_running = False
        self.heartbeat_task = None

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
        self.heartbeat_running = True
        self.heartbeat_task.start()

    def heartbeat(self):
        while True:
            time.sleep(NodesManager.HEARTBEAT_INTERVAL)
            # print(('Current nodes for node %s : ' %
            #  self.node_id.node_address) + str([n.node_id.node_address for n in self.nodes]))
            if (not self.heartbeat_running):
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
        self.heartbeat_running = False

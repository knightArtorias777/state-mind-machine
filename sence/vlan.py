import socket
import threading
import json
import logging
from typing import Dict, Set


class VLANServer:
    def __init__(self, host: str = '0.0.0.0', port: int = 5000):
        """初始化VLAN服务器

        Args:
            host: 服务器监听地址
            port: 服务器监听端口
        """
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clients: Dict[str, socket.socket] = {}  # 客户端连接池
        self.vlans: Dict[str, Set[str]] = {}  # VLAN成员关系
        self.setup_logging()

    def setup_logging(self):
        """配置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def start(self):
        """启动服务器"""
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.logger.info(f"服务器启动在 {self.host}:{self.port}")
        except OSError as e:
            self.logger.error(f"启动服务器时发生错误: {e}")
            self.logger.info("尝试使用其他端口...")
            self.port += 1  # 尝试下一个端口
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.logger.info(f"服务器启动在 {self.host}:{self.port}")

        while True:
            client_socket, address = self.server_socket.accept()
            self.logger.info(f"新连接来自 {address}")
            client_handler = threading.Thread(
                target=self.handle_client,
                args=(client_socket, address)
            )
            client_handler.start()

    def handle_client(self, client_socket: socket.socket, address: tuple):
        """处理客户端连接

        Args:
            client_socket: 客户端socket对象
            address: 客户端地址
        """
        try:
            # 等待客户端注册信息
            data = client_socket.recv(1024).decode()
            client_info = json.loads(data)
            client_id = client_info['client_id']
            vlan_id = client_info['vlan_id']

            # 注册客户端
            self.register_client(client_id, vlan_id, client_socket)

            while True:
                try:
                    data = client_socket.recv(1024).decode()
                    if not data:
                        break

                    message = json.loads(data)
                    self.broadcast_to_vlan(vlan_id, message, client_id)

                except json.JSONDecodeError:
                    self.logger.error("无效的JSON数据")
                    break

        except Exception as e:
            self.logger.error(f"处理客户端时发生错误: {e}")
        finally:
            self.unregister_client(client_id, vlan_id)
            client_socket.close()

    def register_client(self, client_id: str,
                        vlan_id: str,
                        client_socket: socket.socket):
        """注册新客户端

        Args:
            client_id: 客户端ID
            vlan_id: VLAN ID
            client_socket: 客户端socket对象
        """
        self.clients[client_id] = client_socket
        if vlan_id not in self.vlans:
            self.vlans[vlan_id] = set()
        self.vlans[vlan_id].add(client_id)
        self.logger.info(f"客户端 {client_id} 加入 VLAN {vlan_id}")

    def unregister_client(self, client_id: str, vlan_id: str):
        """注销客户端

        Args:
            client_id: 客户端ID
            vlan_id: VLAN ID
        """
        if client_id in self.clients:
            del self.clients[client_id]
        if vlan_id in self.vlans and client_id in self.vlans[vlan_id]:
            self.vlans[vlan_id].remove(client_id)
        self.logger.info(f"客户端 {client_id} 离开 VLAN {vlan_id}")

    def broadcast_to_vlan(self, vlan_id: str, message: dict, sender_id: str):
        """向VLAN内所有成员广播消息

        Args:
            vlan_id: VLAN ID
            message: 要广播的消息
            sender_id: 发送者ID
        """
        if vlan_id not in self.vlans:
            return

        for client_id in self.vlans[vlan_id]:
            if client_id != sender_id and client_id in self.clients:
                try:
                    self.clients[client_id].send(json.dumps(message).encode())
                except Exception as e:
                    self.logger.error(f"发送消息到客户端 {client_id} 失败: {e}")


class VLANClient:
    def __init__(self, client_id: str,
                 vlan_id: str,
                 server_host: str = 'localhost',
                 server_port: int = 5000):
        """初始化VLAN客户端

        Args:
            client_id: 客户端ID
            vlan_id: VLAN ID
            server_host: 服务器地址
            server_port: 服务器端口
        """
        self.client_id = client_id
        self.vlan_id = vlan_id
        self.server_host = server_host
        self.server_port = server_port
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.setup_logging()

    def setup_logging(self):
        """配置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def connect(self):
        """连接到服务器"""
        try:
            self.client_socket.connect((self.server_host, self.server_port))
            # 发送注册信息
            registration_info = {
                'client_id': self.client_id,
                'vlan_id': self.vlan_id
            }
            self.client_socket.send(json.dumps(registration_info).encode())
            self.logger.info(f"已连接到服务器 {self.server_host}:{self.server_port}")
            return True
        except Exception as e:
            self.logger.error(f"连接服务器失败: {e}")
            return False

    def send_message(self, message: dict):
        """发送消息

        Args:
            message: 要发送的消息
        """
        try:
            self.client_socket.send(json.dumps(message).encode())
        except Exception as e:
            self.logger.error(f"发送消息失败: {e}")

    def receive_messages(self):
        """接收消息"""
        while True:
            try:
                data = self.client_socket.recv(1024).decode()
                if not data:
                    break
                message = json.loads(data)
                self.logger.info(f"收到消息: {message}")
            except Exception as e:
                self.logger.error(f"接收消息失败: {e}")
                break

    def start_receiving(self):
        """启动接收消息的线程"""
        receive_thread = threading.Thread(target=self.receive_messages)
        receive_thread.daemon = True
        receive_thread.start()

    def close(self):
        """关闭连接"""
        self.client_socket.close()

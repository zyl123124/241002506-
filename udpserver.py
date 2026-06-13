# server.py
import sys
import socket
import struct
import random
import threading

# 学号配置：后4位 2506
STUDENT_ID_LAST4 = 2506
XOR_KEY = 0x5A3C
STUDENT_ID = STUDENT_ID_LAST4 ^ XOR_KEY

# 报文类型
TYPE_CONN_REQ = 0x01
TYPE_CONN_ACK = 0x02
TYPE_DATA     = 0x03
TYPE_ACK      = 0x04

HEADER_LEN = 8
LOSS_RATE = 0.3  # 30%模拟丢包

# 解析报文
def unpack_packet(pkt):
    header = pkt[:HEADER_LEN]
    body = pkt[HEADER_LEN:]
    sid, ptype, seq, cs = struct.unpack("!HBBL", header)
    return sid, ptype, seq, cs, body

# 构造报文
def make_packet(pkt_type, seq, data):
    cs = 0
    for b in data:
        cs = (cs + b) & 0xFFFFFFFF
    header = struct.pack("!HBBL", STUDENT_ID, pkt_type, seq, cs)
    return header + data

# 校验学号
def verify_sid(sid):
    origin = sid ^ XOR_KEY
    return 0 <= origin <= 9999

# 处理单个客户端（对应TCP的handle_client）
def handle_client(client_addr):
    print(f"[+] 新客户端连接：{client_addr}")
    while True:
        try:
            data, addr = server_sock.recvfrom(1024)
            sid, ptype, seq, cs, body = unpack_packet(data)

            # 身份校验
            if not verify_sid(sid):
                print(f"[!] {client_addr} 学号校验失败，拒绝服务")
                continue

            # 处理连接请求
            if ptype == TYPE_CONN_REQ:
                print(f"[INIT] {client_addr} 发起连接请求")
                resp_pkt = make_packet(TYPE_CONN_ACK, 0, b"")
                server_sock.sendto(resp_pkt, addr)

            # 处理数据报文 + 模拟丢包
            elif ptype == TYPE_DATA:
                print(f"[DATA] 收到报文，序号：{seq}")
                # 随机丢包
                if random.random() < LOSS_RATE:
                    print(f"[LOSS] 模拟丢包，序号：{seq}")
                    continue
                # 回复确认报文
                ack_pkt = make_packet(TYPE_ACK, seq, b"")
                server_sock.sendto(ack_pkt, addr)
                print(f"[ACK] 已发送确认，序号：{seq}")

        except Exception as e:
            print(f"[-] 客户端 {client_addr} 断开：{e}")
            break

# 主程序（和TCP服务端框架完全一致）
def main():
    global server_sock
    if len(sys.argv) != 2:
        print("用法：python server.py 端口号")
        sys.exit(1)
    port = int(sys.argv[1])

    server_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_sock.bind(("0.0.0.0", port))
    print(f"[*] UDP服务端启动，监听端口 {port}")

    # 循环接收客户端，每一个连接开独立线程
    while True:
        data, client_addr = server_sock.recvfrom(1024)
        t = threading.Thread(target=handle_client, args=(client_addr,))
        t.daemon = True
        t.start()

if __name__ == "__main__":
    main()
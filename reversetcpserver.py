import socket
import threading
import struct

# 报文类型定义
TYPE_INIT = 1
TYPE_AGREE = 2
TYPE_REV_REQ = 3
TYPE_REV_ANS = 4

def handle_client(conn, addr):
    print(f"[+] 新客户端连接：{addr}")
    try:
        # 1. 接收Initialization报文
        header = conn.recv(6)  # 2B Type + 4B N
        if not header:
            return
        type_, N = struct.unpack("!HI", header)  #拆包
        if type_ != TYPE_INIT:
            return
        print(f"[INIT] 收到客户端{addr}请求，总块数N={N}")

        # 2. 回复Agree报文
        agree_pkt = struct.pack("!H", TYPE_AGREE)
        conn.sendall(agree_pkt)

        # 3. 循环处理每一块反转请求
        for i in range(N):
            # 接收reverseRequest报文头
            req_header = conn.recv(6)  # 2B Type + 4B Length
            if not req_header:
                break
            type_, length = struct.unpack("!HI", req_header)
            if type_ != TYPE_REV_REQ:
                break
            # 接收Data部分
            data = b""
            while len(data) < length:
                chunk = conn.recv(length - len(data))
                if not chunk:
                    break
                data += chunk
            # 反转文本（核心逻辑）
            reversed_data = data[::-1]
            # 构造reverseAnswer报文
            ans_pkt = struct.pack("!HI", TYPE_REV_ANS, len(reversed_data)) + reversed_data
            conn.sendall(ans_pkt)
            print(f"[REV] 处理第{i+1}块，长度={length}字节")
    except Exception as e:
        print(f"[!] 客户端{addr}出错：{e}")
    finally:
        conn.close()
        print(f"[-] 客户端{addr}断开连接")

def main():
    import sys
    if len(sys.argv) != 2:
        print("用法：python3 server.py <port>")
        sys.exit(1)
    port = int(sys.argv[1])

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", port))
    sock.listen(5)
    print(f"[*] 服务端启动，监听端口{port}...")

    #多线程
    while True:
        conn, addr = sock.accept()
        t = threading.Thread(target=handle_client, args=(conn, addr))
        t.daemon = True
        t.start()

if __name__ == "__main__":
    main()
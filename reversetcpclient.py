import socket
import struct
import random
import sys
from datetime import datetime

# 报文类型定义
TYPE_INIT = 1       # 初始化报文：告诉服务端“我有几块数据”
TYPE_AGREE = 2      # 确认报文：服务端说“收到，我准备好了”
TYPE_REV_REQ = 3    # 反转请求报文：客户端发“这块数据帮我反转”
TYPE_REV_ANS = 4    # 反转回答报文：服务端发“这是反转好的数据”

def log_event(log_file, event):
    """记录日志事件，带时间戳"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    log_line = f"[{timestamp}] {event}\n"
    log_file.write(log_line)
    print(log_line, end="")

def split_file(file_path, Lmin, Lmax, seed):
    """按规则分块，返回块列表（每块的偏移和长度）和总块数N"""
    with open(file_path, "rb") as f:
        data = f.read()
    total_len = len(data)
    blocks = []       # 用来存每一块的信息：（起始位置，块长度）
    offset = 0          # 当前读到哪个位置了，从0开始
    random.seed(seed)  # 固定种子，保证分块可复现
    while offset < total_len:
        remaining = total_len - offset
        if remaining <= Lmax:
            block_len = remaining
        else:
            block_len = random.randint(Lmin, Lmax)
        blocks.append((offset, block_len))
        offset += block_len
    return data, blocks, len(blocks)

def main():
    if len(sys.argv) != 7:
        print("用法：python reversetcpclient.py <serverIP> <serverPort> <Lmin> <Lmax> <chunk_seed> <file_path>")
        sys.exit(1)

    serverIP = sys.argv[1]
    serverPort = int(sys.argv[2])
    Lmin = int(sys.argv[3])
    Lmax = int(sys.argv[4])
    chunk_seed = int(sys.argv[5])
    file_path = sys.argv[6]

    # 1. 分块
    data, blocks, N = split_file(file_path, Lmin, Lmax, chunk_seed)
    print(f"[INFO] 文件分块完成，总块数N={N}")

    # 打开日志文件
    log_file = open("run_log.txt", "w", encoding="utf-8")
    reversed_full = b""               #用来存所有反转结果的 “空盒子”

    try:
        # 2. 连接服务端
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)    #IPv4 TCP
        sock.connect((serverIP, serverPort))
        log_event(log_file, f"连接到服务端 {serverIP}:{serverPort}")

        # 3. 发送Initialization报文
        init_pkt = struct.pack("!HI", TYPE_INIT, N)
        sock.sendall(init_pkt)
        log_event(log_file, f"发送Initialization报文，N={N}")

        # 4. 接收Agree报文
        agree_pkt = sock.recv(2)
        type_, = struct.unpack("!H", agree_pkt)
        if type_ != TYPE_AGREE:
            log_event(log_file, "收到错误报文，断开连接")
            return
        log_event(log_file, "收到Agree报文，初始化完成")

        # 5. 循环发送每一块并接收反转结果
        for idx, (offset, block_len) in enumerate(blocks, 1):
            # 提取当前块数据
            block_data = data[offset:offset+block_len]
            # 发送reverseRequest报文
            req_pkt = struct.pack("!HI", TYPE_REV_REQ, block_len) + block_data
            sock.sendall(req_pkt)
            log_event(log_file, f"发送reverseRequest报文，块号={idx}，长度={block_len}")

            # 接收reverseAnswer报文头
            ans_header = sock.recv(6)
            type_, ans_len = struct.unpack("!HI", ans_header)
            if type_ != TYPE_REV_ANS:
                log_event(log_file, f"收到错误报文，块号={idx}")
                break
            # 接收反转数据
            rev_data = b""
            while len(rev_data) < ans_len:
                chunk = sock.recv(ans_len - len(rev_data))
                if not chunk:
                    break
                rev_data += chunk
            # 终端打印
            print(f"第{idx}块：{rev_data.decode('ascii')}")
            log_event(log_file, f"收到reverseAnswer报文，块号={idx}，长度={ans_len}")
            reversed_full += rev_data

    except Exception as e:
        log_event(log_file, f"出错：{e}")
    finally:
        sock.close()
        log_file.close()
        # 6. 写入完整反转文件
        with open("reversed_output.txt", "wb") as f:
            f.write(reversed_full)
        print("[INFO] 完整反转文件已生成：reversed_output.txt")

if __name__ == "__main__":
    main()
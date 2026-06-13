# client.py
import sys
import socket
import struct
import time
import pandas as pd

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
DATA_PER_PACK = 80
WINDOW_MAX_PKT = 5    # 滑动窗口最多5个包
TIMEOUT_SEC = 0.3     # 超时时间300ms

# 构造报文
def make_packet(pkt_type, seq, data):
    cs = 0
    for b in data:
        cs = (cs + b) & 0xFFFFFFFF
    header = struct.pack("!HBBL", STUDENT_ID, pkt_type, seq, cs)
    return header + data

# 解析报文
def unpack_packet(pkt):
    header = pkt[:HEADER_LEN]
    body = pkt[HEADER_LEN:]
    sid, ptype, seq, cs = struct.unpack("!HBBL", header)
    return sid, ptype, seq, cs, body

def main():
    # 命令行参数校验
    if len(sys.argv) != 3:
        print("用法：python client.py 服务端IP 端口号")
        sys.exit(1)

    server_ip = sys.argv[1]
    server_port = int(sys.argv[2])
    server_addr = (server_ip, server_port)

    # 创建UDP套接字 + 设置超时
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(TIMEOUT_SEC)

    # 日志与统计变量
    log_fp = open("run_log.txt", "w", encoding="utf-8")
    rtt_list = []
    total_send = 0
    retrans_cnt = 0
    total_data_pkt = 30  # 总共发送30个数据包

    # 1. 模拟连接建立
    print("==== 开始建立连接 ====")
    conn_pkt = make_packet(TYPE_CONN_REQ, 0, b"")
    while True:
        sock.sendto(conn_pkt, server_addr)
        total_send += 1
        log_fp.write(f"[{time.time()}] 发送连接请求\n")
        try:
            recv_data, _ = sock.recvfrom(1024)
            sid, ptype, seq, cs, body = unpack_packet(recv_data)
            if ptype == TYPE_CONN_ACK:
                print("连接建立成功！")
                log_fp.write(f"[{time.time()}] 收到连接确认\n")
                break
        except socket.timeout:
            print("连接请求超时，重新发送...")
            log_fp.write(f"[{time.time()}] 连接请求超时，重传\n")
            retrans_cnt += 1

    # 2. GBN滑动窗口 数据传输
    print("\n==== 开始传输数据 ====")
    base = 0
    next_seq = 0
    test_data = b"0" * DATA_PER_PACK

    while base < total_data_pkt:
        # 窗口内连续发包
        while next_seq < base + WINDOW_MAX_PKT and next_seq < total_data_pkt:
            send_pkt = make_packet(TYPE_DATA, next_seq, test_data)
            send_ts = time.time()
            sock.sendto(send_pkt, server_addr)
            total_send += 1
            log_fp.write(f"[{send_ts}] 发送数据包 序号={next_seq}\n")
            next_seq += 1

        # 等待ACK，超时则重传整个窗口
        try:
            ack_data, _ = sock.recvfrom(1024)
            sid, ptype, ack_seq, cs, body = unpack_packet(ack_data)
            if ptype == TYPE_ACK:
                recv_ts = time.time()
                rtt = (recv_ts - send_ts) * 1000
                rtt_list.append(rtt)
                log_fp.write(f"[{recv_ts}] 收到确认 序号={ack_seq} RTT={rtt:.2f}ms\n")
                # 累积确认，滑动窗口
                if ack_seq >= base:
                    base = ack_seq + 1
        except socket.timeout:
            print(f"超时！重传窗口起始 base={base}")
            log_fp.write(f"[{time.time()}] 超时，重传窗口 base={base}\n")
            next_seq = base
            retrans_cnt += 1

    # 3. 传输结束，统计输出
    print("\n==== 传输完成 统计信息 ====")
    log_fp.write(f"[{time.time()}] 全部数据传输完成\n")

    # 计算丢包率
    loss_rate = (total_send - total_data_pkt) / total_send * 100
    print(f"丢包率：{loss_rate:.2f} %")
    log_fp.write(f"丢包率：{loss_rate:.2f}%\n")

    # RTT统计
    if rtt_list:
        df = pd.DataFrame(rtt_list, columns=["RTT(ms)"])
        print(f"最大RTT：{df['RTT(ms)'].max():.2f} ms")
        print(f"最小RTT：{df['RTT(ms)'].min():.2f} ms")
        print(f"平均RTT：{df['RTT(ms)'].mean():.2f} ms")
        print(f"RTT标准差：{df['RTT(ms)'].std():.2f} ms")

        log_fp.write(f"最大RTT：{df['RTT(ms)'].max():.2f} ms\n")
        log_fp.write(f"最小RTT：{df['RTT(ms)'].min():.2f} ms\n")
        log_fp.write(f"平均RTT：{df['RTT(ms)'].mean():.2f} ms\n")
        log_fp.write(f"RTT标准差：{df['RTT(ms)'].std():.2f} ms\n")

    log_fp.close()
    sock.close()

if __name__ == "__main__":
    main()
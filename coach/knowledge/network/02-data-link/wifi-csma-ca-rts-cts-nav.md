# 802.11 CSMA/CA：CTS 中的 NAV 怎样计时

## 为什么收到 CTS 的站还要静默

无线局域网可能有隐藏站：B 听不到发送站 A，却能听到接收站 AP。若 B 只凭自己听到的空闲信道发送，就会在 AP 处干扰 A 的数据帧。802.11 用请求发送帧（Request To Send，RTS）和允许发送帧（Clear To Send，CTS）预约接下来的一次交换；听到 RTS 或 CTS 的其他站，把帧中持续时间字段装入网络分配向量（Network Allocation Vector，NAV），在倒计时结束前不竞争信道。

```text
A                    AP                              B（隐藏站）
│── RTS ────────────►│
│       SIFS         │
│◄──── CTS ──────────│────────────── CTS ───────────►│ 开始 NAV
│       SIFS         │                                │
│── DATA ───────────►│                                │ 静默至 ACK 结束
│       SIFS         │                                │
│◄──── ACK ──────────│                                ▼
```

短帧间间隔（Short Interframe Space，SIFS）使 CTS、DATA、ACK 能紧接着完成这一轮已预约的交换。分布式帧间间隔（Distributed Interframe Space，DIFS）只用于开始一轮新的竞争；预约已经开始后，不应把 DIFS 加入 NAV。

## NAV 的起点就是当前帧结束处

持续时间字段的含义是“**本帧发送结束后**，信道还会被这次交换占用多久”。因此计算时先站在收到该帧的时刻，把已经发生的 RTS、等待 CTS 的 SIFS 和 CTS 本身全部留在时间轴左侧，只累加右侧尚未发生的部分。

```text
RTS 结束后： SIFS + CTS + SIFS + DATA + SIFS + ACK
CTS 结束后：             SIFS + DATA + SIFS + ACK
DATA 结束后：                         SIFS + ACK
```

隐藏站 B 听到的是 AP 的 CTS，故它设置的是第二行：

```text
NAV(CTS) = 2×SIFS + DATA 发送时间 + ACK 发送时间
```

这不是少算 RTS，而是 RTS 已经结束；也不是漏掉 DIFS，而是 DIFS 尚未属于这次预约。

## 数据帧时间怎样换算

长度为 `L B` 的数据帧含有 `8L bit`。链路速率为 `R Mb/s` 时，`1 Mb/s = 1 bit/μs`，所以忽略其他开销时：

```text
DATA 发送时间 = 8L / R  μs
```

例如 `L=1998 B、R=54 Mb/s`，数据帧时间为 `1998×8/54 = 296 μs`。若 `SIFS=28 μs、ACK=2 μs`，则 CTS 中的 NAV 为 `28+296+28+2=354 μs`。RTS、CTS、ACK 等控制帧的发送时间若题目已给出，应直接使用；不要把它们误当成数据帧再按 `L/R` 重算。

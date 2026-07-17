# 802.11 CSMA/CA：RTS/CTS 与 NAV

## RTS/CTS 怎样预约信道

无线局域网中的隐藏站可能听不到发送站，却能听到接收站。发送站先用请求发送帧（Request To Send，RTS）预约，接收站再发回允许发送帧（Clear To Send，CTS）；邻近站侦听到 RTS 或 CTS 后，按其持续时间字段设置网络分配向量（Network Allocation Vector，NAV），在倒计时结束前保持静默。

```text
发送站 A                  接收站 AP                   隐藏站 B
   ── RTS ──►
             SIFS
   ◄─ CTS ──────────────── CTS ─────────────────────► 收到 CTS，设置 NAV
             SIFS                                  │
   ── DATA ─►                                      │ 剩余预约时间
             SIFS                                  │ = SIFS + DATA + SIFS + ACK
   ◄─ ACK ──                                        ▼
```

短帧间间隔（Short Interframe Space，SIFS）让 CTS、DATA、ACK 能连续完成同一轮交换。分布式帧间间隔（Distributed Interframe Space，DIFS）用于新一轮信道竞争；RTS 已经发出后，后续预约时间不再包含 DIFS。

## 不同帧中的 NAV 从哪里算起

持续时间字段只填写“本帧结束后还要占用多久”，已经发送完的帧不能重复计入：

```text
RTS 中的持续时间 = 3×SIFS + CTS + DATA + ACK
CTS 中的持续时间 = 2×SIFS + DATA + ACK
DATA 中的持续时间 = SIFS + ACK
```

隐藏站若只听到 CTS，就从 CTS 结束处开始预约，因此使用第二式。题目给出数据帧总长度 `L B`、链路速率 `R Mb/s` 且忽略额外开销时：

```text
DATA 发送时间 = L×8 / R  μs
```

这里能直接得到微秒，是因为 `B` 先乘 8 变成 bit，而 `Mb/s` 与 `bit/μs` 数值相同。控制帧的发送时间若已由题目给出，直接代入，不再用数据链路速率重算。

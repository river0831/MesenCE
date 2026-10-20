# NES 运行时翻译模型与 Corner Cases

> 状态：工作文档  
> 目标：记录当前实现、设计约束、已知问题和待验证情况。本文描述的是通用模型；Dragon Quest 专属地址、文本表和翻译内容属于翻译包配置。

## 1. 最基本的产品规则

系统必须始终遵守一条规则：

> 游戏画面上当前可见的文字才显示翻译；已经不可见的文字必须停止显示。

“曾经解码过”“曾经写入过 Nametable”“属于当前 NPC”都不能单独证明文字仍然可见。最终显示状态必须由当前屏幕状态决定。

同时遵守以下原则：

1. 有稳定语义来源的格子优先使用来源，不再对这些格子执行 fallback 内容识别。
2. 没有稳定来源的格子仍然可以通过屏幕内容识别和翻译数据库查询处理。
3. 排除 fallback 的单位是“有稳定来源的格子”，不是矩形窗口或来源覆盖区域。
4. 不为某个日文词、某件道具或某个游戏场景编写特殊判断。
5. 游戏专属知识进入翻译包或适配配置；运行时匹配、生命周期和 grouping 算法保持通用。
6. 漏翻译可以接受；错误翻译、错误残留和把不可见内容显示出来应优先避免。

## 2. 名词与身份

### 2.1 Record

`recordId` 表示 ROM 中一个已提取的语义文本记录，例如一段 NPC 对话或商店提示。

它回答：文字来自哪条原文？

同一个 record 可以：

- 分多次写入；
- 跨多行显示；
- 被滚动；
- 被部分遮挡；
- 在不同时间重复出现。

### 2.2 Instance

`instanceId` 表示一次运行时显示生命周期。

同一个 NPC 两次说相同的话，也应产生两个 instance。一个 record 可以同时存在多个解码 fragment 或 instance；不能因为新 instance 出现，就立即删除旧 instance 仍然可见的格子。

### 2.3 Logical glyph

逻辑字符是文本解码后的语义字符。它有：

- `recordId`
- `instanceId`
- `glyphIndex`：在 record 展开结果中的位置
- `sourceOffset`：ROM 来源偏移
- `value`：最终写入的游戏字符或 tile 值

浊音、半浊音等修饰符应归属于其基础字符，不能错误地形成独立语义字符。

### 2.4 Source cell

带稳定来源的 Nametable 格子。它把一个当前屏幕格子和逻辑字符关联起来。

### 2.5 Block

当前屏幕上可以独立摆放译文的一组可见字符。当前实现以“同一 `recordId`、同一屏幕 tile 行”为基础 block。

block 不是永久文本分段，也不是对 ROM 原文做不可逆切句；它只是当前帧的可见投影。

### 2.6 Fallback match

无法得到稳定来源时，从当前 Nametable 的可见字符内容中查找翻译数据库得到的匹配。调试界面中：

- 绿色框：稳定来源路径；
- 红色框：fallback 内容识别路径。

## 3. 当前数据流

```text
ROM 文本 / 运行时参数
        │
        ▼
游戏文本解码与字典展开
        │  recordId + instanceId + glyphIndex
        ▼
PPU 写入缓冲区
        │  关联目标 Nametable 地址和值
        ▼
物理 CIRAM / 两个 Nametable 页面
        │  根据实时滚动与镜像关系投影
        ▼
当前 256×240 屏幕上的可见格子
        │
        ├── 有稳定来源 ──► source grouping ──► 译文区间投影
        │
        └── 无稳定来源 ──► 内容识别 ──► 翻译数据库查询
                                      │
                                      ▼
                            当前帧 Translation Scene
                                      │
                                      ▼
                              macOS 翻译窗口渲染
```

## 4. Nametable 与当前屏幕

NES 的 PPU 地址空间可以表示四个逻辑 Nametable，但卡带镜像通常只提供两个物理 CIRAM 页面。Dragon Quest 使用垂直镜像。

来源追踪保存物理页面中的格子；每帧根据 PPU scroll 和镜像关系，将它们投影成当前屏幕坐标。翻译系统关心的是投影后的屏幕格子，而不是仅固定观察某一个 Nametable 页面。

这解决了以下情况：

- 游戏在离屏 Nametable 中准备窗口；
- 通过滚动瞬间把准备好的页面带到屏幕；
- 玩家看不到明显切换，但 PPU 实际显示来源已改变；
- 同一物理页面通过镜像映射到不同逻辑页面。

## 5. 稳定来源路径

### 5.1 来源建立

当前 Dragon Quest 适配器观察文本流和 PPU 缓冲写入，将符合预期字符序列的写入标记为：

```text
(recordId, instanceId, glyphIndex, sourceOffset, tileValue)
```

只有目标地址和最终写入值与待提交来源相符时，Nametable 格子才继承该来源。

### 5.2 来源失效

后来的无来源写入覆盖该格子时，旧来源必须清除。仅仅 tile 数值相同不能证明来源身份相同。

如果游戏只是原样刷新同一个格子，并且能够确定仍是同一所有者，可以保留来源。

### 5.3 可见投影

每帧把带来源的物理格子投影到当前屏幕，输出每个可见字的：

```json
{
  "recordId": "chr-fc-234a",
  "instanceId": "msg-42",
  "index": 12,
  "cell": 641
}
```

其中 `cell` 是当前屏幕 tile 坐标的一维表示，不是 ROM 地址。

### 5.4 Grouping

当前规则：

1. 先按 `recordId` 汇总当前可见的来源格子。
2. 再按屏幕 tile 行建立独立 block。
3. 一个 block 可以包含多个 decoder instance 的格子。
4. block 使用自己的屏幕 bounds、源索引范围和 `unitId`。
5. block 消失时，对应翻译必须在同一帧生命周期中消失。

不能仅按 `glyphIndex` 是否连续切 block。运行时来源追踪可能漏掉中间格子，而屏幕文字仍是同一行；仅按缺号切割曾把“要买什么？”错误拆成“买 / 什 / 什么？”。

### 5.5 译文区间投影

不把每条长文本预先硬切成许多固定小句。对一个可见 block：

1. 找到它覆盖的最小和最大原文逻辑索引。
2. 计算该范围在完整原文中的大致比例。
3. 将同一比例映射到译文字符序列。
4. `{ITEM}` 等运行时 placeholder 作为不可拆分原子。

该投影是近似算法。日文与中文语序、长度可能不同，因此它保证“显示大致对应部分”，但不保证语言学上的逐字对齐。

## 6. Fallback 内容路径

### 6.1 使用条件

只有没有稳定来源的格子才能参与 fallback。不能用“稳定来源的矩形范围”整体排除，因为同一窗口内可能混合：

- 稳定来源对话；
- 无来源的道具名称；
- 数字或价格；
- 子窗口选项；
- 运行时生成内容。

### 6.2 内容识别

fallback 从当前屏幕字符格子建立文本 run，再与翻译数据库中的候选文本比较。可使用：

- 精确匹配；
- 子串匹配；
- 多候选最优匹配；
- 词汇表匹配；
- 带 placeholder 的模板匹配。

匹配必须保留屏幕位置和实际参与匹配的格子，避免把数据库中存在但屏幕上不可见的文本显示出来。

### 6.3 当前限制

如果数据库只有一条完整长 record，而屏幕上只有其完全失去来源的后半句，fallback 未必能从局部内容找到完整 record。

当前例子：

```text
chr-fc-234a
原文：这里是武器和防具店。/ 要买点什么吗？
```

运行时只有第一部分约 42% 的格子保留稳定来源；第二行“なにか かうかね？”整行没有来源。因为 fallback 数据库没有足够的局部索引，它也没有匹配到后半句，因此发生漏译。

## 7. 运行时参数与模板

道具、敌人、人物名和数值不应写死在 instance 中。翻译记录是模板，instance 只保存本次运行时参数：

```json
{
  "recordId": "dq.chest.found-item",
  "instanceId": "msg-184",
  "parameters": {
    "ITEM": {
      "valueId": 3,
      "sourceText": "かぎ",
      "translation": "钥匙"
    }
  }
}
```

`ITEM` 的值应从运行时来源、屏幕内容或游戏状态中解析；不能把某次获得的“钥匙”永久写入模板。

## 8. 生命周期模型

### 8.1 创建

检测到一次新的文本生产事务时创建新的 `instanceId`。

### 8.2 保持

只要某个 instance 的来源格子仍然投影到当前屏幕，它就保持活跃。后续出现的新 instance 不得自动终止旧 instance。

### 8.3 结束

来源格子从当前屏幕消失后，翻译应立即从 scene 删除。解码器返回、NPC 对话流程结束或经过固定帧数，都不能取代当前屏幕可见性成为最终显示规则。

### 8.4 同 record 多 instance

同一个 record 可能：

- 被重复说出；
- 被多个 decoder invocation 分段写入；
- 在旧窗口尚未消失时再次出现。

显示 grouping 可以跨 fragment 汇总同一 record 的可见格子；生命周期诊断仍应保留涉及的 `instanceIds`。

## 8.5 问题边界与 Case 分类

本文的核心模型是一个**基于 Nametable 当前可见状态的识别与翻译模型**。它不负责从 ROM 字节、解码器调用或 RAM 搬运中推导 `recordId`；如何取得 record 和 provenance 属于模型之前的输入准备阶段。

可以把完整链路分成五层：

```text
ROM / 翻译包
    │
    ▼
[A Record 前处理]
确定 record 边界、recordId、glyphIndex、sourceOffset、模板与参数定义
    │
    ▼
[B 运行时来源采集与传播]
把 decoder / RAM / PPU write 关联到 recordId、instanceId、glyphIndex
    │
    ▼
[C Nametable 可见模型]              ← 本文核心 assumption
两页 CIRAM + scroll 投影 + 当前可见 cell + 遮挡 + grouping + 生命周期
    │
    ▼
[D 译文投影与布局]
把可见原文区间映射为译文区间，并决定位置、换行和尺寸
    │
    ▼
[E 发布、调试与覆盖率]
帧末发布、性能、调试显示、未翻译与未知内容统计
```

### 核心模型的输入契约

Nametable 模型可以假定上游尽可能为每个物理格子提供以下信息：

```text
(physicalPage, cellAddress, tileValue,
 recordId?, instanceId?, glyphIndex?, sourceOffset?, writeGeneration?)
```

其中问号表示来源可能缺失。核心模型负责回答“哪些格子现在可见、属于哪个可见 block、译文应该显示多久和放在哪里”，但不应承担“这个 ROM 地址到底属于哪个 record”的主要责任。若 `recordId` 缺失，核心模型只能把格子标为 unknown，或调用一个明确隔离的 fallback；fallback 不是 Nametable 模型的基本假设。

### Case 分类表

| 层级 | 主要 Cases | 这一层负责的问题 |
|---|---|---|
| A Record 前处理 | 13、14、22、23、29、32 | record 边界、共享字节、分支、模板参数、翻译包内容和候选索引 |
| B 运行时来源采集与传播 | 6、7、8、15、17、18、33 | 从 decoder/sourceOffset/复制链取得并传播 record、instance 与 glyph 身份 |
| C Nametable 可见模型 | 1–5、9–11、16、19–21、24–25、30 | 页面投影、可见性、遮挡、block、instance 生命周期和屏幕结构 |
| D 译文投影与布局 | 12、27、28 | 可见原文区间到译文区间的映射，以及译文尺寸和排版 |
| E 发布与调试 | 26、31 | 帧级发布、延迟和调试层 |

部分 Case 跨层，这是正常的。例如 Case 6 的“fragment 属于哪个 record/instance”由 B 层决定，而“同一 record/instance 的多个可见 fragment 如何合并”由 C 层决定。

### 按问题类别阅读的目录

Case 编号保持不变，避免已有讨论、截图和测试引用失效。阅读时按以下顺序查看，可把同类问题放在一起比较。

#### A Record 前处理

- [Case 13 共享前缀或后缀](#case-13共享前缀或后缀)
- [Case 14 相邻分支文本](#case-14相邻分支文本)
- [Case 22 运行时 ITEM](#case-22运行时-item)
- [Case 23 参数只存在于游戏状态](#case-23参数只存在于游戏状态)
- [Case 29 错误词汇命中](#case-29错误词汇命中)
- [Case 32 已识别但没有译文](#case-32已识别但没有译文)

#### B 运行时来源采集与传播

- [Case 06 同 record 多 fragment](#case-06同-record-多-fragment)
- [Case 07 glyphIndex 缺号](#case-07glyphindex-缺号)
- [Case 08 整行 provenance 丢失](#case-08整行-provenance-丢失)
- [Case 15 浊音与半浊音](#case-15浊音与半浊音)
- [Case 17 相同 tile 的无来源重写](#case-17相同-tile-的无来源重写)
- [Case 18 PPU copy 与 redraw](#case-18ppu-copy--redraw)
- [Case 33 完全未识别](#case-33完全未识别)

#### C Nametable 可见模型

- [Case 01 两个 Nametable 页面](#case-01两个-nametable-页面)
- [Case 02 离屏准备后切换](#case-02离屏准备后切换)
- [Case 03 文本解码结束但窗口仍在](#case-03文本解码结束但窗口仍在)
- [Case 04 窗口关闭但翻译残留](#case-04窗口关闭但翻译残留)
- [Case 05 连续两条对话共存](#case-05连续两条对话共存)
- [Case 09 上层窗口遮挡下层对话](#case-09上层窗口遮挡下层对话)
- [Case 10 同一行中部被遮挡](#case-10同一行中部被遮挡)
- [Case 11 长对话滚动](#case-11长对话滚动)
- [Case 16 重复字符](#case-16重复字符)
- [Case 19 道具列表](#case-19道具列表)
- [Case 20 商店价格与名称](#case-20商店价格与名称)
- [Case 21 是与否菜单](#case-21是否菜单)
- [Case 24 子窗口覆盖底层菜单](#case-24子窗口覆盖底层菜单)
- [Case 25 菜单构建中的半成品](#case-25菜单构建中的半成品)
- [Case 30 启动时幽灵文字](#case-30启动时幽灵文字)

#### D 译文投影与布局

- [Case 12 日中语序不同](#case-12日中语序不同)
- [Case 27 翻译比原文长](#case-27翻译比原文长)
- [Case 28 多行中文高度不足](#case-28多行中文高度不足)

#### E 发布与调试

- [Case 26 快速操作造成滞后](#case-26快速操作造成滞后)
- [Case 31 调试框与译文重叠](#case-31调试框与译文重叠)

### 对 Case 5 到 Case 8 的重新定位

- **Case 5 连续两条对话共存：C 层问题。** 假定上游已经给出 I1、I2，Nametable 模型必须让两个可见 instance 独立存在、独立消失。
- **Case 6 同 record 多 fragment：B 与 C 的接口问题。** B 层先判断 F1、F2 是否属于同一 `recordId + instanceId`；C 层只负责把已带正确身份、且当前可见的格子合成一个 block。C 层不应仅凭空间相邻猜测两个 fragment 的 record。
- **Case 7 glyphIndex 缺号：根因通常在 B 层，容错在 C 层。** 来源传播漏掉索引是上游问题；但在 record 身份仍明确且没有真实遮挡证据时，C 层不应把缺号误判为多个可见 block。
- **Case 8 整行 provenance 丢失：主要是 A/B 层问题。** 第二行没有 `recordId` 时，Nametable 核心只能看到一组 unknown cells。`sourceOffset -> recordId + glyph range` 候选方案属于 record 前处理索引与运行时来源恢复，不属于 Nametable grouping 算法。恢复来源后，C 层才负责把第二行纳入原 instance 或显示为相应 block。

因此，评审 Case 8 时应先问“上游能否恢复可靠来源”，而不是先修改 Nametable grouping。只有在上游无法提供来源时，才讨论是否增加独立、低置信度的屏幕内容 fallback。

## 8.6 候选模型：可见 Glyph、长度映射与 Fallback

本节记录当前讨论形成的候选模型，供后续 Case 评审使用。它尚未替换现有实现，也不表示具体阈值和数据结构已经决定。

### 8.6.1 总体规则

模型仍遵守：**屏幕上显示什么，我们翻译什么。**

正常路径继续依赖 `recordId`、`instanceId` 和 record 内字符位置；遮挡、滚动或窗口关闭只改变当前可见字符集合，不应仅因此创建新的 instance。模型优先保证顶层文本准确。被顶层窗口遮挡的底层文本只显示其当前可见部分，原文与译文之间允许使用近似、单调的长度映射，不强求逐词语义对齐。

### 8.6.2 Record token 与可见 glyph

record 中的普通字符、空格、换行和结束符都可以占用连续的 `tokenIndex`，但只有真正写入 Nametable 的字符才产生可见 glyph/cell。

```text
R0 R1 R2 R3 R4 Enter5 R6 R7 R8 Enter9
R10 R11 Space12 R13 Enter14 R15 R16 R17 R18 End19
```

- 普通字符：参与长度映射，并可能产生屏幕 glyph；
- `Space`：根据游戏行为作为可见间隔或仅作为布局 token；
- `Enter`：长度权重为 0，并构成 hard grouping boundary；
- `End`：长度权重为 0，表示 record 结构结束，但不直接决定屏幕译文消失。

因此可分别使用 `tokenIndex` 表示 record 流位置，使用 `glyphId` 或 glyph occurrence 表示具体屏幕字符。

### 8.6.3 基于长度的原文到译文映射

设某个 source segment 的有效原文长度为 `N`，对应翻译长度为 `M`。默认使用单调边界函数：

```text
P(i) = round(i * M / N)
Ri -> T[P(i) .. P(i + 1))
```

当 `M < N` 时，部分原文字符自然映射为空；当 `M > N` 时，一个原文字符可以对应多个翻译字符。控制符权重为 0，不消耗翻译字符。

```text
Source: R0 R1 R2 R3 R4 R5 R6 R7
Target: T0 T1 T2 T3 T4

可能得到：
R0 -> T0    R1 -> 空    R2 -> T1    R3 -> T2
R4 -> 空    R5 -> T3    R6 -> 空    R7 -> T4
```

优先按换行、翻译包 segment 或可选人工锚点分段计算，避免整条长 record 的舍入误差持续累积：

```text
人工 mapping
    ↓ 没有
分行或分段长度 mapping
    ↓ 没有
整条 record 长度 mapping
```

### 8.6.4 当前可见字符的 grouping

先根据当前帧的两页 Nametable、scroll、layer 和遮挡关系确定真正可见的 cells，再按以下条件建立 visible groups：

1. `recordId` 相同；
2. `instanceId` 相同；
3. token 顺序连续或允许跨过明确的零宽控制 token；
4. 不跨越 `Enter` 等 hard boundary；
5. 屏幕位置属于同一视觉流；

窗口边界和顶层遮挡不作为 hard constraint。模型只记录可见 fragments 之间的空间与时间 gap，不假设 gap 是由窗口、遮挡、空白还是来源丢失造成；这些信息如果可得，只能作为软评分。

因此 grouping 不是单纯的 index range，而是可见 glyph 的空间连通分量。假设 `R1 R2 R3 R7 R8` 被遮挡：

```text
遮挡前：R0 R1 R2 R3 R4 Enter | R6 R7 R8 Enter
遮挡后：R0          R4 Enter | R6       Enter

visible groups：{R0}、{R4}、{R6}
```

每个 visible group 取得其 source token 对应的目标区间，合并、去重并按 target index 排序。由于长度映射为单调且每个 source 区间拥有确定的 target slice，同一目标字符不应同时复制到两个 visible groups。group 的显示 bounds 只来自当前可见 cells，不使用被遮挡 cells 扩大范围。

### 8.6.5 有稳定身份时的正常路径

```text
当前可见 Nametable cells
        ↓
按 recordId + instanceId 分区
        ↓
按 hard boundary、空间连续性和遮挡形成 visible groups
        ↓
使用 source-to-target 长度 mapping 取得每组译文
        ↓
以该组可见 cells 为锚点进行布局
        ↓
帧末发布 scene
```

同一 instance 的 group 可以随遮挡分裂，并在遮挡消失后重新合并。分裂和合并不自动改变 `instanceId`。

### 8.6.6 无 recordId 时的临时 text grouping

两个 invalid `recordId` 不能因为值相同就被认为属于同一条 text。无稳定来源的字符先形成独立的临时身份，例如 `screenTextInstanceId`。它表示“这些字符从屏幕行为看，很可能属于同一次文本显示”，不是正式 provenance。

初始 grouping 可以综合：

- 同一行的空间连续性、字符编码和 palette；
- 相邻行的缩进、行距与阅读顺序；
- 同一帧或相近时间的写入；
- write sequence、PPU 地址变化和可能的 producer context；
- 字符是否一起出现、滚动和消失；
- 上层窗口造成的已知 gap。

每个临时 text 应保存有序 fragments，而不是立即删除间隙后拼成一个字符串：

```text
screenTextInstanceId = U17
fragments = ["ここは", "みせだ", "なにか"]
gaps      = [known-cover, unknown-gap]
```

### 8.6.7 翻译包 fallback 检索

fallback 依次尝试：

1. **完整匹配**：当前 run 与翻译包 record 或独立短词完全一致；
2. **record 内连续子串匹配**：可见后半句命中某个 record 的唯一 source range；
3. **有序多 fragment 匹配**：多个可见 fragment 在同一 record 中按屏幕顺序出现，中间允许存在 gap；
4. **受限上下文匹配**：已有稳定 record、窗口或场景信息时，只在相关候选中查询。

候选评分至少考虑匹配覆盖率、完整边界、fragment 顺序、分行/控制符一致性、窗口和时间上下文，以及候选歧义。结果分为：

- 高置信度：恢复推断出的 `recordId + source range`，进入正常长度映射；
- 中置信度：只显示可靠的局部翻译，不升级为正式 record；
- 低置信度：保持 unknown，不显示翻译。

### 8.6.8 Observed 与 Inferred provenance

fallback 成功后仍需区分直接观测来源和内容推断来源：

```text
ObservedProvenance  = decoder / sourceOffset / copy chain 直接证明
InferredProvenance  = screen fragments + translation package 匹配推断
```

`InferredProvenance` 应保留 confidence、匹配 source ranges、候选数量和评分原因。fallback 可以恢复 `recordId` 与 source range，但不能仅凭内容自动证明原来的 `instanceId`。默认继续使用临时 `screenTextInstanceId`；只有 record、窗口、时间和生命周期证据都一致时，才考虑与已有正式 instance 合并。

### 8.6.9 当前尚未决定的细节

- 长度映射使用四舍五入、floor/ceil 还是预计算边界表；
- `Space` 的长度权重和是否构成 group gap；
- 同一行允许跨越多大的空格；
- 跨行组成同一 `screenTextInstanceId` 的时间和空间阈值；
- fallback 高、中、低置信度的具体阈值；
- 推断来源何时允许升级并合并到正式 instance；
- 日中语序差异明显的 record 是否需要人工 segment；
- 长度 mapping 在多个分离 group 上的舍入与边界稳定规则。

## 8.7 已知来源与未知来源的统一算法

本节保留上一轮 provenance-first 方案，用于历史对照和 Case 分析。下一版实现的主线已改为 8.8 节的 Nametable-first 算法。

本节把稳定 provenance 路径与 unknown fallback 路径整合为一个可实现的逐帧算法。核心思想是：**已知来源是固定锚点，未知来源产生候选；两者经过统一约束求解后生成当前 scene。**

### 8.7.1 输入与输出

离线输入：

```text
TranslationPackage
  records[]
    recordId
    sourceTokens[]
    translationTokens[]
    controlBoundaries[]
    optionalManualSegments[]
```

运行时输入：

```text
FrameSnapshot
  frameNumber
  visibleCells[]
    cellId / physicalPage / screenX / screenY
    tileValue / decodedCharacter
    recordId? / instanceId? / tokenIndex?
    provenanceKind? / writeGeneration? / writtenFrame?
```

输出：

```text
TranslationScene
  blocks[]
    blockId
    cells[]
    sourceFragments[]
    translatedText
    bounds
    identityStatus
    confidence
```

`identityStatus` 至少区分：

```text
Observed          // 可靠 provenance
InferredRecord    // fallback 唯一或高置信度恢复 record + source range
InferredPhrase    // record 不唯一，但所有候选给出同一局部翻译
Unknown           // 不能安全翻译
```

### 8.7.2 离线阶段：编译翻译包

每次加载翻译包时完成：

1. 将 record 解析为连续 `sourceTokens`；普通字符、`Space`、`Enter`、`End` 均保留 `tokenIndex`。
2. 将浊点等多个物理 tile 合成为 logical glyph，避免长度 mapping 按 tile 数重复计数。
3. 生成 source-to-target 边界表；优先人工 mapping，其次分行/分段长度 mapping，最后整条 record 长度 mapping。
4. 生成强边界 segment（`Enter`/`End`）、空格子 segment、翻译包显式短词以及受限长度的连续子串。
5. 建立完整 segment trie、任意 offset/substring 索引和首字符倒排索引。
6. 将 source phrase 相同且局部译文相同的候选归并为 `TranslationEquivalenceClass`。
7. 记录每个 phrase 的候选 record 数量、source ranges 和唯一性统计，供运行时评分。

离线条目可以表示为：

```text
PhraseIndexEntry {
  sourceTokens
  recordId
  sourceRange
  segmentId
  boundaryBefore
  boundaryAfter
  targetRange
  translationClassId?
  globalOccurrenceCount
}
```

### 8.7.3 运行时阶段 A：构建当前可见集合

1. 保存两页物理 Nametable provenance。
2. 使用当前 scroll/mirroring 投影为屏幕 cells。
3. 只保留当前帧真正显示的 cells。
4. 将 cells 分为 `ObservedCells` 与 `UnknownCells`。
5. 当前帧消失的 cells 不进入 scene；decoder 是否仍运行不影响此判断。

```text
VisibleCells
  ├── ObservedCells：recordId + instanceId + tokenIndex 可靠
  └── UnknownCells：缺少可靠 record 或 instance
```

### 8.7.4 运行时阶段 B：处理已知来源

Observed cells 按 `recordId + instanceId` 分区，再根据 hard boundary、屏幕阅读顺序和空间连续性形成 `ObservedGroup`。`Enter` 强制断开；普通 index 缺号本身不证明遮挡，需要同时检查实际 screen cells。

```text
ObservedGroup {
  recordId
  instanceId
  cells[]
  sourceRanges[]
  targetRanges[]
  confidence = 1.0
}
```

Observed provenance 是固定锚点：fallback 不得修改其身份。unknown candidate 可以引用邻近 observed cells 作为证据，但只能占用 unknown cells。

### 8.7.5 运行时阶段 C：构建 unknown screen graph

每个 unknown cell 是一个节点；边只表示一种可能的阅读后继关系，不表示两个节点已经属于同一条 text。

```text
ScreenEdge {
  fromCell
  toCell
  relation: Right | NextLine | Gap
  deltaX / deltaY
  frameDelta?
}
```

模型不要求识别窗口，也不把顶层遮挡作为 hard constraint。对于两个分离 fragments，只保存它们的顺序、距离和 gap：

```text
FragmentGap {
  deltaX
  deltaY
  skippedCellCount
  interveningMatchedCells
  reason = Unknown
}
```

### 8.7.6 运行时阶段 D：生成 unknown 候选

从每个 unknown cell 的 decoded character 查询离线索引，并沿 screen graph 扩展。候选类型按优先级包括：

1. `KnownGapFill`：左右 observed anchors 属于同一 record/instance，候选 source range 正好填补中间 gap；
2. `FullSegment`：屏幕 fragment 完整匹配独立 segment；
3. `TranslationEquivalentPhrase`：多个 record 候选不唯一，但局部译文完全一致；
4. `UniqueSubstring`：连续 screen fragment 在翻译包中唯一命中；
5. `OrderedMultiFragment`：多个 fragments 在同一 record 中按顺序命中，中间允许 source 和 screen gap；
6. `AmbiguousSubstring`：存在多个不同译文候选，仅用于诊断，不默认显示。

统一候选结构：

```text
MatchCandidate {
  candidateId
  claimedUnknownCells[]
  observedAnchorCells[]
  screenFragments[]
  gaps[]

  recordId?
  instanceId?
  sourceRanges[]
  targetRanges[]
  translationClassId?
  translatedText?

  matchType
  evidence[]
  score
  confidence
}
```

### 8.7.7 硬约束

统一求解器只保留下列 generic hard constraints：

1. **Cell 排他**：一个 unknown cell 最多由一个最终候选占用。
2. **Observed 不可冲突**：候选不能改变可靠 observed cell 的 `recordId/instanceId/tokenIndex`。
3. **字符与顺序一致**：screen fragments 必须以相同顺序出现在候选 source ranges 中。
4. **合法 source 结构**：候选必须来自一个合法 record/source range 或明确的 translation equivalence class，不能任意拼接不同 records。

以下内容不作为 hard constraints：

- 是否位于同一个窗口；
- 是否跨过顶层窗口；
- 是否位于同一个矩形；
- gap 的具体成因。

这些信号如果存在，只能进入软评分。

### 8.7.8 候选评分与优化目标

候选基础得分考虑：

- known gap fill 与 observed anchors 一致性；
- 完整 segment、完整边界和唯一子串；
- 多个 record 是否产生相同局部翻译；
- fragment 覆盖长度与顺序；
- 换行、空格和控制边界的一致程度；
- gap 数量、跨度和跨行次数；
- 写入时间、write sequence 和跨帧稳定性；
- 与其他高置信度候选的交叉或不必要合并；
- 候选数量及译文歧义。

优化优先级采用字典序，而不是单纯最大化覆盖率：

```text
1. 最大化可靠性和唯一性
2. 最大化与 Observed anchors 的一致性
3. 最大化跨帧稳定性
4. 在前三项相近时最大化未知 cell 覆盖率
5. 最小化 fragment 数、gap 数和不必要合并
```

不应给 unmatched cells 过高惩罚；允许保留 `Unknown` 是模型安全性的一部分。

### 8.7.9 求解策略

第一版不需要引入通用 ILP/SAT 求解器，可以使用分层 greedy + bounded beam search：

```text
selected = observedGroups
occupied = observedCells

依次处理：
  1. KnownGapFill
  2. 唯一 FullSegment
  3. TranslationEquivalentPhrase
  4. UniqueSubstring
  5. OrderedMultiFragment

对于每一级：
  - 按 score/confidence 排序
  - 跳过 cell 冲突候选
  - 对相近得分分支保留有限个 beam states
  - 如果最佳与次佳差距不足，保持 unknown
```

后续只有在日志证明 greedy/beam 经常产生局部最优问题时，再考虑 weighted set packing、ILP 或 SAT。

### 8.7.10 统一生成翻译 block

求解完成后，将 observed groups 和 selected inferred candidates 转换为统一 `ResolvedGroup`：

```text
ResolvedGroup {
  identityStatus
  recordId?
  instanceKey
  cells[]
  sourceRanges[]
  targetRanges[]
  translatedText
  confidence
}
```

翻译生成规则：

- `Observed` / `InferredRecord`：使用 source ranges 对应的长度 mapping；
- `InferredPhrase`：直接使用 translation equivalence class 的局部译文；
- `Unknown`：不生成用户译文，只进入诊断；
- 所有 bounds 只由当前组的可见 cells 计算；
- target ranges 合并、去重并按 target index 输出；
- 相同 target token 不得复制到两个最终 blocks，除非翻译包显式允许。

### 8.7.11 跨帧生命周期

Observed group 使用正式 `instanceId`。unknown/inferred group 使用临时 `screenTextInstanceId`，根据 cell 重叠、字符内容、空间移动和候选一致性跨帧关联。

```text
FallbackTrack {
  screenTextInstanceId
  previousCells[]
  selectedCandidateIds[]
  firstSeenFrame
  lastSeenFrame
  confidence
}
```

跨帧规则：

- 相同 cells 和字符保持原候选，给予稳定奖励；
- 新写入或字符改变允许重新求解；
- 遮挡造成 group 分裂不自动创建新的正式 instance；
- cells 消失后相应 block 从下一份 scene 移除；
- inferred record 只有在 record、时间和 observed 生命周期证据一致时才能并入正式 instance。

### 8.7.12 每帧伪代码

```text
ResolveFrame(frame, packageIndex, previousState):
    visible = ProjectVisibleNametable(frame)
    observedCells, unknownCells = PartitionByProvenance(visible)

    observedGroups = BuildObservedGroups(observedCells)
    screenGraph = BuildUnknownScreenGraph(unknownCells)

    candidates = []
    candidates += GenerateKnownGapFill(observedGroups, unknownCells)
    candidates += MatchFullSegments(screenGraph, packageIndex)
    candidates += MatchTranslationClasses(screenGraph, packageIndex)
    candidates += MatchUniqueSubstrings(screenGraph, packageIndex)
    candidates += MatchOrderedFragments(screenGraph, packageIndex)

    ScoreCandidates(candidates, observedGroups, previousState)
    selected = SolveNonConflictingCandidates(candidates, observedCells)

    resolved = MergeObservedAndInferred(observedGroups, selected)
    blocks = ProjectTranslationsByLength(resolved, packageIndex)
    scene = LayoutVisibleBlocks(blocks)

    nextState = UpdateTracks(previousState, resolved, frame)
    return scene, nextState, diagnostics
```

### 8.7.13 建议实现顺序

**阶段 1：离线索引与统一数据结构**

- record tokenization 和 logical glyph；
- 分段长度 mapping 边界表；
- full segment index；
- translation equivalence class；
- `ResolvedGroup`、`MatchCandidate` 和诊断结构。

**阶段 2：已知来源路径迁移**

- 将现有 observed grouping 输出转换为 `ResolvedGroup`；
- 验证现有已处理 Cases 不回退；
- 暂不启用 unknown 优化。

**阶段 3：安全 fallback MVP**

- `KnownGapFill`；
- 唯一 `FullSegment`；
- `TranslationEquivalentPhrase`；
- cell 排他和 observed 冲突检查；
- 低置信度保持 unknown。

**阶段 4：子串与多 fragment**

- 任意 offset substring index；
- `UniqueSubstring`；
- `OrderedMultiFragment`；
- gap penalty 和 fragment complexity penalty。

**阶段 5：跨帧稳定与性能**

- `FallbackTrack`；
- 候选缓存和增量更新；
- bounded beam search；
- 性能计数、候选解释和回归测试。

这一顺序先保护现有稳定来源路径，再逐步打开 unknown fallback，便于针对每类候选单独测量误译率。

### 8.7.14 统一算法仍未完全支持的 Cases

本节描述的是算法设计边界，不代表当前代码已经实现前述能力。统一算法实现后，仍需要以下外部机制或后续增强。

#### 没有核心解决方案

| Case | 限制 | 仍需机制 |
|---|---|---|
| 17 相同 tile 的无来源重写 | 最终 tileValue 相同，单看画面无法判断生产者已经变化 | PPU write event、writeGeneration、无来源写入清除旧 provenance |
| 22 运行时 ITEM | 参数可能不是普通 source phrase | 翻译模板与 instance 参数解析 |
| 23 参数只存在于游戏状态 | 屏幕字符不足以恢复对象 | RAM/game-state 读取或 decoder 参数 |
| 31 调试框与译文重叠 | 属于显示层问题 | UI 图层和调试标签布局 |
| 32 已识别但没有译文 | 翻译包没有可输出内容 | 补充翻译包；保持 recognized/untranslated |

#### 只能近似支持

- **Case 12 日中语序不同**：长度 mapping 是单调近似；局部遮挡或滚动时可能取得错误中文区间，需要可选人工 segment mapping。
- **Case 27 翻译比原文长**：算法能确定内容与锚点，但仍需要换行、字号和边缘约束。
- **Case 28 多行中文高度不足**：需要布局引擎根据译文实际尺寸扩展 bounds。

#### 有 fallback 路径但不保证成功

- **Case 8 整行 provenance 丢失**：唯一 segment、substring 或 ordered fragments 命中时可以恢复；短句多义时保持 unknown。
- **Case 18 PPU copy/redraw**：可以按内容重新匹配，但无法保证恢复原正式 instance；稳定方案仍是复制链追踪。
- **Case 29 错误词汇命中**：全帧约束可以降低误匹配，不能消除语言和短子串本身的歧义。
- **Case 33 完全未识别**：翻译包缺失、字符解码错误、片段过短或候选译文不一致时仍无法安全显示。

#### 依赖 Record 前处理正确

- **Case 13 共享前缀或后缀**：要求翻译包保存正确的 record 身份、共享 span 和合法 source ranges。
- **Case 14 相邻分支文本**：要求前处理或运行时 provenance 区分实际执行分支。
- **Case 15 浊音与半浊音**：要求在长度 mapping 前正确构建 logical glyph；不同游戏可能需要组合规则配置。

#### 需要实现期重点验证

- **Case 19 道具列表**：需验证相邻多行不会被错误合并，名称与数量仍然对应。
- **Case 20 商店价格与名称**：文本和数值来自不同管道，仍需更高层的 screen-layout composition。
- **Case 24 子窗口覆盖底层菜单**：不依赖窗口识别，但必须验证 gap/fragment penalty 足以抑制远距离错误合并。

#### 属于运行机制而非匹配模型

- **Case 25 菜单构建中的半成品**：要求只在帧末求解和发布。
- **Case 26 快速操作造成滞后**：候选缓存、增量计算和 beam 宽度需要性能验证。
- **Case 30 启动时幽灵文字**：启动、换 ROM 和断开连接时必须显式清空 scene 与 tracks。

因此，统一算法实现后的主要剩余缺口是：运行时模板参数、write/copy provenance、布局引擎、record 前处理质量，以及无法消除的短文本歧义。

## 8.8 下一版主算法：Nametable 文本分组与翻译包反向匹配

> 设计决定（2026-10-20）：下一版实现以本节为主线。它不再要求每个屏幕字符都成功传播 `recordId / instanceId`，而是先从当前 Nametable 中确定性解码字符和空间结构，再用翻译包反向判断文本来源。旧 provenance 路径保留为可选的高信度证据和调试信息，不再是能否翻译的前提。

### 8.8.1 目标与基本假设

主规则仍然是：**屏幕上显示什么，就只翻译什么。**

算法依赖三类输入：

1. 当前帧 PPU/Nametable 中的真实 tile、palette、屏幕坐标和解码字符；
2. 翻译包中的 record、source tokens、换行/空格/控制符和译文；
3. 可选证据：`recordId`、`instanceId`、`glyphIndex`、写入时间、跨帧 track 和视觉边界。

游戏专属的 decoder 或 provenance 配置可以提升准确度，但基本分组和匹配必须能在它们缺失时工作。

### 8.8.2 总体流程

```text
当前 PPU/Nametable
        │
        ▼
可见 cell 与确定字符解码
        │
        ▼
同行 TextLine 提取
        │
        ▼
生成连续多行 TextBlock candidates
        │
        ├── 每行单独查询 Top-K source ranges
        ├── 计算相邻行的来源一致性与连续性
        └── 合并文本再做整体匹配
        │
        ▼
全帧非重叠优化
        │
        ├── 翻译包命中 ──► 原文到译文投影
        └── 无安全命中 ──► 保持原文或进入本地翻译 fallback
        │
        ▼
当前帧 Translation Scene
```

### 8.8.3 第一阶段：构建 ScreenCell

先根据实时 scroll、mirroring 和屏幕裁切，将物理 Nametable 投影到当前帧。每个可能的文字格子保存：

```text
ScreenCell {
  cellId
  row / column
  screenX / screenY
  tileId
  decodedCharacter?
  paletteId
  renderedGlyphMask
  backgroundSignature
  recordId? / instanceId? / glyphIndex?   // 可选，不是必需
  firstSeenFrame / lastChangedFrame
}
```

`decodedCharacter` 来自游戏字符表、CHR 字形表或翻译包配置。字符无法解码时，该 cell 可以作为视觉边界或 unknown glyph，但不应随意加入文本查询。

### 8.8.4 第二阶段：提取单行 TextLine

在同一 tile row 上，按从左到右连接可解码字符。行内可允许少量空格，但不能跨过明确的视觉边界或大段非文字区域。

行内证据包括：

- 字符在同一 baseline；
- 列坐标连续，或只差可解释的 space；
- palette 和 background signature 相似；
- 字形、假名、标点和数字类型可以构成合法文本；
- 相邻 cell 之间没有对话框线、图标或明显背景中断。

输出不是最终 block，而是保守的单行单元：

```text
TextLine {
  lineId
  orderedCells[]
  rawText
  normalizedText
  bounds
  visualSignature
  optionalProvenanceSummary
}
```

### 8.8.5 第三阶段：生成多行 TextBlock candidates

多行 block 不直接由窗口边界决定。算法只在屏幕上下相邻、阅读顺序连续的 `TextLine` 之间建立可能的连接。

对 `L1, L2, L3` 只生成连续组合：

```text
[L1] [L2] [L3]
[L1,L2] [L2,L3]
[L1,L2,L3]
```

不允许跳过 `L2` 直接生成 `[L1,L3]`。第一版可将最大高度限制为 4 行，防止候选数爆炸。

两行之间的初始 `lineLinkScore` 由以下软证据组成：

- 行距是否规则；
- 水平范围是否重叠，左缩进是否合理；
- palette/background 是否连续；
- 上一行结尾与下一行开头是否具有语言连续性；
- 两行是否在接近时间出现，或表现为同一次逐字写入；
- 中间是否存在明确框线或不可穿越的图形边界。

明确视觉边界可作为 hard break；没检测到边界不等于已证明两行属于同一 block。

### 8.8.6 第四阶段：逐行查询来源

对每个 `TextLine` 单独查询翻译包，保留 Top-K 候选，不过早选定唯一 record：

```text
LineMatch {
  lineId
  recordId
  sourceStart / sourceEnd
  matchType
  matchedTokenCount
  editCost
  boundaryCompatibility
  occurrenceCount
  score
}
```

例如：

```text
L1 -> Record A [10..18]  0.96
L2 -> Record A [20..29]  0.94
L3 -> Record A [31..39]  0.91
```

“同一 record”不足以证明它们属于同一 block。还必须检查 source ranges 是否按顺序且距离合理。两个 range 之间只包含 `Enter`、`Space` 或少量可解释的缺失 glyph 时，给予高连续分。

短行可能在大量 records 中出现，因此必须对 `occurrenceCount` 施加歧义惩罚。一个只有两个假名的行可以提供辅助证据，但不应单独决定 block 或译文。

### 8.8.7 第五阶段：连接后的整体复核

如果相邻行的 Top-K 结果中存在共同 record，且 source ranges 按屏幕阅读顺序连续，就生成一个强 block hypothesis。然后将多行文本连接并再次查询：

```text
normalize(L1) + Enter + normalize(L2) + Enter + normalize(L3)
```

整体复核时同时允许翻译包中的真实 `Enter`、可忽略空格和受限的少量 gap。它的作用是将多个单行的弱命中变成一个长文本的唯一强命中。

```text
L1 单独：多义       L2 单独：多义       L3 单独：多义
       \                 |                 /
        \---- 共同 Record A + ranges 连续 ----/
                           |
                           v
                    合并后整体查询
                           |
                 Record A [10..39] = 0.98
                           |
                           v
                    确认多行 TextBlock
```

需要单独记录“合并增益”：

```text
combinedGain = combinedMatchScore
             - Aggregate(individualLineScores)
```

如果合并后没有提高唯一性或匹配质量，就不应只因为两行靠得近而强制合并。

### 8.8.8 BlockCandidate 与评分

```text
BlockCandidate {
  candidateId
  lineIds[]
  cells[]
  bounds
  normalizedLines[]

  lineMatches[]
  recordId?
  sourceRanges[]
  translatedText?

  visualScore
  temporalScore
  individualMatchScore
  sourceContinuityScore
  combinedMatchScore
  ambiguityPenalty
  boundaryPenalty
  totalScore
}
```

概念上：

```text
totalScore =
    visual continuity
  + temporal continuity
  + individual line evidence
  + same-record agreement
  + ordered source-range continuity
  + combined match quality
  + combined uniqueness gain
  + optional provenance agreement
  - source ambiguity
  - visual boundary crossing
  - unexplained source/screen gaps
  - unnecessary merge complexity
```

`recordId / instanceId` 如果存在，可以作为强加分或冲突检查；如果不存在，算法仍可依靠字符、source range 和空间/时间证据完成决策。

### 8.8.9 第六阶段：全帧选择

不能独立接受每个高分候选，因为 `[L1,L2]` 与 `[L2,L3]` 会争用 `L2`。最终选择必须满足：

1. 一个 `TextLine` 最多属于一个最终 block；
2. 一个 cell 最多被一个最终 block 占用；
3. 不跨过 hard visual boundary；
4. 只选择连续行组合；
5. 最佳候选与次佳候选差距不足时，保留 unknown 而不猜测。

因为 block 只占用连续的 lines，第一版可使用 weighted interval scheduling / dynamic programming，无需引入通用 ILP。如果同一屏幕中有多个水平区域，先分成不相交的 line columns，再在每个 column 中做 DP。

### 8.8.10 翻译生成和 fallback

对已命中翻译包的 block：

1. 精确 record/range 命中时，使用翻译包的 segment mapping；
2. 只有长度 mapping 时，按 source range 单调投影到 target range；
3. 多行 block 的译文优先整体布局，不强制每一个日文行对应一个中文行；
4. bounds 只由当前可见 cells 计算。

对没有安全命中翻译包的 block，按以下顺序处理：

```text
足够长且置信度高的可见日文
        ↓
查跨帧翻译缓存
        ↓ 未命中
可选的本地日→中翻译器
        ↓
标记为 MachineFallback，不写回正式翻译包
```

过短、包含 unknown glyph 或存在多个不同分组解释的文本，不进入机器翻译，以避免频繁抖动和错译。

### 8.8.11 跨帧稳定

为每个最终 block 建立 `TextBlockTrack`：

```text
TextBlockTrack {
  trackId
  previousLineIds / cells / text
  selectedRecordId?
  selectedSourceRanges[]
  firstSeenFrame / lastSeenFrame
  stableFrameCount
  confidence
}
```

如果字符、位置和候选来源没有实质变化，延续上一帧结果，不重复执行全量模糊查询。逐字对话在文本还在生长时可以暂缓发布，直到：

- 文本稳定若干帧；
- 出现句末或翻译包强边界；
- 长文本已经形成高置信度唯一命中。

当 cells 从屏幕消失时，对应译文必须随当前 scene 消失；track 只用于缓存和身份稳定，不能让不可见文本继续显示。

### 8.8.12 每帧伪代码

```text
ResolveFrame(frame, packageIndex, previousTracks):
    cells = DecodeVisibleNametable(frame)
    textLines = ExtractConservativeTextLines(cells)

    lineMatches = {}
    for line in textLines:
        lineMatches[line.id] = QueryTopK(line.normalizedText, packageIndex)

    blockCandidates = []
    for consecutiveLines in EnumerateConsecutiveLineGroups(textLines, maxLines=4):
        if CrossesHardVisualBoundary(consecutiveLines):
            continue

        candidate = BuildBlockCandidate(consecutiveLines)
        candidate.lineMatches = Collect(lineMatches, consecutiveLines)
        candidate.sourceChains = JoinOrderedCommonSources(candidate.lineMatches)
        candidate.combinedMatches = QueryCombinedText(consecutiveLines, packageIndex)
        ScoreBlock(candidate, frame, previousTracks)
        blockCandidates.append(candidate)

    selectedBlocks = SelectNonOverlappingBlocks(blockCandidates)

    for block in selectedBlocks:
        if block.hasSafePackageMatch:
            block.translation = ProjectPackageTranslation(block)
        else if block.isStableAndSafeForMachineFallback:
            block.translation = QueryCachedLocalTranslator(block)
        else:
            block.translation = None

    scene = LayoutUsingCurrentVisibleBounds(selectedBlocks)
    tracks = UpdateTextBlockTracks(previousTracks, selectedBlocks)
    return scene, tracks, diagnostics
```

### 8.8.13 实现分步

**Phase 1：可见字符与单行基线**

- 只读当前可见 Nametable；
- 输出 `ScreenCell` 和 `TextLine`；
- 用 debug overlay 显示解码字符、line bounds 和分割原因；
- 暂不输出译文。

**Phase 2：翻译包索引与逐行查询**

- 统一 source normalization；
- 建立 full record、line/segment、substring 和首字符索引；
- 为每行输出 Top-K `LineMatch`、source range 和歧义数；
- 先做诊断，不自动 grouping。

**Phase 3：多行 candidates 与整体复核**

- 枚举最多 4 个连续 TextLines；
- 实现共同 record + ordered ranges 链接；
- 实现 combined query 和 `combinedGain`；
- 将候选评分分解显示在调试日志中。

**Phase 4：全帧选择与译文投影**

- 使用 DP 选择不重叠 block；
- 只对唯一性和 margin 达标的候选发布译文；
- 接入 segment mapping 和长度 mapping；
- 对照现有 case 矩阵验证错译、漏译和残留。

**Phase 5：跨帧与本地翻译 fallback**

- `TextBlockTrack` 和增量缓存；
- 逐字写入的稳定发布策略；
- 本地日→中翻译与持久缓存；
- 机器译文明确标记，与翻译包结果分开评估。

### 8.8.14 第一版成功标准

- 在没有任何 record provenance 的普通对话画面中，能稳定提取完整 `TextLine`；
- 三行对话中，逐行候选能通过共同 record 和连续 source ranges 合并成一个 block；
- 两个相邻但无关的文本区域不被错误合并；
- 短词多义时保持 unknown，不用覆盖率强行选择；
- 有 provenance 与无 provenance 时，对同一稳定画面应产生相同的文本分组和译文；
- 候选分数、丢弃原因、source ranges 和最佳/次佳 margin 可通过诊断输出解释。

## 9. 已知 Corner Cases

下表中的“状态”含义：

- 已处理：已有实现和回归测试；
- 部分处理：主要情况可工作，但仍有已知缺口；
- 未处理：需要后续设计或更多运行时证据。

| 情况 | 典型现象 | 根因 | 当前策略 | 状态 |
|---|---|---|---|---|
| 两个 Nametable 页面 | 宝箱、菜单文字完全不出现 | 只观察了一个物理页面或没有实时投影 | 保存两页 CIRAM，按实时 scroll 投影 | 已处理 |
| 离屏准备后切换 | 玩家没感觉切页，但来源突然改变 | 游戏先在不可见页面写窗口 | 每帧重新投影，而非按写入时坐标冻结 | 已处理 |
| 文本解码结束但窗口仍在 | 翻译过早消失 | 把 decoder 生命周期当显示生命周期 | 以可见来源格子为准 | 已处理 |
| 窗口关闭但翻译残留 | 原文消失，翻译仍在 | instance 或 cell 未正确结束 | 当前帧格子消失即移除 scene item | 已处理，继续回归 |
| 连续两条对话共存 | 第二句覆盖第一句译文位置 | record 共用固定 box 或复用 instance | 独立 instance 与实时 bounds | 已处理 |
| 同 record 多 fragment | 一句话只显示一部分 | 每次 decoder invocation 被当成整条生命周期 | 汇总同 record 的当前可见格子 | 已处理 |
| glyphIndex 缺号 | “要买什么？”被拆成几个字 | 来源标签不完整被误判为遮挡 | 同 record、同屏幕行作为 block | 已处理 |
| 整行 provenance 丢失 | 日文整行可见但没有任何翻译框 | 该行所有格子都没有来源；fallback 又无法局部匹配长 record | 尚需局部 record 匹配或来源恢复 | 未处理 |
| 上层窗口遮挡下层对话 | 下层只剩几个分散可见部分 | 同一 record 的格子被覆盖 | 按可见 block 独立投影和摆放 | 部分处理 |
| 同一行中部被遮挡 | 行左右两部分可见，中央被盖住 | 当前按行 grouping 会合并左右部分 | 需要可靠的遮挡证据，不能仅凭索引缺号 | 未处理 |
| 长对话滚动 | 屏幕始终只显示长 record 的一个区间 | 固定 segment 无法表示滚动视图 | 根据可见源范围比例投影译文 | 部分处理 |
| 日中语序不同 | 比例区间对应的中文语义不完全一致 | 两种语言不能逐字符对齐 | 允许近似；后续可加入可选人工锚点 | 部分处理 |
| 共享前缀或后缀 | 不同消息被错误归并 | ROM 文本结构共享字节区间 | record 与 instance 双重身份，不用 tile 值作为身份 | 部分处理 |
| 相邻分支文本 | 两个选择或分支串在一起 | 静态扫描边界不等于运行时消息边界 | 运行时来源、分隔符与可见 grouping 联合判断 | 部分处理 |
| 浊音/半浊音 | `か` 与浊点被分成两个字符 | 修饰符单独占 tile 或写入 | 修饰符继承基础字符语义身份 | 部分处理，需更多游戏验证 |
| 重复字符 | 一个字的来源跳到另一个同字位置 | 用 tile 值代替字符身份 | 使用 instanceId + glyphIndex | 已处理 |
| 相同 tile 的无来源重写 | 地图文字继承旧对话来源 | tile 值相等被误认为同一所有者 | 无匹配生产者的写入清除旧 provenance | 已处理 |
| PPU copy / redraw | 文字可见但一部分来源丢失 | 字符通过复制或未观察路径重绘 | 当前有有限传播；需要逐写入诊断 | 部分处理 |
| 道具列表 | 名称不翻译或被拼成一句话 | 多个独立词条通过运行时列表管道排列 | 稳定来源优先；否则逐 run 查询词汇数据库 | 部分处理 |
| 商店价格与名称 | 名称和数字位置错配 | 文本、数值来自不同管道 | 每个匹配保留自己的 cells 和 bounds | 部分处理 |
| 是/否菜单 | 明明有翻译但不显示 | 短文本缺少稳定来源或 fallback 未收录 | 通用短词记录 + 内容匹配 | 已处理，继续扩包 |
| 运行时 ITEM | 显示固定错误道具 | 把参数值写死在模板 | 模板 + instance 参数 | 已处理基础链路 |
| 参数只存在于游戏状态 | 画面上无法读出具体对象 | 参数没有以独立文字写入 | 允许从运行时状态/解码流记录参数 | 部分处理 |
| 子窗口覆盖底层菜单 | 底层标签仍显示或压住子窗口 | 用矩形窗口决定所有权 | 只按确切来源格子排除 fallback | 部分处理 |
| 菜单构建中的半成品 | 译文短暂闪烁、位置变化 | 一帧内多次中间状态发布 | 帧末合并，只发布最后 scene | 已处理 |
| 快速操作造成滞后 | 翻译晚于游戏 | 高频事件重复匹配和 UI 更新 | 帧级合并、减少重复刷新 | 已优化，仍可继续 |
| 翻译比原文长 | 超出框或位置偏右 | 原框太窄、字体布局策略不一致 | 当前保证可见优先；后续需要通用排版策略 | 部分处理 |
| 多行中文高度不足 | 只显示半句话 | bounds 来自少量来源格子 | block bounds 与文本布局需要解耦或扩展 | 部分处理 |
| 错误词汇命中 | 出现“彩虹水滴”等无关词 | 局部字符对多个数据库候选都成立 | 需要候选评分、上下文和冲突抑制 | 部分处理 |
| 启动时幽灵文字 | 刚打开就出现旧字符 | scene 或窗口状态未清空 | 初始化空 scene，首次可见快照覆盖 | 已处理 |
| 调试框与译文重叠 | 看起来像重复字符 | 调试 metadata 画在内容上 | 调试层应和用户译文视觉分离 | 部分处理 |
| 未翻译 record | 有识别框但没有中文 | 数据库没有译文 | 调试中区分 recognized/untranslated | 待增强 |
| 完全未识别 | 原文可见但没有任何框 | 稳定来源和 fallback 均失败 | 记录未知 screen run，供扩包和诊断 | 待增强 |

### 9.1 Corner Cases 草图索引

草图统一使用以下符号：

```text
[源]  = 有稳定 provenance 的屏幕格子
[?]   = 无稳定来源、等待 fallback 的格子
[遮]  = 被其他窗口覆盖的格子
→ 中文 = 翻译窗口中的结果
×      = 错误结果或不应继续存在的内容
```

#### Case 01：两个 Nametable 页面

```text
物理页 A                    物理页 B
┌────────────┐             ┌────────────┐
│ 地图       │             │ [源][源]钥匙│
└────────────┘             └────────────┘
       └──── PPU 当前显示 B ────┘
屏幕：发现了钥匙。          → 发现了钥匙。

错误模型：只扫描 A → 什么也识别不到
```

#### Case 02：离屏准备后切换

```text
帧 N：屏幕显示 A              离屏 B 正在写入
┌────────────┐              ┌────────────┐
│ 地图       │              │ [源]新窗口 │
└────────────┘              └────────────┘

帧 N+1：scroll 指向 B → 玩家直接看到新窗口
                         → 此时才显示新译文
```

#### Case 03：文本解码结束但窗口仍在

```text
时间 ─────────────────────────────────►
解码器： [运行][结束]
屏幕：   [────── 对话窗口仍然可见 ──────]
翻译：   [────── 应继续显示 ────────────]

错误：解码结束时立刻删除翻译
```

#### Case 04：窗口关闭但翻译残留

```text
关闭前：│ 日文窗口 │  → │ 中文译文 │
关闭后：│   地图   │  → │          │
                         × 中文译文仍残留

正确：最后一个可见来源格子消失 → scene item 消失
```

#### Case 05：连续两条对话共存

```text
屏幕：┌──────────────┐
      │ 第一句 [msg-1]│
      │ 第二句 [msg-2]│
      └──────────────┘

翻译：┌ 第一句译文 ┐  ┌ 第二句译文 ┐
      各自 instance、生命周期和摆放位置
```

#### Case 06：同 record 多 fragment

```text
同一个 record R：
fragment msg-1 → [0][1][2]
fragment msg-2 →          [3][4][5]
                       grouping
                           ▼
当前可见 R → [0][1][2][3][4][5] → 一条译文
```

#### Case 07：glyphIndex 缺号

```text
屏幕同一行： [0][1][?][?][4][5][6]
来源索引：     0  1        4  5  6

错误：按缺号切成「买」│「什」│「什么？」
当前：同 record + 同屏幕行 → 一个 block →「要买什么？」
```

#### Case 08：整行 provenance 丢失

```text
┌────────────────────────────┐
│ [源][源] 这里是武器和防具店 │ → 已翻译（42%）
│ [? ][? ] なにか かうかね？ │ → 当前漏译
└────────────────────────────┘

稳定来源找不到第二行；全记录 fallback 也无法仅凭后半句命中。
```

#### Case 09：上层窗口遮挡下层对话

```text
原下层对话： [0][1][2][3][4][5][6][7][8]
上层窗口：          ┌──────────┐
当前可见：    [0][1]│ [遮][遮] │[7][8]
                    └──────────┘

目标：左、右可见 block 分别投影；遮住的内容不显示。
```

#### Case 10：同一行中部被遮挡

```text
同一 tile 行： [源][源] ┌ 子窗口 ┐ [源][源]
                       └────────┘
当前按行 grouping：└──────── 一个 block ────────┘
风险：译文可能跨过实际不可见的中部。
需要遮挡证据，不能仅凭 glyphIndex 缺号判断。
```

#### Case 11：长对话滚动

```text
完整 record：0──────────────50──────────────100
页面 1 可见：██████████
页面 2 可见：        ██████████
页面 3 可见：                  ██████████

每页仅投影当前可见原文比例对应的译文区间。
```

#### Case 12：日中语序不同

```text
日文： [地点][方向][动作][对象]
中文： [动作][对象][方向][地点]
比例：  20%────40%              ≠ 完整语义边界

结果只能近似；可选人工锚点才能获得精确语义对齐。
```

#### Case 13：共享前缀或后缀

```text
record A：[欢迎光临][武器店]
record B：[欢迎光临][旅店  ]
                 ▲共享前缀

只看 tile 内容 → 容易混淆
recordId + instanceId → 保留各自身份
```

#### Case 14：相邻分支文本

```text
ROM 连续区域： [分支 A][控制符][分支 B][结束]
屏幕实际只走： [分支 A]

错误：静态扫描后把 A+B 同时翻译
目标：运行时来源 + 分隔符 + 当前可见 grouping
```

#### Case 15：浊音与半浊音

```text
逻辑字符：          が
物理 tile：       [か][゛]
来源身份：          └─ 同一个 logical glyph ─┘

错误：[か] 与 [゛] 分别 grouping 或让浊点继承错误字符。
```

#### Case 16：重复字符

```text
文本：  か  か  か
tile： [12][12][12]       数值完全相同
身份： [i0][i1][i2]       glyphIndex 不同

不能用 tile=12 判断它们是同一个字符实例。
```

#### Case 17：相同 tile 的无来源重写

```text
帧 N：  对话写入 tile 12 → [tile 12 / 来源 R]
帧 N+1：地图写入 tile 12 → [tile 12 / 无来源]

数值相同，但生产者不同。
正确：清除旧来源 R；否则地图会继承旧译文。
```

#### Case 18：PPU copy / redraw

```text
带来源缓冲区： [R:0][R:1][R:2]
                    │ copy / redraw
                    ▼
Nametable：       [ ? ][ ? ][ ? ]  文字可见但来源未传播

需要追踪复制链，或由局部内容识别补救。
```

#### Case 19：道具列表

```text
┌ 道具 ────────────┐
│ [药草]      × 2  │ → 药草
│ [火把]      × 1  │ → 火把
│ [钥匙]      × 3  │ → 钥匙
└──────────────────┘

每一行是独立词条，不应合并为“药草火把钥匙”。
```

#### Case 20：商店价格与名称

```text
屏幕行： [竹竿] ........ [10]
来源：   文本管道         数值管道
翻译：   [竹竿]           [10 G]

错误：名称来自第一行，价格却绑定到第二行。
每个匹配必须保留自己的 cells/bounds。
```

#### Case 21：是/否菜单

```text
┌────────┐
│ > はい │ → 是
│   いいえ│ → 否
└────────┘

短词可能没有稳定来源；fallback 需要把每一行作为独立候选。
```

#### Case 22：运行时 ITEM

```text
模板：发现了 {ITEM}。
本次参数：ITEM = かぎ → 钥匙
本次显示：发现了钥匙。

下一次 ITEM = たいまつ → 火把
模板不变，instance 参数改变。
```

#### Case 23：参数只存在于游戏状态

```text
游戏状态：itemId = 03 ───────┐
                              ▼
屏幕模板：发现了 [空槽/图标] → 仍需解析为「钥匙」

如果参数没有独立文字，不能只靠屏幕 OCR；需读取状态或解码流。
```

#### Case 24：子窗口覆盖底层菜单

```text
底层：┌ 命令 ───────────┐
      │ 交谈  状态  道具 │
      │ 楼梯  开门  拿取 │
      └─────────────────┘
上层：       ┌ 是 / 否 ┐
             └─────────┘

只排除被上层实际占用的格子；不能排除整个底层矩形。
```

#### Case 25：菜单构建中的半成品

```text
同一帧内部：
t0：┌框
t1：┌框 + 第一个字
t2：┌框 + 完整菜单

对外只发布帧末 t2；否则译文会闪烁和跳位。
```

#### Case 26：快速操作造成滞后

```text
游戏帧：  A ─ B ─ C ─ D ─ E
旧翻译：  A ──── A ──── C ──── E
                    ▲明显落后

优化：帧内合并、跳过重复匹配、只提交最新 scene。
```

#### Case 27：翻译比原文长

```text
原框：  ┌──── 短日文 ────┐
中文：  ┌────── 更长的中文翻译 ──────┐
                                      × 超出

需要换行、字号或可扩展布局；不能假设中日字符数相等。
```

#### Case 28：多行中文高度不足

```text
来源 bounds：┌──────────┐  只有一行高度
中文译文：   │ 第一行   │
             │ 第二行 × │  被裁掉
             └──────────┘

文本布局高度不能完全等同于少量来源格子的紧边界。
```

#### Case 29：错误词汇命中

```text
屏幕局部字符：「しずく」
候选 A：水滴
候选 B：彩虹水滴
候选 C：某句中的子串

仅“包含”就选择 B → × 错译；需要候选评分和冲突抑制。
```

#### Case 30：启动时幽灵文字

```text
上次退出：scene =「钥匙」
新程序启动：游戏尚未显示文字

错误：黑屏 → ×「钥匙」
正确：初始化 scene = 空，等待第一份当前帧快照。
```

#### Case 31：调试框与译文重叠

```text
┌────────────────────┐
│ recordId 42%       │  调试 metadata
│ 这里是武器和防具店 │  用户译文
└────────────────────┘
        ▲ 两层文字重叠时看起来像乱码或重复

应在视觉上分层，或把 metadata 放在框外。
```

#### Case 32：已识别但没有译文

```text
屏幕： [源][源][源]
识别： recordId = chr-xxxx  ✓
数据库：translation = null
输出： [recognized / untranslated]

它不是识别失败，而是翻译包尚未覆盖。
```

#### Case 33：完全未识别

```text
屏幕：日文清晰可见
稳定来源：无
fallback：无候选
调试框：无

应记录 unknown screen run，区别于“有 record、无翻译”。
```

## 10. “整行来源丢失”问题的候选方案

这是当前最重要的未解决问题之一。

### 候选方案 A：按 sourceOffset 恢复 record 与 glyph

> 状态：待评审，尚未决定实现。

在翻译包构建时生成静态索引：

```text
sourceOffset -> recordId + glyphIndex / glyph range
```

以 `chr-fc-234a` 为例，第二行具有明确来源：

```text
sourceOffset 9050  -> chr-fc-234a / glyph 16..18  （字典 token「なにか」）
sourceOffset 9051  -> chr-fc-234a / glyph 19      （空格）
sourceOffset 9052  -> chr-fc-234a / glyph 20      （か）
sourceOffset 9053  -> chr-fc-234a / glyph 21      （う）
sourceOffset 9054  -> chr-fc-234a / glyph 22      （か）
sourceOffset 9055  -> chr-fc-234a / glyph 23      （ね）
```

当新的 decoder transaction 从 record 中部开始时，不再要求重新看到完整 record 前缀；只要当前 source pointer 能落入唯一、可信的 source span，就恢复 `recordId` 和对应 `glyphIndex`。如果旧 message instance 尚未明确结束，并且 record、窗口上下文和时间关系一致，则把这次 transaction 作为旧 instance 的新 decoder fragment；否则创建新 instance。

```text
source pointer 9050
        │ 静态索引
        ▼
chr-fc-234a / glyph 16
        │ 旧 I1 仍在同一显示事务中
        ▼
R1 / I1 / fragment F2
```

优点：即使 fragment 从 record 中部开始，也能恢复稳定语义来源；不需要用 tile 值反向猜 record。  
风险：共享 ROM 区间、字典 token、多 record 复用 source span 时可能产生歧义；相同 record 再次出现时不能仅凭 recordId 复用旧 instance。  
评审问题：source span 唯一性规则；字典展开到 glyph range 的映射；instance continuation 的结束证据；没有新的 ROM read、只有 RAM/PPU copy 时的处理。

### 候选方案 B：record 内局部内容索引

翻译包在构建时为每条 record 生成所有足够可靠的连续子串索引。运行时 fallback 可以用屏幕上的后半句找到所属 record 和大致原文范围。

优点：通用，不修改游戏解码器。  
风险：短子串可能歧义，需要唯一性和上下文评分。

### 候选方案 C：恢复来源传播

追踪字符从缓冲区、临时 RAM、PPU copy 到 Nametable 的完整复制链，让目前无来源的格子继承原始来源。

优点：语义身份最准确。  
风险：不同游戏复制管道不同，适配成本较高。

### 候选方案 D：混合恢复

当同一个 record 已有部分稳定来源时，仅在其附近的无来源文本中查询该 record 的剩余子串。

优点：候选范围小，误匹配风险低于全库搜索。  
风险：必须严格限制为当前可见字符，避免补出屏幕上不存在的文本。

当前把方案 A 作为优先评审候选，但尚未决定实现。方案 B 可作为纯 fallback，方案 C 用于来源传播诊断和逐游戏增强，方案 D 用于已有稳定 record 锚点时的受限补救。

## 11. 仍需记录的诊断数据

为了区分“来源丢失”和“真正遮挡”，建议调试事件保留：

- frame number；
- recordId / instanceId / glyphIndex；
- ROM source offset；
- PPU 写入前后的地址和值；
- 写入管道或 producer 类型；
- 物理 Nametable 页面；
- 投影后的屏幕 cell；
- 当前 cell 是否有来源；
- 来源被建立、复制、覆盖、清除的原因；
- fallback 候选、得分和拒绝原因；
- 最终 block 的成员格子和源索引范围。

调试模式应允许针对单个屏幕格子查看简短历史，而不是默认记录无限完整 trace，以避免显著拖慢模拟器。

## 12. 回归测试矩阵

每次修改 grouping、生命周期或 fallback 后，至少验证：

1. 打开和关闭普通 NPC 对话。
2. 连续两句对话使用不同 instance 和位置。
3. 长对话逐行滚动。
4. 上层菜单遮挡下层对话。
5. 商店欢迎语、购买提示、商品列表和价格。
6. 道具列表中的多个词条。
7. 是/否、方向和命令菜单。
8. 宝箱获得金币、火把、钥匙和其他 ITEM 参数。
9. 两个 Nametable 页面之间滚动或切换。
10. 状态窗口完全打开、部分构建和关闭。
11. 相同对话重复触发两次。
12. 来源存在、fallback 命中、两者都失败三种调试状态。
13. 原文消失后的下一帧没有残留翻译。
14. 快速连续操作时翻译不明显落后且不会闪回旧内容。

## 13. 成功标准

模型不以“提取并翻译 ROM 中所有文本”为唯一成功标准。更重要的是：

- 能把屏幕上的文本稳定映射到正确翻译；
- 同类游戏只需要更换翻译包和少量适配配置；
- 稳定来源路径准确，fallback 路径有边界；
- 错误不会被隐藏，调试界面能说明文本来自哪条路径；
- 新发现的 corner case 可以被加入本文件和自动回归测试。


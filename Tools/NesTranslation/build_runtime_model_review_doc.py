"""Build a visual DOCX review guide for runtime translation corner cases."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[2]
ASSET_DIR = ROOT / "Research/dragon-quest-jp/review-assets/runtime-model-figures"
OUTPUT = ROOT / "Research/dragon-quest-jp/review-output/runtime-translation-model-review.docx"
FONT = "/System/Library/AssetsV2/com_apple_MobileAsset_Font8/86ba2c91f017a3749571a82f2c6d890ac7ffb2fb.asset/AssetData/PingFang.ttc"


CASES = [
    ("两个 Nametable 页面", "已处理", "画面来自 B 页，但只扫描 A 页时会完全漏掉。", ["地图（A 页）", "发现了 かぎ。（B 页）"], "发现了钥匙。", "pages"),
    ("离屏准备后切换", "已处理", "窗口先写在离屏页，滚动后才进入当前画面。", ["帧 N：地图", "帧 N+1：新窗口"], "切换后显示新译文", "swap"),
    ("解码结束但窗口仍在", "已处理", "解码生命周期短于屏幕显示生命周期。", ["＊「まだ みえる", "解码器：已返回"], "窗口可见时继续显示", "lifetime"),
    ("窗口关闭但翻译残留", "已处理", "画面已经清空，旧 scene item 不应继续存在。", ["窗口：已关闭", "地图重新出现"], "翻译同步消失", "closed"),
    ("连续两条对话共存", "已处理", "两条可同时看见的消息各有自己的显示 instance；新消息出现不能删除旧消息。", ["第一句  instance I1", "第二句  instance I2"], "I1：第一句译文\nI2：第二句译文", "two"),
    ("同 record 多 fragment", "已处理", "fragment 是一次显示中的一批解码输出；多批输出可以共同组成同一个 record 和 instance。", ["F1：[0][1][2]", "F2：   [3][4][5]"], "R1 / I1：合并为一条完整译文", "fragments"),
    ("glyphIndex 缺号", "已处理", "来源缺号不等于遮挡，同一屏幕行仍应组成一个 block。", ["[0][1][?][?][4][5]", "なにを かうかね？"], "要买什么？", "holes"),
    ("整行 provenance 丢失", "未处理", "第二行可见，但整行没有稳定来源；候选方案用 sourceOffset 把中途开始的 fragment 接回原 record。", ["ここは ぶきのみせだ", "なにか かうかね？"], "当前：第二行漏译\n候选：9050 → R1 / glyph 16", "lostrow"),
    ("上层窗口遮挡下层对话", "部分处理", "下层 record 只剩多个分散可见 block。", ["左侧可见文字     右侧", "下层对话仍在"], "分别显示可见部分", "overlay"),
    ("同一行中部被遮挡", "未处理", "按行 grouping 可能错误跨过中间遮挡。", ["文字左半      文字右半", "同一 tile 行"], "不能补出被遮内容", "midcover"),
    ("长对话滚动", "部分处理", "同一长 record 每页只显示其中一个区间。", ["第 1 页：很久以前……", "第 2 页：勇者来到……"], "只投影当前页对应译文", "scroll"),
    ("日中语序不同", "部分处理", "按比例截取无法保证落在相同语义边界。", ["地点 → 方向 → 动作", "当前只见中间部分"], "动作 → 对象 → 方向", "order"),
    ("共享前缀或后缀", "部分处理", "两个 record 的相同文字不能仅凭 tile 值归并。", ["欢迎光临  武器店", "欢迎光临  旅店"], "分别保持 A 与 B 的身份", "shared"),
    ("相邻分支文本", "部分处理", "ROM 中相邻不代表运行时同时显示。", ["> はい", "  いいえ"], "只翻译当前可见分支", "branch"),
    ("浊音与半浊音", "部分处理", "基础字与修饰 tile 应共享一个语义字符身份。", ["か  ＋  ゛", "物理上是两个 tile"], "逻辑字符：が", "dakuten"),
    ("重复字符", "已处理", "相同 tile 值必须由 glyphIndex 区分。", ["か   か   か", "12   12   12"], "i0   i1   i2", "repeat"),
    ("相同 tile 的无来源重写", "已处理", "值相同但生产者变化时必须清除旧来源。", ["帧 N：对话 tile 12", "帧 N+1：地图 tile 12"], "第二次写入不继承旧译文", "rewrite"),
    ("PPU copy 与 redraw", "部分处理", "复制路径未传播来源时，文字可见但 provenance 消失。", ["缓冲：[R0][R1][R2]", "画面：[ ?][ ?][ ?]"], "需要传播或 fallback", "copy"),
    ("道具列表", "部分处理", "多个词条必须逐行识别，不能拼成一句话。", ["やくそう    2", "たいまつ    1", "かぎ        3"], "药草 2\n火把 1\n钥匙 3", "list"),
    ("商店价格与名称", "部分处理", "名称和数字来自不同管道，但需要保留同一行位置。", ["たけざお      10", "こんぼう      60"], "竹竿 10 G\n木棒 60 G", "shop"),
    ("是与否菜单", "已处理", "短词可能只能通过屏幕内容 fallback。", ["> はい", "  いいえ"], "是\n否", "yesno"),
    ("运行时 ITEM", "已处理", "模板固定，ITEM 在每个 instance 中动态解析。", ["あ は かぎを", "みつけた。"], "发现了钥匙。", "item"),
    ("参数只存在于游戏状态", "部分处理", "画面没有独立文字时，需要从状态或解码流取得参数。", ["发现了 [图标]", "RAM itemId = 03"], "发现了钥匙。", "state"),
    ("子窗口覆盖底层菜单", "部分处理", "只排除被稳定来源占用的确切格子，不能排除整个矩形。", ["交谈   咒文", "状态  [是/否]", "楼梯   调查"], "底层未遮格子仍可识别", "submenu"),
    ("菜单构建中的半成品", "已处理", "一帧内可能依次出现边框、单字和完整菜单。", ["t0：只画边框", "t1：写入一半", "t2：完整菜单"], "只发布帧末 t2", "build"),
    ("快速操作造成滞后", "已优化", "重复匹配和多次 UI 更新会让翻译落后。", ["游戏：A B C D E", "旧翻译：A A C C E"], "目标：A B C D E", "lag"),
    ("翻译比原文长", "部分处理", "中文超过原窗口宽度时可能偏右或越界。", ["みじかい", "原文窗口较窄"], "这是一条明显更长的中文译文", "wide"),
    ("多行中文高度不足", "部分处理", "来源紧边界只有一行高度，中文第二行可能被裁掉。", ["ながい せりふ", "来源 bounds：1 行"], "第一行中文\n第二行中文", "height"),
    ("错误词汇命中", "部分处理", "局部子串可能同时命中多个数据库候选。", ["しずく", "候选：水滴／彩虹水滴"], "应选择水滴，不应误选彩虹水滴", "wrong"),
    ("启动时幽灵文字", "已处理", "新程序启动前必须清空上一次 scene。", ["游戏尚未开始", "黑色空画面"], "不应出现「钥匙」", "ghost"),
    ("调试框与译文重叠", "部分处理", "metadata 和用户译文画在同一位置会像乱码。", ["recordId 42%", "这里是武器店"], "调试标签应放在框外", "debug"),
    ("已识别但没有译文", "待增强", "recordId 已确定，但翻译包中的 translation 为空。", ["[源][源][源]", "recordId = chr-xxxx"], "recognized / untranslated", "untranslated"),
    ("完全未识别", "待增强", "稳定来源和 fallback 都没有结果。", ["日文清晰可见", "没有任何识别框"], "记录 unknown screen run", "unknown"),
]


# A case keeps its original number so old discussions and screenshots remain
# valid, while the review document presents related cases next to each other.
CATEGORIES = [
    ("A", "Record 前处理", "先确定 record 的边界、身份、模板、参数与翻译数据。", [13, 14, 22, 23, 29, 32], "#3566A8"),
    ("B", "运行时来源采集与传播", "把 decoder、RAM 和 PPU 写入可靠地关联到 record、instance 与 glyph。", [6, 7, 8, 15, 17, 18, 33], "#28834C"),
    ("C", "Nametable 可见模型", "根据物理页面、滚动、遮挡和当前可见格子建立 block 与生命周期。", [1, 2, 3, 4, 5, 9, 10, 11, 16, 19, 20, 21, 24, 25, 30], "#A66A00"),
    ("D", "译文投影与布局", "把可见原文区间映射到译文，并处理位置、换行和尺寸。", [12, 27, 28], "#7546A5"),
    ("E", "发布与调试", "控制帧级发布、响应速度和调试信息的呈现。", [26, 31], "#586270"),
]


# Each entry explains why the case matters and how to review it.  The visual
# guide deliberately keeps these notes next to the simulated screen so a
# reviewer does not have to cross-reference the Markdown design document.
DETAILS = {
    "pages": ("来源格子可能位于任一物理 CIRAM 页；只缓存当前认为的页面会漏掉完整窗口。", "保存两页来源状态，再使用本帧 scroll、镜像方式和可见坐标进行投影。", "让文字分别出现在 A/B 页并滚动切换；译文应只跟随当前可见页。"),
    "swap": ("游戏可先在屏幕外完成窗口，再用一次滚动把它带入画面，因此玩家看不到逐字写入。", "来源在写入时绑定物理格子；显示时重新投影，不能冻结为写入时的屏幕坐标。", "切换前不得提前显示；切换后的第一帧应完整出现且位置正确。"),
    "lifetime": ("解码函数返回只代表生产结束，不代表字符已经从 PPU 画面消失。", "scene 生命周期由当前可见来源格子维持；只要还有格子可见，instance 就继续存在。", "解码结束后停留数秒，译文不得消失；关窗后必须立即消失。"),
    "closed": ("旧来源若没有在覆盖或清屏时清除，就会形成已经看不见的幽灵译文。", "每帧从可见格子重建 scene；没有可见成员的 block 不再发布。", "关闭窗口、换地图及载入存档后，旧译文均不得残留。"),
    "two": ("例：NPC 先说第一句，玩家推进后第二句写到另一行，而第一句尚未被清除。两句即使来自同一个 record，也必须是 I1、I2 两次显示。", "先按 instance 隔离格子，再从各自当前可见的格子建立 block。I2 出现不结束 I1；每个 instance 按自己的可见性独立消失。", "让 I1、I2 同时可见，再分别清除其中一句；另一句的译文、位置和生命周期都不应改变。"),
    "fragments": ("fragment 只是 decoder 的一批输出，不是新对话。例：同一句商店问候先解码 glyph 0–2，再解码 glyph 3–5。", "F1、F2 都挂在同一个 record R1 和显示 instance I1 下；fragmentId 主要用于追踪生产过程，不能作为切断译文的依据。", "分两批或逐字写入同一句；最终只能出现一个译文。decoder 返回后，只要来源格子仍可见，译文就必须保留。"),
    "holes": ("漏掉的 glyphIndex 可能只是来源追踪缺口，并不证明屏幕中存在遮挡。", "同 record、同屏幕行的格子仍组成一个 block；缺号只降低覆盖率，不直接切段。", "制造中间缺号，确认句子仍完整；真正遮挡必须由屏幕格子占用事实证明。"),
    "lostrow": ("同一 message 的后半段仍有 ROM 来源，但当前运行时只绑定了前 10/24 个 glyph；后续 decoder transaction 或写入路径没有继续传播 provenance。", "候选方案 A（待评审）：建立 sourceOffset → recordId + glyph range 索引。例：9050 → chr-fc-234a / glyph 16–18；旧 I1 未结束时作为新 fragment 续接。", "确认 source span 唯一性、字典展开映射和 instance continuation 条件；如果只有 RAM/PPU copy 而没有 ROM read，仍需来源传播方案。"),
    "overlay": ("上层窗口覆盖部分来源格子后，下层 record 可能剩下多个空间上分离的可见块。", "先按当前可见格子形成连通 block，再分别把各 block 的索引范围投影到译文。", "移动上层窗口；每个剩余块应独立摆放，遮住的语义不得被补出来。"),
    "midcover": ("左右文字位于同一行并不表示中间也可见；按整行合并会越过真实遮挡。", "需要利用被上层窗口实际占用的格子把行切成多个连通分量，而不是猜测缺号。", "遮住行首、行中、行尾分别测试；只显示每个可见分量对应的译文。"),
    "scroll": ("长 record 可在同一窗口中滚动多页，屏幕始终只保留其中一段。", "用当前可见 glyphIndex 的最小/最大范围定位原文区间，再近似映射到译文区间。", "逐页前进和返回；译文应随可见区间变化，不得展示整条未出现内容。"),
    "order": ("日文和中文的词序、长度不同，相同比例位置未必对应同一语义。", "比例投影只作为通用近似；翻译包可选提供语义锚点，但运行时不写词汇特例。", "检查是否出现明显错段；必要时记录需要锚点的 record，而不是调整全局阈值。"),
    "shared": ("两个 record 可以共享字节、前缀或后缀，仅按文字或 ROM 邻接关系会混为一条。", "始终以 recordId/instanceId 保持身份；共享字符也分别属于各自的运行时实例。", "让两条相似消息同时或连续出现，确认译文不会串台或复用旧位置。"),
    "branch": ("ROM 中相邻的分支文本不一定同时执行，静态连续区域不能直接当作一条消息。", "结合运行时来源、控制符和当前可见格子，只选择实际走到并显示的分支。", "分别选择是/否或不同菜单项；未执行分支绝不能提前显示。"),
    "dakuten": ("日文浊点可能占独立 tile，但语义上属于前一个基础字符。", "解码阶段将基础字与修饰 tile 关联为一个 logical glyph，同时保留全部物理格子。", "覆盖或重写任一组成 tile 时，组合字符身份和显示范围都要正确更新。"),
    "repeat": ("同一句中相同字符拥有相同 tile 值；tile 值无法区分它们在原文中的位置。", "使用 recordId + instanceId + glyphIndex 作为身份，tileValue 只用于验证写入。", "对连续重复字逐个覆盖和滚动，来源索引不得跳到另一个同字。"),
    "rewrite": ("地图或新窗口可能写入与旧文字数值相同的 tile，但生产者已经改变。", "任何无匹配生产者的写入都清除旧 provenance；数值相等不能保留所有权。", "用相同 tile 覆盖旧对话，确认旧译文立刻消失且不会再次复活。"),
    "copy": ("字符可能先写入 RAM/离屏区，再由 copy 或 redraw 搬到 Nametable，绕开直接追踪。", "能证明复制关系时传播来源；无法证明时保持无来源并交给受限 fallback。", "记录每次复制链的地址和值；宁可漏译，也不要把不确定来源强行继承。"),
    "list": ("道具列表由多个独立短词和数量组成，空间相近但语义上不是一句长文本。", "稳定来源按行形成 block；无来源时也按屏幕 run/行查询词汇库，并保留数量格子。", "改变库存数量和列表顺序；名称、数量、翻译位置必须始终对应。"),
    "shop": ("商品名由文本管道产生，价格可能由数值绘制管道产生，二者没有共同 record。", "分别识别名称和数字，再依据同一可见行的空间关系组成展示行，不伪造共同来源。", "购买、翻页和价格变化时检查名称不会绑定到上一行或旧价格。"),
    "yesno": ("极短菜单常缺少稳定来源，也容易与长文本中的相同片段发生歧义。", "把每个屏幕行作为独立 fallback 候选，要求完整短词匹配及合理边界。", "在不同场景打开是/否菜单，确认自动出现、光标移动不改变词义。"),
    "item": ("模板文本固定，但道具名由本次事件参数决定；写死译文会在不同宝箱中出错。", "翻译记录保存模板，instance 创建时解析 ITEM 参数并作为不可拆分原子渲染。", "连续取得钥匙、火把、金币等对象，确认每个 instance 使用自己的参数。"),
    "state": ("有些参数只以图标或数值存在，屏幕字符本身不足以还原具体对象。", "允许翻译包声明受控的运行时参数来源；通用核心只接收参数，不理解游戏含义。", "参数缺失时不得猜测；应显示通用部分或进入诊断，并记录所需状态字段。"),
    "submenu": ("子窗口只覆盖底层菜单的一部分，按整个矩形排除会让仍可见标签消失。", "fallback 排除的最小单位是已有稳定来源或上层实际占用的屏幕格子。", "在不同位置弹出子窗口；未遮格子继续显示，重叠格子只显示最上层内容。"),
    "build": ("一帧内部菜单可能经历边框、半行文字、完整文字等多个中间状态。", "收集帧内变化并在帧末生成一次最终 scene，UI 只消费最新完整快照。", "逐帧录像检查，不应出现单字闪烁、重复框或中间位置跳动。"),
    "lag": ("每次 PPU 写入都匹配数据库并刷新 UI，会产生积压，使译文落后于操作。", "帧内合并、缓存不变结果、丢弃过期 scene，并让 UI 只绘制最新版本。", "快速开关菜单和连续移动；翻译不能倒退到旧帧，延迟应保持有界。"),
    "wide": ("译文宽度可能远大于来源 bounds；简单居中会偏移或越过窗口边缘。", "把来源 bounds 当锚点而非硬裁剪框，统一执行换行、字号下限和屏幕边界约束。", "测试短、中、超长译文；文字必须可见且不与其他 block 无规则重叠。"),
    "height": ("少量来源格子的紧边界只有一行高，但译文换行后需要更多垂直空间。", "先计算译文布局尺寸，再围绕来源锚点扩展显示框，并限制在可用屏幕区域。", "两行以上译文应完整显示；不能因来源高度不足裁掉后半句。"),
    "wrong": ("短子串可能命中词汇、道具全名或长句片段，单纯 contains 会选到错误候选。", "候选评分考虑完整边界、长度、当前 record 上下文和冲突；低置信度时不显示。", "为歧义词构造多个候选，确认选择可解释；错误候选应在调试信息中列出。"),
    "ghost": ("进程或窗口复用上一轮 scene，新游戏尚未提交首帧时就绘出了旧内容。", "启动、换 ROM 和断开连接时显式发布空 scene；新内容只能来自当前帧快照。", "反复退出和快速重启，黑屏阶段必须保持为空。"),
    "debug": ("调试 metadata 与译文使用同一坐标层，会造成看似重复、错位或乱码。", "调试标签使用独立图层并放在框外；关闭调试后用户布局完全不受影响。", "切换调试开关，译文的位置和尺寸应保持不变，标签不得遮住正文。"),
    "untranslated": ("来源识别成功并不代表翻译包已有中文；两种状态必须分开统计。", "保留 recordId 和可见 block，但标记 recognized/untranslated，不生成伪译文。", "补入翻译包后无需代码或额外操作，同一 record 应自动开始显示中文。"),
    "unknown": ("日文可见但既没有来源，也没有 fallback 候选，普通日志很难复现场景。", "记录去重后的 unknown screen run、格子内容、坐标与帧上下文，供扩包和诊断。", "调试框应明确表示未识别；收录翻译后再次运行应自动转为正常匹配。"),
}


COLORS = {
    "bg": "111319", "screen": "111111", "grid": "333942", "white": "F4F5F7",
    "source": "26D866", "fallback": "FF515E", "cover": "FFB020",
    "info": "59A8FF", "muted": "AAB2BE", "panel": "20242C",
}


def font(size: int, index: int = 0) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT, size=size, index=index)


def wrap(draw: ImageDraw.ImageDraw, text: str, fnt, width: int) -> list[str]:
    lines: list[str] = []
    for paragraph in text.splitlines() or [""]:
        current = ""
        for char in paragraph:
            trial = current + char
            if current and draw.textlength(trial, font=fnt) > width:
                lines.append(current)
                current = char
            else:
                current = trial
        lines.append(current)
    return lines


def rect(draw, box, fill=None, outline=None, width=1):
    draw.rectangle(box, fill=fill, outline=outline, width=width)


def draw_grid(draw, box, step=28):
    x0, y0, x1, y1 = box
    for x in range(x0, x1 + 1, step):
        draw.line((x, y0, x, y1), fill="#293039", width=1)
    for y in range(y0, y1 + 1, step):
        draw.line((x0, y, x1, y), fill="#293039", width=1)


def draw_window(draw, box, lines, *, title="游戏画面"):
    x0, y0, x1, y1 = box
    rect(draw, box, fill="#070809", outline="#F4F5F7", width=5)
    draw.text((x0 + 18, y0 - 38), title, font=font(23), fill="#D8DCE2")
    y = y0 + 24
    for line in lines:
        draw.text((x0 + 24, y), line, font=font(29), fill="#F4F5F7")
        y += 52


def source_cells(draw, x, y, pattern, color="#26D866"):
    for i, flag in enumerate(pattern):
        xx = x + i * 31
        rect(draw, (xx, y, xx + 27, y + 27), fill="#171B20", outline=color if flag else "#69727E", width=3)
        if flag:
            draw.ellipse((xx + 9, y + 9, xx + 18, y + 18), fill=color)


def draw_scene(case_no: int, title: str, lines: list[str], output: str, kind: str, path: Path):
    img = Image.new("RGB", (1600, 1000), "#111319")
    d = ImageDraw.Draw(img)
    d.text((42, 24), f"CASE {case_no:02d}", font=font(22), fill="#59A8FF")
    d.text((172, 18), title, font=font(35, 1), fill="#F4F5F7")
    status = CASES[case_no - 1][1]
    summary = CASES[case_no - 1][2]
    status_color = "#69E893" if status == "已处理" else "#FFCE73"
    d.text((1410, 26), status, font=font(22), fill=status_color, anchor="ra")
    left = (54, 104, 950, 490)
    right = (1010, 104, 1544, 490)
    rect(d, left, fill="#171A1F", outline="#49515B", width=2)
    draw_grid(d, left, 28)
    draw_window(d, (125, 160, 870, 425), [] if kind in {"two", "fragments"} else lines[:4])
    if kind == "two":
        # Two independent display occurrences coexist.  The record may be the
        # same or different; instance identity keeps position and lifetime apart.
        rect(d, (165, 205, 830, 278), fill="#101820", outline="#59A8FF", width=3)
        d.text((185, 217), "I1", font=font(21, 1), fill="#7DBAFF")
        d.text((250, 217), "第一句：欢迎来到城里。", font=font(27), fill="#F4F5F7")
        rect(d, (165, 306, 830, 379), fill="#101A14", outline="#26D866", width=3)
        d.text((185, 318), "I2", font=font(21, 1), fill="#69E893")
        d.text((250, 318), "第二句：国王正在找勇者。", font=font(27), fill="#F4F5F7")
        d.text((165, 395), "I2 出现 ≠ I1 结束；两者分别跟随自己的可见格子", font=font(18), fill="#AAB2BE")
    elif kind == "fragments":
        # One semantic record and one display occurrence, produced by two
        # decoder batches.  Fragment identity is diagnostic, not a split point.
        d.text((165, 177), "同一 record R1 · 同一次显示 I1", font=font(22, 1), fill="#F4F5F7")
        rect(d, (165, 225, 455, 285), fill="#111C27", outline="#59A8FF", width=3)
        d.text((182, 238), "F1  [0][1][2]", font=font(24), fill="#7DBAFF")
        rect(d, (540, 225, 830, 285), fill="#122018", outline="#26D866", width=3)
        d.text((557, 238), "F2  [3][4][5]", font=font(24), fill="#69E893")
        d.line((455, 255, 540, 255), fill="#AAB2BE", width=3)
        d.line((310, 310, 310, 350), fill="#59A8FF", width=4)
        d.line((685, 310, 685, 350), fill="#26D866", width=4)
        d.line((310, 350, 685, 350), fill="#AAB2BE", width=4)
        d.polygon([(485, 350), (510, 350), (497, 370)], fill="#AAB2BE")
        d.text((275, 378), "一个可见结果：[0][1][2][3][4][5]", font=font(23), fill="#F4F5F7")
    rect(d, right, fill="#070809", outline="#49515B", width=2)
    d.text((1032, 66), "翻译与识别结果", font=font(23), fill="#D8DCE2")
    for idx, line in enumerate(wrap(d, output, font(31), 470)):
        d.text((1050, 160 + idx * 52), line, font=font(31), fill="#F4F5F7")

    # Shared source-cell strip; each special case modifies it visually.
    pattern = [1, 1, 1, 1, 1, 1, 1, 1]
    if kind in {"holes", "lostrow", "copy", "unknown"}:
        pattern = [1, 1, 0, 0, 1, 0, 1, 1]
    source_cells(d, 170, 445, pattern)
    d.text((460, 447), "当前屏幕来源格子", font=font(19), fill="#AAB2BE")

    if kind in {"overlay", "midcover", "submenu"}:
        rect(d, (420, 210, 700, 350), fill="#2B2415", outline="#FFB020", width=5)
        d.text((475, 255), "上层窗口", font=font(27), fill="#FFCE73")
    if kind == "lostrow":
        source_cells(d, 170, 478, [0] * 8, color="#FF515E")
        d.text((460, 477), "第二行无来源", font=font(19), fill="#FF7B85")
    if kind == "pages":
        rect(d, (92, 125, 405, 390), fill="#17202A", outline="#69727E", width=3)
        d.text((205, 210), "A 页", font=font(32), fill="#AAB2BE")
        rect(d, (520, 125, 835, 390), fill="#07130B", outline="#26D866", width=4)
        d.text((635, 210), "B 页", font=font(32), fill="#69E893")
    if kind in {"wrong", "ghost"}:
        rect(d, (1034, 348, 1518, 425), outline="#FF515E", width=4)
        d.text((1052, 362), "× 错误显示", font=font(23), fill="#FF7B85")
    if kind in {"untranslated", "unknown"}:
        d.text((1050, 365), "需要进入诊断队列", font=font(22), fill="#FFCE73")

    d.line((950, 295, 1010, 295), fill="#59A8FF", width=5)
    d.polygon([(1008, 283), (1030, 295), (1008, 307)], fill="#59A8FF")
    d.line((54, 522, 1544, 522), fill="#3A424C", width=2)
    d.text((62, 540), "现象", font=font(21, 1), fill="#59A8FF")
    for idx, line in enumerate(wrap(d, summary, font(22), 1320)):
        d.text((190, 538 + idx * 30), line, font=font(22), fill="#D8DCE2")

    mechanism, handling, verification = DETAILS[kind]
    panels = [
        ("为什么会发生", mechanism, "#FFCE73"),
        ("模型如何处理", handling, "#69E893"),
        ("Review / 验证方法", verification, "#59A8FF"),
    ]
    panel_y = 610
    panel_h = 105
    for label, body, accent in panels:
        rect(d, (54, panel_y, 1544, panel_y + panel_h), fill="#171A1F", outline="#3E4651", width=2)
        d.text((78, panel_y + 16), label, font=font(22, 1), fill=accent)
        wrapped = wrap(d, body, font(22), 1180)
        for idx, line in enumerate(wrapped[:2]):
            d.text((315, panel_y + 15 + idx * 32), line, font=font(22), fill="#E4E7EB")
        panel_y += 118

    d.text((56, 970), "判断原则：宁可暂时漏译，也不要显示屏幕上不可见或身份不确定的内容。", font=font(18), fill="#8E98A6", anchor="ls")
    img.save(path, quality=95)


def draw_cover(path: Path):
    img = Image.new("RGB", (1600, 1100), "#F7F8FA")
    d = ImageDraw.Draw(img)
    d.text((110, 105), "NES 运行时翻译模型", font=font(58, 1), fill="#111319")
    d.text((110, 185), "视觉审查手册", font=font(58, 1), fill="#111319")
    d.text((112, 280), "用游戏画面格子说明当前模型和 33 个 Corner Cases", font=font(28), fill="#4B5563")
    rect(d, (110, 370, 1490, 710), fill="#111319", outline="#374151", width=3)
    draw_grid(d, (110, 370, 1490, 710), 36)
    rect(d, (190, 435, 910, 645), fill="#060708", outline="#F4F5F7", width=5)
    d.text((235, 475), "＊「屏幕上显示什么", font=font(38), fill="#F4F5F7")
    d.text((235, 545), "     就只翻译什么。", font=font(38), fill="#F4F5F7")
    source_cells(d, 1040, 460, [1, 1, 1, 1, 1, 1])
    d.text((1040, 515), "稳定来源", font=font(25), fill="#69E893")
    source_cells(d, 1040, 565, [0, 0, 0, 0, 0, 0], color="#FF515E")
    d.text((1040, 620), "无来源  fallback", font=font(25), fill="#FF7B85")
    d.text((110, 790), "首要规则", font=font(30, 1), fill="#111319")
    rules = [
        "只有当前屏幕可见的文字才显示翻译。",
        "有稳定来源的格子优先使用来源。",
        "只有没有稳定来源的格子才进入 fallback。",
        "排除 fallback 的单位是格子，不是整个窗口矩形。",
    ]
    for i, rule in enumerate(rules):
        d.text((145, 850 + i * 48), f"{i + 1}. {rule}", font=font(25), fill="#252A31")
    img.save(path, quality=95)


def draw_layer_boundary(path: Path):
    """Explain which work belongs before, inside, and after the Nametable model."""
    img = Image.new("RGB", (1600, 1000), "#F7F8FA")
    d = ImageDraw.Draw(img)
    d.text((70, 45), "问题边界", font=font(42, 1), fill="#111319")
    d.text((70, 105), "Nametable 模型接收已经尽可能附带来源身份的物理格子；record 的取得属于上游。", font=font(24), fill="#4B5563")

    layers = [
        ("A", "Record 前处理", "record 边界 · recordId · sourceOffset · 模板参数", "#E8EEF9", "#3566A8"),
        ("B", "来源采集与传播", "decoder / RAM / PPU write → instanceId + glyphIndex", "#EAF7EF", "#28834C"),
        ("C", "Nametable 可见模型", "两页投影 · 当前可见 cell · 遮挡 · grouping · 生命周期", "#FFF3D6", "#A66A00"),
        ("D", "译文投影与布局", "可见原文区间 → 译文区间 · 位置 · 换行 · 尺寸", "#F2EBFA", "#7546A5"),
        ("E", "发布与诊断", "帧末 scene · 性能 · recognized / untranslated / unknown", "#F2F4F7", "#586270"),
    ]
    y = 175
    for idx, (letter, title, body, fill, accent) in enumerate(layers):
        rect(d, (140, y, 1460, y + 116), fill=fill, outline=accent, width=3)
        rect(d, (140, y, 238, y + 116), fill=accent)
        d.text((189, y + 58), letter, font=font(34, 1), fill="#FFFFFF", anchor="mm")
        d.text((275, y + 18), title, font=font(27, 1), fill="#111319")
        d.text((275, y + 67), body, font=font(21), fill="#374151")
        if idx < len(layers) - 1:
            d.line((800, y + 116, 800, y + 141), fill="#6B7280", width=4)
            d.polygon([(789, y + 136), (811, y + 136), (800, y + 151)], fill="#6B7280")
        y += 145

    d.text((70, 925), "核心判断：C 层回答“现在屏幕上有哪些可见 block”；A/B 层回答“这些格子来自哪个 record”。", font=font(22, 1), fill="#8A5500")
    img.save(path, quality=95)


def draw_case_classification(path: Path):
    """Map the 33 cases to their primary responsibility layer."""
    img = Image.new("RGB", (1600, 1000), "#111319")
    d = ImageDraw.Draw(img)
    d.text((55, 35), "33 个 Cases 的责任分类", font=font(38, 1), fill="#F4F5F7")
    d.text((55, 92), "主分类表示首先应在哪一层解决；跨层 Case 在说明中保留接口责任。", font=font(22), fill="#AAB2BE")
    groups = [
        ("A  Record 前处理", "13 · 14 · 22 · 23 · 29 · 32", "边界、共享字节、分支、模板参数、翻译包与候选索引", "#3566A8"),
        ("B  来源采集与传播", "6 · 7 · 8 · 15 · 17 · 18 · 33", "取得并传播 recordId、instanceId、glyphIndex、sourceOffset", "#28834C"),
        ("C  Nametable 可见模型", "1–5 · 9–11 · 16 · 19–21 · 24–25 · 30", "页面投影、可见性、遮挡、block、生命周期和屏幕结构", "#A66A00"),
        ("D  译文投影与布局", "12 · 27 · 28", "可见区间的语义映射、位置、换行和显示尺寸", "#7546A5"),
        ("E  发布与调试", "26 · 31", "帧级发布、性能和调试信息", "#586270"),
    ]
    y = 150
    for title, cases, body, accent in groups:
        rect(d, (55, y, 1545, y + 126), fill="#191D23", outline="#3E4651", width=2)
        rect(d, (55, y, 345, y + 126), fill=accent)
        d.text((78, y + 22), title, font=font(24, 1), fill="#FFFFFF")
        d.text((380, y + 18), cases, font=font(25, 1), fill="#F4F5F7")
        d.text((380, y + 69), body, font=font(21), fill="#C7CDD5")
        y += 143

    rect(d, (55, 875, 1545, 960), fill="#201B10", outline="#A66A00", width=3)
    d.text((80, 892), "Case 5–8 的结论", font=font(22, 1), fill="#FFCE73")
    d.text((285, 891), "5 属于 C；6 是 B→C 接口；7 的根因在 B、容错在 C；8 主要属于 A/B，不能靠 grouping 单独修复。", font=font(20), fill="#F4F5F7")
    img.save(path, quality=95)


def draw_category_page(letter: str, title: str, description: str, case_numbers: list[int], accent: str, path: Path):
    img = Image.new("RGB", (1600, 1000), "#F7F8FA")
    d = ImageDraw.Draw(img)
    rect(d, (110, 110, 310, 310), fill=accent)
    d.text((210, 210), letter, font=font(88, 1), fill="#FFFFFF", anchor="mm")
    d.text((370, 125), title, font=font(48, 1), fill="#111319")
    for i, line in enumerate(wrap(d, description, font(25), 1050)):
        d.text((372, 205 + i * 38), line, font=font(25), fill="#4B5563")
    d.line((110, 360, 1490, 360), fill=accent, width=5)
    y = 410
    for number in case_numbers:
        case_title, status = CASES[number - 1][0], CASES[number - 1][1]
        d.text((145, y), f"CASE {number:02d}", font=font(22, 1), fill=accent)
        d.text((300, y), case_title, font=font(25), fill="#111319")
        d.text((1390, y), status, font=font(20), fill="#667085", anchor="ra")
        y += 48
    d.text((110, 935), "Case 编号保持不变；这里只改变阅读顺序。", font=font(20), fill="#667085")
    img.save(path, quality=95)


def draw_toc(path: Path):
    img = Image.new("RGB", (1600, 1000), "#F7F8FA")
    d = ImageDraw.Draw(img)
    d.text((80, 45), "目录", font=font(44, 1), fill="#111319")
    d.text((80, 105), "按问题责任分组阅读；Case 编号沿用原编号。", font=font(23), fill="#4B5563")
    page = 14  # cover, TOC, boundary, classification, seven model/algorithm pages, two gap pages
    columns = [(80, 160, 750), (830, 160, 1520)]
    col = 0
    y = columns[col][1]
    for letter, title, _description, numbers, accent in CATEGORIES:
        needed = 48 + len(numbers) * 27
        if y + needed > 935:
            col += 1
            y = columns[col][1]
        x0, _, x1 = columns[col]
        d.text((x0, y), f"{letter}  {title}", font=font(24, 1), fill=accent)
        d.text((x1, y), str(page), font=font(21, 1), fill=accent, anchor="ra")
        y += 36
        page += 1
        for number in numbers:
            title_text = CASES[number - 1][0]
            d.text((x0 + 25, y), f"Case {number:02d}  {title_text}", font=font(18), fill="#252A31")
            d.text((x1, y), str(page), font=font(18), fill="#667085", anchor="ra")
            y += 27
            page += 1
        y += 12
    d.text((80, 950), "前置：边界 3 · 分类 4 · 候选模型 5–7 · 统一算法 8–11 · 剩余缺口 12–13", font=font(19), fill="#667085")
    img.save(path, quality=95)


def draw_candidate_model_overview(path: Path):
    img = Image.new("RGB", (1600, 1000), "#F7F8FA")
    d = ImageDraw.Draw(img)
    d.text((70, 45), "候选模型草案", font=font(42, 1), fill="#111319")
    d.text((70, 105), "当前讨论记录  尚未替换现有实现", font=font(23), fill="#667085")
    d.text((70, 165), "核心规则：屏幕上显示什么，我们翻译什么。", font=font(28, 1), fill="#A66A00")

    stages = [
        ("当前可见 Nametable cells", "两页投影 · scroll · layer · 遮挡"),
        ("身份与分组", "recordId + instanceId + tokenIndex · 可见连通分量"),
        ("Source 到 Target", "优先分段长度 mapping · 控制符权重为 0"),
        ("布局与发布", "只使用当前可见 cells 的 bounds · 帧末 scene"),
    ]
    y = 245
    for idx, (title, body) in enumerate(stages):
        rect(d, (150, y, 1450, y + 118), fill="#FFFFFF", outline="#D0D5DD", width=2)
        rect(d, (150, y, 225, y + 118), fill="#A66A00" if idx == 2 else "#3566A8")
        d.text((187, y + 59), str(idx + 1), font=font(31, 1), fill="#FFFFFF", anchor="mm")
        d.text((265, y + 18), title, font=font(26, 1), fill="#111319")
        d.text((265, y + 67), body, font=font(21), fill="#4B5563")
        if idx < len(stages) - 1:
            d.line((800, y + 118, 800, y + 143), fill="#667085", width=4)
            d.polygon([(789, y + 138), (811, y + 138), (800, y + 153)], fill="#667085")
        y += 150
    d.text((70, 915), "Instance 在遮挡期间保持；visible group 可以分裂并在遮挡消失后重新合并。", font=font(22), fill="#4B5563")
    img.save(path, quality=95)


def draw_length_mapping(path: Path):
    img = Image.new("RGB", (1600, 1000), "#111319")
    d = ImageDraw.Draw(img)
    d.text((55, 35), "分段长度 Mapping", font=font(38, 1), fill="#F4F5F7")
    d.text((55, 92), "允许一个原文字符对应多个、一个或零个翻译字符；Enter 与 End 不消耗目标长度。", font=font(22), fill="#AAB2BE")

    source = ["R0", "R1", "R2", "R3", "R4", "R5", "R6", "R7"]
    target = ["T0", "T1", "T2", "T3", "T4"]
    mapping = [["T0"], [], ["T1"], ["T2"], [], ["T3"], [], ["T4"]]
    x0, cell_w = 95, 170
    d.text((55, 175), "Source", font=font(23, 1), fill="#7DBAFF")
    d.text((55, 485), "Target slice", font=font(23, 1), fill="#69E893")
    for i, token in enumerate(source):
        x = x0 + i * cell_w
        rect(d, (x, 235, x + 120, 305), fill="#17202A", outline="#59A8FF", width=3)
        d.text((x + 60, 270), token, font=font(25), fill="#F4F5F7", anchor="mm")
        d.line((x + 60, 305, x + 60, 455), fill="#69727E", width=3)
        label = " · ".join(mapping[i]) if mapping[i] else "∅"
        color = "#69E893" if mapping[i] else "#8E98A6"
        rect(d, (x, 520, x + 120, 590), fill="#122018" if mapping[i] else "#20242C", outline=color, width=3)
        d.text((x + 60, 555), label, font=font(24), fill=color, anchor="mm")

    rect(d, (95, 670, 735, 850), fill="#171A1F", outline="#FFB020", width=3)
    d.text((125, 700), "部分遮挡", font=font(24, 1), fill="#FFCE73")
    d.text((125, 755), "R1 R2 R3 被遮挡", font=font(23), fill="#F4F5F7")
    d.text((125, 805), "可见组：{R0} 与 {R4}", font=font(23), fill="#F4F5F7")
    rect(d, (865, 670, 1505, 850), fill="#171A1F", outline="#26D866", width=3)
    d.text((895, 700), "输出", font=font(24, 1), fill="#69E893")
    d.text((895, 755), "{R0} → T0", font=font(23), fill="#F4F5F7")
    d.text((895, 805), "{R4} → ∅；隐藏区的 T1/T2 不补出", font=font(23), fill="#F4F5F7")
    d.text((55, 940), "优先级：人工 mapping → 分行或分段长度 mapping → 整条 record 长度 mapping", font=font(21), fill="#AAB2BE")
    img.save(path, quality=95)


def draw_fallback_model(path: Path):
    img = Image.new("RGB", (1600, 1000), "#F7F8FA")
    d = ImageDraw.Draw(img)
    d.text((70, 45), "无 RecordId 的 Fallback", font=font(42, 1), fill="#111319")
    d.text((70, 105), "invalid 不是共同身份；先形成临时 screenTextInstanceId，再查询翻译包。", font=font(23), fill="#4B5563")

    steps = [
        ("Unknown cells", "屏幕位置 · 字体 · palette · 写入时间"),
        ("临时 text grouping", "保留有序 fragments 与 gap，不直接无缝拼接"),
        ("翻译包查询", "完整匹配 → 连续子串 → 有序多 fragment"),
        ("候选评分", "覆盖率 · 边界 · 顺序 · 分行 · 窗口 · 时间 · 歧义"),
    ]
    y = 190
    for idx, (title, body) in enumerate(steps):
        rect(d, (105, y, 1035, y + 116), fill="#FFFFFF", outline="#D0D5DD", width=2)
        d.text((135, y + 18), title, font=font(25, 1), fill="#111319")
        d.text((135, y + 68), body, font=font(20), fill="#4B5563")
        if idx < len(steps) - 1:
            d.line((570, y + 116, 570, y + 140), fill="#667085", width=4)
            d.polygon([(559, y + 135), (581, y + 135), (570, y + 150)], fill="#667085")
        y += 145

    outcomes = [
        ("高置信度", "恢复 inferred recordId + source range", "#28834C"),
        ("中置信度", "只显示可靠局部翻译", "#A66A00"),
        ("低置信度", "保持 unknown，不显示", "#B42318"),
    ]
    y = 250
    for title, body, accent in outcomes:
        rect(d, (1100, y, 1510, y + 145), fill="#FFFFFF", outline=accent, width=3)
        d.text((1130, y + 20), title, font=font(23, 1), fill=accent)
        for i, line in enumerate(wrap(d, body, font(19), 340)):
            d.text((1130, y + 68 + i * 29), line, font=font(19), fill="#252A31")
        y += 175
    d.text((70, 890), "ObservedProvenance 与 InferredProvenance 必须分开记录；内容命中不能自动证明原 instanceId。", font=font(22, 1), fill="#3566A8")
    d.text((70, 940), "待定：分组阈值、置信度阈值、Space 权重、推断来源升级条件。", font=font(20), fill="#667085")
    img.save(path, quality=95)


def draw_unified_algorithm(path: Path):
    img = Image.new("RGB", (1600, 1000), "#111319")
    d = ImageDraw.Draw(img)
    d.text((55, 35), "统一算法", font=font(38, 1), fill="#F4F5F7")
    d.text((55, 92), "已知来源是固定锚点；未知来源生成候选；统一求解后输出当前 scene。", font=font(22), fill="#AAB2BE")

    rect(d, (80, 170, 1520, 285), fill="#171A1F", outline="#59A8FF", width=3)
    d.text((120, 192), "当前可见 Nametable cells", font=font(27, 1), fill="#7DBAFF")
    d.text((120, 240), "两页物理状态 → scroll 投影 → 只保留当前帧可见 cells", font=font(21), fill="#E4E7EB")
    d.line((800, 285, 800, 330), fill="#69727E", width=4)

    rect(d, (80, 330, 735, 565), fill="#151D19", outline="#26D866", width=3)
    d.text((115, 355), "Observed path", font=font(26, 1), fill="#69E893")
    d.text((115, 410), "recordId + instanceId + tokenIndex", font=font(21), fill="#F4F5F7")
    d.text((115, 455), "形成固定 ObservedGroups", font=font(21), fill="#F4F5F7")
    d.text((115, 500), "不能被 fallback 改写", font=font(21), fill="#AAB2BE")

    rect(d, (865, 330, 1520, 565), fill="#201B10", outline="#FFB020", width=3)
    d.text((900, 355), "Unknown path", font=font(26, 1), fill="#FFCE73")
    d.text((900, 410), "screen graph + package indexes", font=font(21), fill="#F4F5F7")
    d.text((900, 455), "生成 phrase / substring / fragment 候选", font=font(21), fill="#F4F5F7")
    d.text((900, 500), "允许无法解释的 cells 保持 unknown", font=font(21), fill="#AAB2BE")

    d.line((405, 565, 690, 655), fill="#69727E", width=4)
    d.line((1190, 565, 910, 655), fill="#69727E", width=4)
    rect(d, (420, 655, 1180, 790), fill="#17202A", outline="#59A8FF", width=4)
    d.text((800, 690), "约束求解", font=font(28, 1), fill="#7DBAFF", anchor="ma")
    d.text((800, 744), "可靠性 → anchor 一致性 → 跨帧稳定 → 覆盖率", font=font(21), fill="#F4F5F7", anchor="ma")
    d.line((800, 790, 800, 835), fill="#69727E", width=4)
    rect(d, (420, 835, 1180, 935), fill="#122018", outline="#26D866", width=3)
    d.text((800, 885), "ResolvedGroups → 长度 mapping → layout → TranslationScene", font=font(23, 1), fill="#69E893", anchor="mm")
    img.save(path, quality=95)


def draw_offline_indexes(path: Path):
    img = Image.new("RGB", (1600, 1000), "#F7F8FA")
    d = ImageDraw.Draw(img)
    d.text((70, 45), "离线翻译包编译", font=font(42, 1), fill="#111319")
    d.text((70, 105), "运行前准备 source-to-target mapping 与 unknown query 所需索引。", font=font(23), fill="#4B5563")
    items = [
        ("1", "Tokenization", "普通字符、Space、Enter、End 保留连续 tokenIndex"),
        ("2", "Logical glyph", "浊点等多个物理 tile 合成一个逻辑字符"),
        ("3", "Length mapping", "人工 → 分段/分行 → 整条 record 的边界表"),
        ("4", "Segment indexes", "完整 segment trie、首字符倒排、任意 offset 子串"),
        ("5", "Translation classes", "record 不唯一但局部译文相同的 phrase 归并"),
        ("6", "Statistics", "候选数量、唯一性、source range 与边界类型"),
    ]
    y = 175
    for number, title, body in items:
        rect(d, (105, y, 1495, y + 105), fill="#FFFFFF", outline="#D0D5DD", width=2)
        rect(d, (105, y, 190, y + 105), fill="#3566A8")
        d.text((147, y + 52), number, font=font(28, 1), fill="#FFFFFF", anchor="mm")
        d.text((225, y + 16), title, font=font(24, 1), fill="#111319")
        d.text((520, y + 20), body, font=font(21), fill="#4B5563")
        y += 122
    d.text((70, 930), "第一版优先构建：full segment index、translation equivalence class、长度 mapping 边界表。", font=font(21, 1), fill="#3566A8")
    img.save(path, quality=95)


def draw_solver_rules(path: Path):
    img = Image.new("RGB", (1600, 1000), "#111319")
    d = ImageDraw.Draw(img)
    d.text((55, 35), "逐帧候选求解", font=font(38, 1), fill="#F4F5F7")
    d.text((55, 92), "窗口与遮挡原因不是硬条件；模型只使用当前字符、顺序、来源和合法 source 结构。", font=font(22), fill="#AAB2BE")

    d.text((70, 165), "四条硬约束", font=font(26, 1), fill="#FFCE73")
    hard = [
        "一个 unknown cell 最多属于一个最终候选",
        "候选不能改写可靠 Observed provenance",
        "screen fragments 与 source ranges 的字符和顺序一致",
        "候选来自合法 record/source range 或 translation class",
    ]
    y = 215
    for i, line in enumerate(hard, 1):
        rect(d, (70, y, 760, y + 78), fill="#201B10", outline="#A66A00", width=2)
        d.text((100, y + 22), f"{i}. {line}", font=font(20), fill="#F4F5F7")
        y += 92

    d.text((840, 165), "软评分", font=font(26, 1), fill="#7DBAFF")
    soft = [
        "KnownGapFill 与 anchors 一致性",
        "完整边界、唯一子串、共同局部译文",
        "fragment 覆盖、顺序与控制符一致",
        "gap 数量、跨度、跨行和不必要合并",
        "写入时间、候选歧义与跨帧稳定",
    ]
    y = 215
    for line in soft:
        rect(d, (840, y, 1530, y + 67), fill="#17202A", outline="#3566A8", width=2)
        d.text((870, y + 18), line, font=font(20), fill="#F4F5F7")
        y += 81

    rect(d, (70, 665, 1530, 845), fill="#171A1F", outline="#49515B", width=2)
    d.text((100, 690), "字典序目标", font=font(24, 1), fill="#69E893")
    d.text((100, 742), "可靠性和唯一性  →  Observed 一致性  →  跨帧稳定  →  覆盖率", font=font(23), fill="#F4F5F7")
    d.text((100, 792), "最后最小化 fragment/gap 数；不强迫解释所有 unknown cells。", font=font(21), fill="#AAB2BE")
    d.text((55, 940), "MVP：分层 greedy + bounded beam search；只有证据显示需要时才升级 ILP/SAT。", font=font(21), fill="#AAB2BE")
    img.save(path, quality=95)


def draw_implementation_plan(path: Path):
    img = Image.new("RGB", (1600, 1000), "#F7F8FA")
    d = ImageDraw.Draw(img)
    d.text((70, 45), "建议实现顺序", font=font(42, 1), fill="#111319")
    d.text((70, 105), "先保护稳定来源路径，再逐步打开 unknown fallback。", font=font(23), fill="#4B5563")
    phases = [
        ("阶段 1", "离线索引与统一数据结构", "token、logical glyph、length map、full segment、translation class"),
        ("阶段 2", "迁移已知来源路径", "ObservedGroups → ResolvedGroups；先跑完现有回归"),
        ("阶段 3", "安全 Fallback MVP", "KnownGapFill、唯一 FullSegment、EquivalentPhrase、cell 排他"),
        ("阶段 4", "子串与多 Fragment", "任意 offset、UniqueSubstring、OrderedMultiFragment、gap penalty"),
        ("阶段 5", "跨帧稳定与性能", "FallbackTrack、候选缓存、bounded beam、诊断与基准"),
    ]
    y = 175
    colors = ["#3566A8", "#28834C", "#A66A00", "#7546A5", "#586270"]
    for (phase, title, body), accent in zip(phases, colors):
        rect(d, (105, y, 1495, y + 125), fill="#FFFFFF", outline=accent, width=3)
        rect(d, (105, y, 285, y + 125), fill=accent)
        d.text((195, y + 62), phase, font=font(24, 1), fill="#FFFFFF", anchor="mm")
        d.text((325, y + 17), title, font=font(25, 1), fill="#111319")
        d.text((325, y + 72), body, font=font(20), fill="#4B5563")
        y += 145
    d.text((70, 930), "每阶段都记录：候选来源、得分、拒绝原因、最终占用 cells 与误译率。", font=font(21, 1), fill="#3566A8")
    img.save(path, quality=95)


def draw_remaining_gaps_core(path: Path):
    img = Image.new("RGB", (1600, 1000), "#111319")
    d = ImageDraw.Draw(img)
    d.text((55, 35), "统一算法仍未完全支持的 Cases", font=font(36, 1), fill="#F4F5F7")
    d.text((55, 92), "算法设计边界；不代表当前代码已经实现前述能力。", font=font(22), fill="#AAB2BE")
    groups = [
        ("没有核心解决方案", "17 write generation · 22 ITEM 参数 · 23 game state · 31 UI · 32 无译文", "#FF515E"),
        ("只能近似支持", "12 日中语序 · 27 超长译文 · 28 多行高度", "#FFB020"),
        ("Fallback 不保证成功", "8 整行丢失 · 18 copy/redraw · 29 歧义词 · 33 完全未知", "#59A8FF"),
        ("依赖前处理正确", "13 共享 span · 14 分支边界 · 15 logical glyph", "#7546A5"),
    ]
    y = 165
    for title, cases, accent in groups:
        rect(d, (70, y, 1530, y + 150), fill="#171A1F", outline=accent, width=3)
        d.text((105, y + 20), title, font=font(25, 1), fill=accent)
        for idx, line in enumerate(wrap(d, cases, font(22), 1320)):
            d.text((105, y + 76 + idx * 34), line, font=font(22), fill="#F4F5F7")
        y += 175
    d.text((55, 900), "主要剩余缺口：模板参数 · write/copy provenance · 布局 · record 前处理 · 短文本歧义", font=font(22, 1), fill="#FFCE73")
    d.text((55, 950), "安全原则：无法唯一确定时保留 Unknown，不以覆盖率强迫匹配。", font=font(20), fill="#AAB2BE")
    img.save(path, quality=95)


def draw_remaining_gaps_validation(path: Path):
    img = Image.new("RGB", (1600, 1000), "#F7F8FA")
    d = ImageDraw.Draw(img)
    d.text((70, 45), "实现期验证与外部机制", font=font(42, 1), fill="#111319")
    d.text((70, 105), "这些 Cases 有处理路径，但不能只依赖候选匹配算法。", font=font(23), fill="#4B5563")
    items = [
        ("Case 19", "道具列表", "验证多行不误合并，名称与数量保持对应", "#3566A8"),
        ("Case 20", "商店价格与名称", "增加文本与数值管道的 screen-layout composition", "#3566A8"),
        ("Case 24", "子窗口覆盖底层菜单", "验证 gap/fragment penalty 能抑制远距离错误合并", "#3566A8"),
        ("Case 25", "帧内半成品", "只在帧末求解和发布", "#28834C"),
        ("Case 26", "快速操作滞后", "候选缓存、增量计算与 beam 宽度性能测试", "#28834C"),
        ("Case 30", "启动时幽灵文字", "启动、换 ROM、断开时清空 scene 与 tracks", "#28834C"),
    ]
    y = 175
    for case, title, body, accent in items:
        rect(d, (105, y, 1495, y + 105), fill="#FFFFFF", outline=accent, width=2)
        d.text((135, y + 18), case, font=font(21, 1), fill=accent)
        d.text((300, y + 18), title, font=font(23, 1), fill="#111319")
        d.text((620, y + 22), body, font=font(20), fill="#4B5563")
        y += 122
    d.text((70, 930), "提交前要求：每类候选记录来源、得分、拒绝原因、最终 cells 与误译结果。", font=font(21, 1), fill="#3566A8")
    img.save(path, quality=95)


def set_cell_margins(cell, top=100, start=120, bottom=100, end=120):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcMar = tcPr.first_child_found_in("w:tcMar")
    if tcMar is None:
        tcMar = OxmlElement("w:tcMar")
        tcPr.append(tcMar)
    for m, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tcMar.find(qn(f"w:{m}"))
        if node is None:
            node = OxmlElement(f"w:{m}")
            tcMar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def shade_cell(cell, color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = tcPr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tcPr.append(shd)
    shd.set(qn("w:fill"), color)


def add_picture_with_alt(paragraph, path: Path, alt: str):
    run = paragraph.add_run()
    inline = run.add_picture(str(path), width=Inches(8.85))
    doc_pr = inline._inline.docPr
    doc_pr.set("descr", alt)
    return inline


def set_font(run, name="Arial Unicode MS", size=10, bold=False, color="000000"):
    run.font.name = name
    run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), name)
    run.font.size = Pt(size)
    run.bold = bold
    run.font.color.rgb = RGBColor.from_string(color)


def build_doc():
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    for index, (title, _status, _summary, lines, output, kind) in enumerate(CASES, 1):
        draw_scene(index, title, lines, output, kind, ASSET_DIR / f"case-{index:02d}.png")
    draw_cover(ASSET_DIR / "cover.png")
    draw_layer_boundary(ASSET_DIR / "layer-boundary.png")
    draw_case_classification(ASSET_DIR / "case-classification.png")
    draw_toc(ASSET_DIR / "toc.png")
    draw_candidate_model_overview(ASSET_DIR / "candidate-model-overview.png")
    draw_length_mapping(ASSET_DIR / "candidate-length-mapping.png")
    draw_fallback_model(ASSET_DIR / "candidate-fallback.png")
    draw_unified_algorithm(ASSET_DIR / "unified-algorithm.png")
    draw_offline_indexes(ASSET_DIR / "offline-indexes.png")
    draw_solver_rules(ASSET_DIR / "solver-rules.png")
    draw_implementation_plan(ASSET_DIR / "implementation-plan.png")
    draw_remaining_gaps_core(ASSET_DIR / "remaining-gaps-core.png")
    draw_remaining_gaps_validation(ASSET_DIR / "remaining-gaps-validation.png")
    for letter, title, description, numbers, accent in CATEGORIES:
        draw_category_page(letter, title, description, numbers, accent, ASSET_DIR / f"category-{letter.lower()}.png")

    doc = Document()
    section = doc.sections[0]
    section.orientation = WD_ORIENT.LANDSCAPE
    section.page_width = Inches(11)
    section.page_height = Inches(8.5)
    section.top_margin = Inches(0.55)
    section.bottom_margin = Inches(0.5)
    section.left_margin = Inches(0.65)
    section.right_margin = Inches(0.65)

    styles = doc.styles
    styles["Normal"].font.name = "Arial Unicode MS"
    styles["Normal"]._element.rPr.rFonts.set(qn("w:eastAsia"), "Arial Unicode MS")
    styles["Normal"].font.size = Pt(10)
    for style_name, size in (("Title", 28), ("Heading 1", 18), ("Heading 2", 14)):
        style = styles[style_name]
        style.font.name = "Arial Unicode MS"
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "Arial Unicode MS")
        style.font.size = Pt(size)
        style.font.color.rgb = RGBColor(0, 0, 0)
        style.font.bold = True

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(0)
    run = p.add_run()
    cover_inline = run.add_picture(str(ASSET_DIR / "cover.png"), width=Inches(8.9))
    cover_inline._inline.docPr.set("descr", "NES 运行时翻译模型视觉审查手册封面和图例")
    doc.add_page_break()

    for filename, alt in (
        ("toc.png", "按五类问题组织的目录，列出 Case 编号、标题和页码"),
        ("layer-boundary.png", "Record 前处理、来源采集、Nametable 可见模型、译文布局和发布诊断的五层边界图"),
        ("case-classification.png", "33 个 Corner Cases 按五层责任划分的分类图"),
        ("candidate-model-overview.png", "候选可见 Glyph 与长度映射模型的处理流程"),
        ("candidate-length-mapping.png", "原文到翻译字符的分段长度映射与遮挡示例"),
        ("candidate-fallback.png", "无 recordId 时的临时分组、翻译包检索和置信度处理流程"),
        ("unified-algorithm.png", "已知来源固定锚点与未知来源候选的统一逐帧算法"),
        ("offline-indexes.png", "实现统一算法前需要离线编译的翻译包索引"),
        ("solver-rules.png", "统一求解器的硬约束、软评分和优化优先级"),
        ("implementation-plan.png", "从离线索引到跨帧优化的五阶段实现顺序"),
        ("remaining-gaps-core.png", "统一算法仍不能、只能近似或只能条件支持的 Cases"),
        ("remaining-gaps-validation.png", "需要实现期重点验证或依赖外部运行机制的 Cases"),
    ):
        pic_p = doc.add_paragraph()
        pic_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        pic_p.paragraph_format.space_after = Pt(0)
        add_picture_with_alt(pic_p, ASSET_DIR / filename, alt)
        doc.add_page_break()

    display_items = []
    for letter, title, _description, numbers, _accent in CATEGORIES:
        display_items.append(("category", letter, title))
        display_items.extend(("case", number, CASES[number - 1][0]) for number in numbers)

    for item_index, (item_type, item_id, title) in enumerate(display_items):
        pic_p = doc.add_paragraph()
        pic_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        pic_p.paragraph_format.space_after = Pt(4)
        if item_type == "category":
            add_picture_with_alt(pic_p, ASSET_DIR / f"category-{str(item_id).lower()}.png", f"{item_id} 类 {title} 的分组页")
        else:
            add_picture_with_alt(pic_p, ASSET_DIR / f"case-{item_id:02d}.png", f"Case {item_id:02d} {title} 的游戏格子示意图")
        if item_index != len(display_items) - 1:
            doc.add_page_break()

    doc.core_properties.title = "NES 运行时翻译模型视觉审查手册"
    doc.core_properties.subject = "运行时翻译模型与 Corner Cases"
    doc.core_properties.author = "MesenCE Project"
    doc.save(OUTPUT)


if __name__ == "__main__":
    build_doc()

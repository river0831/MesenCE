# Dragon Quest 原 ROM 文本全量提取与中文审阅目录

- ROM SHA-256: `f3973016ecc113ec89b8b20f49072a2ff677d6b581920683d9c72acc4b667a3e`
- 总记录：**686**（CHR `$FC` 候选 563；PRG 词典 123）
- `reviewed`：现有运行时数据库已采用；`draft`：本轮人工草译；`pending`：保留原文，尚未可靠翻译。
- `uncertain-or-graphics` 不代表台词：它们是为保证“尽可能多提取”而保留的低可信字节记录。

## 文本类型概览

- `armor`：8
- `battle`：11
- `chest-or-system`：10
- `dynamic-template`：16
- `item`：16
- `item-spell-action`：32
- `npc-dialogue`：116
- `phrase`：55
- `shield`：3
- `shop-or-inn`：30
- `story-or-ending`：12
- `system-or-unknown`：78
- `system-template`：6
- `uncertain-or-graphics`：258
- `unresolved`：28
- `weapon`：7

## 翻译进度

- `draft`：237
- `pending`：402
- `reviewed`：47

## 游戏显示难度

- `easy`：165
- `hard`：515
- `medium`：6

`easy` 表示固定短文本、无动态变量和未解析字节；适合优先接入游戏。
`medium` 通常只是较长或跨页；`hard` 则含动态对象、玩家名、数字或未解析编码。

## 建议优先接入游戏的固定文本（79 条）

这些记录已有中文，而且不依赖玩家名、敌人名、道具名或运行时数字。

- `chr-fc-20df`：再见，旅行者。请不要太勉强自己。
- `chr-fc-212a`：愿神明庇佑你。
- `chr-fc-2140`：这里没有楼梯。
- `chr-fc-214f`：不能从这里进入。
- `chr-fc-215b`：那个方向没有人。
- `chr-fc-216d`：谢谢惠顾。还要再买一瓶吗？
- `chr-fc-21a3`：那么，再见。
- `chr-fc-2257`：还有什么要卖给我吗？
- `chr-fc-2263`：这个我们不能收购。
- `chr-fc-229a`：您要卖哪一件？
- `chr-fc-22a2`：恭候您再次光临。
- `chr-fc-22b8`：还要买别的吗？
- `chr-fc-2306`：您想要哪一件？
- `chr-fc-230f`：欢迎光临。这里是道具店。您需要什么？
- `chr-fc-2331`：这样啊，真遗憾。
- `chr-fc-233e`：这样可以吗？
- `chr-fc-238a`：抱歉，你的钱好像不够。
- `chr-fc-23a0`：还要买点别的吗？
- `chr-fc-23ad`：要买什么？
- `chr-fc-23b6`：非常感谢。
- `chr-fc-23be`：下次再来啊。
- `chr-fc-23e8`：MP不足。
- `chr-fc-23f4`：但是什么也没有发生。
- `chr-fc-2413`：火把要在黑暗的地方使用。
- `chr-fc-2437`：圣水失效了。
- `chr-fc-2448`：这里不能使用奇美拉之翼。
- `chr-fc-247c`：龙鳞已经装备着了。
- `chr-fc-2496`：现在还没有可使用的物品。
- `chr-fc-2520`：被诅咒的人啊，滚出去！
- `chr-fc-2532`：我正在寻找地下室。听说它就在城堡的某个地方……
- `chr-fc-25a0`：只要有复活咒文，就能以听到咒文时的状态重新醒来。
- `chr-fc-25cf`：当雨与太阳相遇时，彩虹之桥就会出现。
- `chr-fc-25e0`：真正的勇者应该不会偷窃。
- `chr-fc-2611`：让我们为勇者祈祷。愿光明与你同在。
- `chr-fc-2637`：如果对自己的体力有信心，就进去吧。
- `chr-fc-264e`：我们是旅行商人。许多同伴都被魔物杀害了。
- `chr-fc-26f1`：仔细听人们说的话吧，一定会派上用场。
- `chr-fc-2719`：过桥时要小心！越过桥走得越远，遇到的魔物就越可怕。
- `chr-fc-2770`：请从那里凹进去的地方向里面走。
- `chr-fc-278a`：欢迎光临。请往里面走，隔着柜台和我说话。
- `chr-fc-27b7`：小心毒沼泽。走在沼泽中时要留意体力。
- `chr-fc-2820`：请打倒那些魔物。
- `chr-fc-29b9`：我很忙，去问旁边那个人吧。
- `chr-fc-2a0b`：我最讨厌男人了。走开，走开！
- `chr-fc-2ab9`：我听说了！掳走公主的魔物竟然朝东方飞去了！
- `chr-fc-2ae3`：欢迎！今天萝卜很便宜！
- `chr-fc-2afa`：如果你想寻找印记，就去拜访住在这座城镇神殿里的长老。
- `chr-fc-2b56`：今晚做什么菜好呢……
- `chr-fc-2c70`：欢迎光临！
- `chr-fc-2ca9`：听说龙王的鳞片像钢铁一样坚硬。
- `chr-fc-2da6`：不要去南方。听说那里住着强大得多的魔物。
- `chr-fc-2dd1`：这个世界上真的有能够刺穿龙王身体的剑吗？
- `chr-fc-2e48`：你拿到笛子了吗？
- `chr-fc-2e51`：你去过南方的岛吗？
- `chr-fc-2ea0`：这里是预言所。你找到神圣祠堂了吗？
- `chr-fc-2eb7`：进入洞窟时要带上火把。
- `chr-fc-2ee0`：什么！听说那里有非常强大的魔物……
- `chr-fc-2efb`：噢！你才是真正的勇者！
- `chr-fc-2f09`：这里是雨与太阳交汇的祠堂。
- `chr-fc-2f4d`：这样就好。没有人会说你是胆小鬼。
- `chr-fc-2f6e`：往南方去吧。
- `chr-fc-2f8a`：感谢你救出了公主。
- `chr-fc-2fda`：是谁在碰我？我已经什么也看不见，什么也听不见了……
- `chr-fc-30a0`：如果你中了诅咒，就到这里来。
- `chr-fc-310b`：居然戴着戒指，你这家伙真不害臊啊。
- `chr-fc-3122`：戒指是战士应有的装束。
- `chr-fc-314d`：去吧，然后寻找吧。
- `chr-fc-3178`：这是一个古老传说。
- `chr-fc-3460`：来，去拿宝箱吧。
- `chr-fc-34cb`：愚蠢的家伙！让你尝尝厉害！
- `chr-fc-352a`：但不丢掉一些东西，就再也拿不下了。要丢掉什么吗？
- `chr-fc-3552`：要丢掉什么？
- `chr-fc-3564`：怎么能把那个扔掉！
- `chr-fc-359c`：有一个宝箱！
- `chr-fc-35b2`：从王座后方感觉到一阵风。
- `chr-fc-35c8`：这里什么也拿不到。
- `chr-fc-3cf1`：你说的是真的吗？
- `chr-fc-3e97`：多亏了您，和平终于恢复了！国王也一定会非常高兴！
- `chr-fc-3ec2`：快去国王身边吧！

## 可读文本（高/中可信 CHR 与全部 PRG 词典）

### chr-fc-16f7 · `system-or-unknown` · `pending` · display `hard`

- 位置：CHR `$16F7` / file `$9707`
- 原文：<00><00><49><4A><68>あめと たいようが あわさるぞぞ゙<END>
- 中文：（待翻译/待确认）
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-1a0b · `system-or-unknown` · `pending` · display `hard`

- 位置：CHR `$1A0B` / file `$9A1B`
- 原文：゛゙ぞぞあめと たいようが あわさる<00><40><47>゙<6B><4E><4D><END>
- 中文：（待翻译/待确认）
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-1ef7 · `system-or-unknown` · `pending` · display `hard`

- 位置：CHR `$1EF7` / file `$9F07`
- 原文：ぞあめと たいようが あわさるあめと たいようが あわさるぞ<F0>゙<END>
- 中文：（待翻译/待确认）
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-2014 · `npc-dialogue` · `draft` · display `hard`

- 位置：CHR `$2014` / file `$A024`
- 原文：＊「そなたは もう じゅう<E8>んに / つよい！ なぜに まだ / りゅうおうを たおせぬのか<60> / <57><FF>＊「たびをいちど やめたいときは / おうにあい ふっかつのじゅもんを / きいておくことだな<4F><END>
- 中文：你已经足够强大了！为什么还没有打倒龙王？如果想暂时结束旅程，就去见国王，记下复活咒文。
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-2067 · `item-spell-action` · `draft` · display `hard`

- 位置：CHR `$2067` / file `$A077`
- 原文：{PLAYER_NAME}は にじのしずくを / てんに かざした<4F> / <57><FF>しかし<50> ここに にじは / かからなかった<4F><END>
- 中文：{PLAYER_NAME}把彩虹水滴高举向天空。然而这里没有架起彩虹。
- 显示判断：contains a runtime-substituted name, object, enemy, or number

### chr-fc-208d · `shop-or-inn` · `draft` · display `hard`

- 位置：CHR `$208D` / file `$A09D`
- 原文：＊「おはよう ございます<4F> / ゆう<E9>は おたのしみでしたね<4F> / <57><FF>＊「では また どうぞ<4F><END>
- 中文：早上好。昨晚过得愉快吧。那么，欢迎下次再来。
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-20b3 · `shop-or-inn` · `draft` · display `hard`

- 位置：CHR `$20B3` / file `$A0C3`
- 原文：＊「おはよう ございます<4F> / ゆう<E9>は よく おやすみ / でしたね<4F> / <57><FF>＊「では おやすみなさいませ<4F><END>
- 中文：早上好。昨晚睡得好吗？那么，请再好好休息。
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-20df · `npc-dialogue` · `draft` · display `easy`

- 位置：CHR `$20DF` / file `$A0EF`
- 原文：＊「さようなら たびのひと<4F> あまり / むりを なさいませぬように<4F><END>
- 中文：再见，旅行者。请不要太勉强自己。
- 显示判断：short fixed text with only understood layout controls

### chr-fc-2100 · `shop-or-inn` · `draft` · display `hard`

- 位置：CHR `$2100` / file `$A110`
- 原文：＊「たびびとの やどやへ ようこそ<4F> / ひとばん <F3><00><00><45>゙<4E><43><42>ですが / おとまりに なりますか<60><END>
- 中文：欢迎来到旅人旅店。住一晚需要<F3>金币，要住宿吗？
- 显示判断：contains a runtime-substituted name, object, enemy, or number

### chr-fc-212a · `npc-dialogue` · `draft` · display `easy`

- 位置：CHR `$212A` / file `$A13A`
- 原文：＊「あなたに かみの ごかごが / ありますように<4F><END>
- 中文：愿神明庇佑你。
- 显示判断：short fixed text with only understood layout controls

### chr-fc-2140 · `system-or-unknown` · `draft` · display `easy`

- 位置：CHR `$2140` / file `$A150`
- 原文：ここには かいだんが ない<4F><END>
- 中文：这里没有楼梯。
- 显示判断：short fixed text with only understood layout controls

### chr-fc-214f · `system-or-unknown` · `draft` · display `easy`

- 位置：CHR `$214F` / file `$A15F`
- 原文：ここでは はいれない<4F><END>
- 中文：不能从这里进入。
- 显示判断：short fixed text with only understood layout controls

### chr-fc-215b · `system-or-unknown` · `reviewed` · display `easy`

- 位置：CHR `$215B` / file `$A16B`
- 原文：そのほうこうには だれも いない<4F><END>
- 中文：那个方向没有人。
- 显示判断：short fixed text with only understood layout controls

### chr-fc-216d · `shop-or-inn` · `draft` · display `easy`

- 位置：CHR `$216D` / file `$A17D`
- 原文：＊「ありがとうございます<4F> / もう ひとびん / かわれますか<60><END>
- 中文：谢谢惠顾。还要再买一瓶吗？
- 显示判断：short fixed text with only understood layout controls

### chr-fc-217e · `shop-or-inn` · `draft` · display `hard`

- 位置：CHR `$217E` / file `$A18E`
- 原文：＊「まものよけの せいすいは / いかがでしょう<60> / ひとびん <03><08><45>゙<4E><43><42>ですが<4F><END>
- 中文：可以买一瓶驱除魔物的圣水，价格是38金币。
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-21a3 · `npc-dialogue` · `draft` · display `easy`

- 位置：CHR `$21A3` / file `$A1B3`
- 原文：＊「では またな<END>
- 中文：那么，再见。
- 显示判断：short fixed text with only understood layout controls

### chr-fc-21ab · `shop-or-inn` · `draft` · display `medium`

- 位置：CHR `$21AB` / file `$A1BB`
- 原文：＊「おまえさまは おかねが / たらないようじゃな<4F> / <57><FF>＊「わるいが これいじょう / うるわけには いかんな<4F> / <57><FF>＊「ほれ<4F> かぎをひとつ わたそう<4F> / まだ かぎを かうかな<60><END>
- 中文：看来你的钱不够。抱歉，不能再便宜了。来，给你一把钥匙。还要买钥匙吗？
- 显示判断：fixed text, but long or split across several dialogue pages

### chr-fc-21fa · `shop-or-inn` · `draft` · display `hard`

- 位置：CHR `$21FA` / file `$A20A`
- 原文：＊「どんなとびらも あけてしまう / まほうの かぎは いらんかな<60> / ひとつ <F3><00><00><45>゙<4E><43><42>でどうじゃ<60><END>
- 中文：要不要一把能打开任何门的魔法钥匙？一把<F3>金币，怎么样？
- 显示判断：contains a runtime-substituted name, object, enemy, or number

### chr-fc-222c · `system-or-unknown` · `draft` · display `medium`

- 位置：CHR `$222C` / file `$A23C`
- 原文：＊「ざんねんです<4F> / <57><FF>のろいで からだから はなれない！ / <57><FF>＊「もちものが ありません<4F><END>
- 中文：真遗憾。因为诅咒，它无法离开身体！没有携带任何物品。
- 显示判断：fixed text, but long or split across several dialogue pages

### chr-fc-2257 · `shop-or-inn` · `draft` · display `easy`

- 位置：CHR `$2257` / file `$A267`
- 原文：＊「まだ なにか うってくれますか<60><END>
- 中文：还有什么要卖给我吗？
- 显示判断：short fixed text with only understood layout controls

### chr-fc-2263 · `shop-or-inn` · `draft` · display `easy`

- 位置：CHR `$2263` / file `$A273`
- 原文：＊「それを かうわけには / まいりません<4F><END>
- 中文：这个我们不能收购。
- 显示判断：short fixed text with only understood layout controls

### chr-fc-2277 · `shop-or-inn` · `draft` · display `hard`

- 位置：CHR `$2277` / file `$A287`
- 原文：＊「<FD>で ございますね<4F> / それなら <F3><00><00><45>゙<4E><43><42>で / かいましょう<4F> いいですか<60><END>
- 中文：您要卖<FD>吧？那么我出<F3>金币收购，可以吗？
- 显示判断：contains a runtime-substituted name, object, enemy, or number

### chr-fc-229a · `shop-or-inn` · `draft` · display `easy`

- 位置：CHR `$229A` / file `$A2AA`
- 原文：＊「どれを おうりですか<60><END>
- 中文：您要卖哪一件？
- 显示判断：short fixed text with only understood layout controls

### chr-fc-22a2 · `shop-or-inn` · `draft` · display `easy`

- 位置：CHR `$22A2` / file `$A2B2`
- 原文：＊「では またの おこしを / おまち しております<4F><END>
- 中文：恭候您再次光临。
- 显示判断：short fixed text with only understood layout controls

### chr-fc-22b8 · `shop-or-inn` · `draft` · display `easy`

- 位置：CHR `$22B8` / file `$A2C8`
- 原文：＊「ほかに なにか かわれますか<60><END>
- 中文：还要买别的吗？
- 显示判断：short fixed text with only understood layout controls

### chr-fc-22c4 · `shop-or-inn` · `draft` · display `hard`

- 位置：CHR `$22C4` / file `$A2D4`
- 原文：＊「それいじょう やくそうを / もてませんが<4F> / <57><FF>＊「それいじょう もちものを / もてませんが<4F> / <57><FF>＊「おかねが たりませんが<4F> / <57><FF>＊「<FD>で ございますね<4F> / まいど ありがとうございます<4F><END>
- 中文：不能再携带更多药草了。不能再携带更多物品了。金钱不够。您要的是<FD>吧？感谢惠顾。
- 显示判断：contains a runtime-substituted name, object, enemy, or number

### chr-fc-2306 · `shop-or-inn` · `draft` · display `easy`

- 位置：CHR `$2306` / file `$A316`
- 原文：＊「どれを おもとめですか<60><END>
- 中文：您想要哪一件？
- 显示判断：short fixed text with only understood layout controls

### chr-fc-230f · `shop-or-inn` · `draft` · display `easy`

- 位置：CHR `$230F` / file `$A31F`
- 原文：＊「いらっしゃいませ<4F> / ここは どうぐや です<4F> / どんな ごようでしょうか<60><END>
- 中文：欢迎光临。这里是道具店。您需要什么？
- 显示判断：short fixed text with only understood layout controls

### chr-fc-2331 · `shop-or-inn` · `draft` · display `easy`

- 位置：CHR `$2331` / file `$A341`
- 原文：＊「そうか ざんねんだな<4F><END>
- 中文：这样啊，真遗憾。
- 显示判断：short fixed text with only understood layout controls

### chr-fc-233e · `shop-or-inn` · `draft` · display `easy`

- 位置：CHR `$233E` / file `$A34E`
- 原文：<57>＊「それで いいかね<60><END>
- 中文：这样可以吗？
- 显示判断：short fixed text with only understood layout controls

### chr-fc-234a · `shop-or-inn` · `draft` · display `hard`

- 位置：CHR `$234A` / file `$A35A`
- 原文：＊「ここは <E8>きとよろいの みせだ<4F> / なにか かうかね<60><END>
- 中文：这里是武器和防具店。要买点什么吗？
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-2368 · `shop-or-inn` · `draft` · display `hard`

- 位置：CHR `$2368` / file `$A378`
- 原文：<57>＊「では いまつかっている / <FD>を / <F3><00><00><45>゙<4E><43><42>で ひきとろう<4F><END>
- 中文：那么，你现在使用的<FD>，我出<F3>金币收购。
- 显示判断：contains a runtime-substituted name, object, enemy, or number

### chr-fc-238a · `shop-or-inn` · `draft` · display `easy`

- 位置：CHR `$238A` / file `$A39A`
- 原文：<57>＊「すまないが おかねが / たりないようだ<4F><END>
- 中文：抱歉，你的钱好像不够。
- 显示判断：short fixed text with only understood layout controls

### chr-fc-23a0 · `shop-or-inn` · `draft` · display `easy`

- 位置：CHR `$23A0` / file `$A3B0`
- 原文：＊「ほかに なにか かうかね<60><END>
- 中文：还要买点别的吗？
- 显示判断：short fixed text with only understood layout controls

### chr-fc-23ad · `shop-or-inn` · `draft` · display `easy`

- 位置：CHR `$23AD` / file `$A3BD`
- 原文：＊「なにを かうかね<60><END>
- 中文：要买什么？
- 显示判断：short fixed text with only understood layout controls

### chr-fc-23b6 · `shop-or-inn` · `draft` · display `easy`

- 位置：CHR `$23B6` / file `$A3C6`
- 原文：＊「どうも ありがとう<4F><END>
- 中文：非常感谢。
- 显示判断：short fixed text with only understood layout controls

### chr-fc-23be · `shop-or-inn` · `draft` · display `easy`

- 位置：CHR `$23BE` / file `$A3CE`
- 原文：＊「また きてくれよな<4F><END>
- 中文：下次再来啊。
- 显示判断：short fixed text with only understood layout controls

### chr-fc-23ca · `dynamic-template` · `draft` · display `hard`

- 位置：CHR `$23CA` / file `$A3DA`
- 原文：{PLAYER_NAME}は <FD>の / じゅもんを となえた！<END>
- 中文：{PLAYER_NAME}咏唱了<FD>咒文！
- 显示判断：contains a runtime-substituted name, object, enemy, or number

### chr-fc-23d9 · `item-spell-action` · `draft` · display `hard`

- 位置：CHR `$23D9` / file `$A3E9`
- 原文：{PLAYER_NAME}は まだ じゅもんを / つかえない<4F><END>
- 中文：{PLAYER_NAME}还不会使用咒文。
- 显示判断：contains a runtime-substituted name, object, enemy, or number

### chr-fc-23e8 · `system-or-unknown` · `draft` · display `easy`

- 位置：CHR `$23E8` / file `$A3F8`
- 原文：MP が たりません<4F><END>
- 中文：MP不足。
- 显示判断：short fixed text with only understood layout controls

### chr-fc-23f4 · `system-or-unknown` · `draft` · display `easy`

- 位置：CHR `$23F4` / file `$A404`
- 原文：しかし なにも おきなかった<4F><END>
- 中文：但是什么也没有发生。
- 显示判断：short fixed text with only understood layout controls

### chr-fc-2402 · `item-spell-action` · `draft` · display `hard`

- 位置：CHR `$2402` / file `$A412`
- 原文：<6B>へ<41><69>の こうりょくが / なくなった<4F><END>
- 中文：咒文的效果消失了。
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-2413 · `item-spell-action` · `draft` · display `easy`

- 位置：CHR `$2413` / file `$A423`
- 原文：たいまつは くらいところで / つかうものです<4F><END>
- 中文：火把要在黑暗的地方使用。
- 显示判断：short fixed text with only understood layout controls

### chr-fc-2425 · `item-spell-action` · `draft` · display `hard`

- 位置：CHR `$2425` / file `$A435`
- 原文：{PLAYER_NAME}は せいすいを からだに / ふりかけた<4F><END>
- 中文：{PLAYER_NAME}把圣水洒在身上。
- 显示判断：contains a runtime-substituted name, object, enemy, or number

### chr-fc-2437 · `item-spell-action` · `draft` · display `easy`

- 位置：CHR `$2437` / file `$A447`
- 原文：せいすいの こうりょくが / なくなった<4F><END>
- 中文：圣水失效了。
- 显示判断：short fixed text with only understood layout controls

### chr-fc-2448 · `item-spell-action` · `draft` · display `easy`

- 位置：CHR `$2448` / file `$A458`
- 原文：ここでは つばさを つかえない<4F><END>
- 中文：这里不能使用奇美拉之翼。
- 显示判断：short fixed text with only understood layout controls

### chr-fc-2459 · `item-spell-action` · `draft` · display `hard`

- 位置：CHR `$2459` / file `$A469`
- 原文：{PLAYER_NAME}は つばさを おおぞらに / ほうりなげた<4F><END>
- 中文：{PLAYER_NAME}把奇美拉之翼抛向天空。
- 显示判断：contains a runtime-substituted name, object, enemy, or number

### chr-fc-246f · `item-spell-action` · `draft` · display `hard`

- 位置：CHR `$246F` / file `$A47F`
- 原文：{PLAYER_NAME}は りゅうのうろこを / みにつけた<4F><END>
- 中文：{PLAYER_NAME}装备了龙鳞。
- 显示判断：contains a runtime-substituted name, object, enemy, or number

### chr-fc-247c · `item-spell-action` · `draft` · display `easy`

- 位置：CHR `$247C` / file `$A48C`
- 原文：りゅうのうろこは すでに / みにつけています<4F><END>
- 中文：龙鳞已经装备着了。
- 显示判断：short fixed text with only understood layout controls

### chr-fc-248b · `item-spell-action` · `draft` · display `hard`

- 位置：CHR `$248B` / file `$A49B`
- 原文：{PLAYER_NAME}は ふえをふいた<4F><END>
- 中文：{PLAYER_NAME}吹响了笛子。
- 显示判断：contains a runtime-substituted name, object, enemy, or number

### chr-fc-2496 · `item-spell-action` · `draft` · display `easy`

- 位置：CHR `$2496` / file `$A4A6`
- 原文：つかえるものを まだ / もっていない<4F><END>
- 中文：现在还没有可使用的物品。
- 显示判断：short fixed text with only understood layout controls

### chr-fc-24a8 · `item-spell-action` · `draft` · display `hard`

- 位置：CHR `$24A8` / file `$A4B8`
- 原文：{PLAYER_NAME}は せんしのゆびわを / はめた<4F><END>
- 中文：{PLAYER_NAME}戴上了战士戒指。
- 显示判断：contains a runtime-substituted name, object, enemy, or number

### chr-fc-24b3 · `item-spell-action` · `draft` · display `hard`

- 位置：CHR `$24B3` / file `$A4C3`
- 原文：{PLAYER_NAME}は せんしのゆびわを / はめなおした<4F><END>
- 中文：{PLAYER_NAME}重新戴好了战士戒指。
- 显示判断：contains a runtime-substituted name, object, enemy, or number

### chr-fc-24c1 · `item-spell-action` · `draft` · display `hard`

- 位置：CHR `$24C1` / file `$A4D1`
- 原文：{PLAYER_NAME}は <FD>を / にぎりしめた<4F><END>
- 中文：{PLAYER_NAME}紧紧握住了<FD>。
- 显示判断：contains a runtime-substituted name, object, enemy, or number

### chr-fc-24cf · `item-spell-action` · `draft` · display `hard`

- 位置：CHR `$24CF` / file `$A4DF`
- 原文：{PLAYER_NAME}は たてごとを かなでた<4F><END>
- 中文：{PLAYER_NAME}弹奏了银竖琴。
- 显示判断：contains a runtime-substituted name, object, enemy, or number

### chr-fc-24de · `item-spell-action` · `draft` · display `hard`

- 位置：CHR `$24DE` / file `$A4EE`
- 原文：{PLAYER_NAME}は <FD>を / みにつけた<4F> / <57><FD>が あなたの / からだを しめつける<4F> / あなたは のろわれてしまった<4F><END>
- 中文：{PLAYER_NAME}装备了<FD>。<FD>紧紧勒住你的身体，你受到了诅咒。
- 显示判断：contains a runtime-substituted name, object, enemy, or number

### chr-fc-250c · `dynamic-template` · `draft` · display `hard`

- 位置：CHR `$250C` / file `$A51C`
- 原文：<FD>が あなたの / からだを しめつけている！<END>
- 中文：<FD>正紧紧勒住你的身体！
- 显示判断：contains a runtime-substituted name, object, enemy, or number

### chr-fc-2520 · `npc-dialogue` · `draft` · display `easy`

- 位置：CHR `$2520` / file `$A530`
- 原文：＊「のろわれしものよ<50>でてゆけっ！<FB><END>
- 中文：被诅咒的人啊，滚出去！
- 显示判断：short fixed text with only understood layout controls

### chr-fc-2532 · `npc-dialogue` · `draft` · display `easy`

- 位置：CHR `$2532` / file `$A542`
- 原文：＊「わたしは ちかしつを / さがしている<4F> おしろの / どこかに あるらしいが<6C><END>
- 中文：我正在寻找地下室。听说它就在城堡的某个地方……
- 显示判断：short fixed text with only understood layout controls

### chr-fc-254d · `npc-dialogue` · `draft` · display `hard`

- 位置：CHR `$254D` / file `$A55D`
- 原文：＊「とびらを あけるには / 力<6A>゙が ひつようだ<4F><END>
- 中文：要打开门，需要钥匙。
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-2562 · `npc-dialogue` · `draft` · display `hard`

- 位置：CHR `$2562` / file `$A572`
- 原文：＊「まものたちと たたかって / けいけんを つんでください<4F> / <57>＊「そうすれば ゆうしゃとしての / <44>べ<43>が つぎつぎとあがり / つよくなってゆくでしょう<4F><END>
- 中文：请与魔物战斗，积累经验。这样勇者的等级就会不断提升，逐渐变强。
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-25a0 · `npc-dialogue` · `draft` · display `easy`

- 位置：CHR `$25A0` / file `$A5B0`
- 原文：＊「ふっかつのじゅもんが あれば / それをきいたときの じょうたいで / よみがえることが できるだろう<4F><END>
- 中文：只要有复活咒文，就能以听到咒文时的状态重新醒来。
- 显示判断：short fixed text with only understood layout controls

### chr-fc-25cf · `npc-dialogue` · `draft` · display `easy`

- 位置：CHR `$25CF` / file `$A5DF`
- 原文：＊「あめと たいようが あわさるとき / にじのはしが できる<4F><END>
- 中文：当雨与太阳相遇时，彩虹之桥就会出现。
- 显示判断：short fixed text with only understood layout controls

### chr-fc-25e0 · `npc-dialogue` · `draft` · display `easy`

- 位置：CHR `$25E0` / file `$A5F0`
- 原文：＊「まことの ゆうしゃなら / ぬすみなど せぬはずだ<4F><END>
- 中文：真正的勇者应该不会偷窃。
- 显示判断：short fixed text with only understood layout controls

### chr-fc-25f2 · `npc-dialogue` · `draft` · display `hard`

- 位置：CHR `$25F2` / file `$A602`
- 原文：＊「ここ <40><47>゙<6B><4E><4D>は そのむかし / らくえん でした<4F> / それを まものたちが<6C><END>
- 中文：这里从前曾是乐园，后来却被魔物们……
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-2611 · `npc-dialogue` · `draft` · display `easy`

- 位置：CHR `$2611` / file `$A621`
- 原文：＊「ゆうしゃのため いのりましょう<4F> / <57>＊「ひかりが そなたと ともに / ありますように<6C><END>
- 中文：让我们为勇者祈祷。愿光明与你同在。
- 显示判断：short fixed text with only understood layout controls

### chr-fc-2637 · `npc-dialogue` · `draft` · display `easy`

- 位置：CHR `$2637` / file `$A647`
- 原文：＊「たいりょくに じしんが / あるなら はいるがよい<52><END>
- 中文：如果对自己的体力有信心，就进去吧。
- 显示判断：short fixed text with only understood layout controls

### chr-fc-264e · `npc-dialogue` · `draft` · display `easy`

- 位置：CHR `$264E` / file `$A65E`
- 原文：＊「わたしたちは たびの しょうにん / です<4F> おおくのなかまが / まものたちに ころされました<4F><END>
- 中文：我们是旅行商人。许多同伴都被魔物杀害了。
- 显示判断：short fixed text with only understood layout controls

### chr-fc-2675 · `npc-dialogue` · `draft` · display `hard`

- 位置：CHR `$2675` / file `$A685`
- 原文：＊「うわさでは まものたちに / ほろ<EA>された まちも / あるらしいです<4F><END>
- 中文：听说有些城镇已经被魔物毁灭了。
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-2688 · `npc-dialogue` · `draft` · display `hard`

- 位置：CHR `$2688` / file `$A698`
- 原文：＊「<40><47>゙<6B><4E><4D>の おしろに / ようこそ！<END>
- 中文：欢迎来到拉达托姆城堡！
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-2692 · `npc-dialogue` · `draft` · display `hard`

- 位置：CHR `$2692` / file `$A6A2`
- 原文：＊「力゙<40><4A>のはかは 力゙<40><4A>のまちに<4F> / まちに はいり くらやみのか<E9>を / おすがよい<52><END>
- 中文：加莱之墓就在加莱镇。进入镇里，推开黑暗中的墙壁吧。
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-26b3 · `npc-dialogue` · `draft` · display `hard`

- 位置：CHR `$26B3` / file `$A6C3`
- 原文：＊「おかねが たまったら <E8>きや / よろいを たかいものに / かいかえることだな<4F> / <57>＊「そうすれば もっと つよく / なるだろう<4F><END>
- 中文：攒够钱后，就把武器和铠甲换成更贵的吧。这样会变得更强。
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-26f1 · `npc-dialogue` · `draft` · display `easy`

- 位置：CHR `$26F1` / file `$A701`
- 原文：＊「ひとびとの はなしに みみを / かたむけることだ<4F> / きっと やくにたつだろう<4F><END>
- 中文：仔细听人们说的话吧，一定会派上用场。
- 显示判断：short fixed text with only understood layout controls

### chr-fc-2719 · `npc-dialogue` · `draft` · display `easy`

- 位置：CHR `$2719` / file `$A729`
- 原文：＊「はしに きをつけろ！ / <57>＊「はしをわたって とおくにいくほど / おそろしい まものたちが / あらわれるだろう<4F><END>
- 中文：过桥时要小心！越过桥走得越远，遇到的魔物就越可怕。
- 显示判断：short fixed text with only understood layout controls

### chr-fc-2748 · `npc-dialogue` · `draft` · display `hard`

- 位置：CHR `$2748` / file `$A758`
- 原文：＊「うわさでは どこかに まほうの / 力<6A>゙をうってる まちが / あるらしいですよ<4F><END>
- 中文：听说某处有一座出售魔法钥匙的城镇。
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-2764 · `npc-dialogue` · `draft` · display `hard`

- 位置：CHR `$2764` / file `$A774`
- 原文：＊「うわさでは 力゙<40><4A>のはかに / ぎんのたてごとが あるらしい<6C><END>
- 中文：听说加莱之墓里藏着银竖琴。
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-2770 · `npc-dialogue` · `draft` · display `easy`

- 位置：CHR `$2770` / file `$A780`
- 原文：＊「そこの へこんだところから / なかへ すすんでください<4F><END>
- 中文：请从那里凹进去的地方向里面走。
- 显示判断：short fixed text with only understood layout controls

### chr-fc-278a · `shop-or-inn` · `draft` · display `easy`

- 位置：CHR `$278A` / file `$A79A`
- 原文：＊「いらっしゃいませ<4F> / なかにすすみ つくえ ごしに / はなしかけてくださいな<4F><END>
- 中文：欢迎光临。请往里面走，隔着柜台和我说话。
- 显示判断：short fixed text with only understood layout controls

### chr-fc-27ae · `npc-dialogue` · `draft` · display `hard`

- 位置：CHR `$27AE` / file `$A7BE`
- 原文：＊「<40><47>゙<6B><4E><4D>のまちに ようこそ<4F><END>
- 中文：欢迎来到拉达托姆镇！
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-27b7 · `npc-dialogue` · `draft` · display `easy`

- 位置：CHR `$27B7` / file `$A7C7`
- 原文：＊「どくのぬまちに きをつけなされ<4F> / ぬまちを あるくときは / たいりょくに きをつかうようにな<END>
- 中文：小心毒沼泽。走在沼泽中时要留意体力。
- 显示判断：short fixed text with only understood layout controls

### chr-fc-27e4 · `npc-dialogue` · `draft` · display `hard`

- 位置：CHR `$27E4` / file `$A7F4`
- 原文：＊「このまちの ずっと きたにいき / うみ<E9>を にしにあるくと / 力゙<40><4A>のまちが あるそうです<4F><END>
- 中文：从这座城镇一直向北，再沿海岸向西走，听说那里有加莱镇。
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-280f · `npc-dialogue` · `draft` · display `hard`

- 位置：CHR `$280F` / file `$A81F`
- 原文：＊「い<4E>え わたしは / <41><4E><40>ひめじゃないわ<4F><END>
- 中文：不，我不是萝拉公主。
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-2820 · `npc-dialogue` · `draft` · display `easy`

- 位置：CHR `$2820` / file `$A830`
- 原文：＊「どうか まものたちを / たおして ください<4F><END>
- 中文：请打倒那些魔物。
- 显示判断：short fixed text with only understood layout controls

### chr-fc-282e · `npc-dialogue` · `draft` · display `hard`

- 位置：CHR `$282E` / file `$A83E`
- 原文：＊「たたかいで けいけんを つみ / <44>べ<43>が あがったときは / おうさまに あいに いけよ<4F><END>
- 中文：战斗积累经验、等级提升后，就去见国王吧。
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-2855 · `npc-dialogue` · `draft` · display `hard`

- 位置：CHR `$2855` / file `$A865`
- 原文：＊「おまえが <41><6B>の ちをひくもの<60> / なにか しょうこが あるのか<60><END>
- 中文：你就是继承洛特血脉的人？有什么证据吗？
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-286c · `npc-dialogue` · `draft` · display `hard`

- 位置：CHR `$286C` / file `$A87C`
- 原文：＊「<40><47>゙<6B><4E><4D>のおしろのみなみから / うみのむこうに おしろが / みえるでしょう<4F> / <57>＊「りゅうおうは そのしろに / いるとか<6C><4F>おお こわい<6C><4F><END>
- 中文：从拉达托姆城堡南边，可以看见海对岸的一座城堡。听说龙王就在那里。噢，真可怕……
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-28a9 · `npc-dialogue` · `draft` · display `hard`

- 位置：CHR `$28A9` / file `$A8B9`
- 原文：＊「ここは ろてん<E8>ろで / ございま<4E>す<4F> / <57>＊「こうようは りゅうまちで / ございま<4E>す<4F><END>
- 中文：这里是露天浴池。功效是治疗风湿。
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-28d1 · `npc-dialogue` · `draft` · display `hard`

- 位置：CHR `$28D1` / file `$A8E1`
- 原文：＊「<42><4D><42><4E><40>の はるかひがしに / すばらしい<E8>きを / うっているまちが あるらしい<4F><END>
- 中文：听说在麦拉遥远的东方，有一座出售优秀武器的城镇。
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-28f1 · `npc-dialogue` · `draft` · display `hard`

- 位置：CHR `$28F1` / file `$A901`
- 原文：＊「うわさでは り<4D><43><47>゙<4E><43>に / 力<6A>゙をうるみせが あるらしい<4F><END>
- 中文：听说里姆尔达尔有一家卖钥匙的店。
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-2904 · `npc-dialogue` · `draft` · display `hard`

- 位置：CHR `$2904` / file `$A914`
- 原文：＊「おれは ゆうていだ<4F> / <6A><4D>こうを さがしている<4F><END>
- 中文：我是悠帝，正在寻找米亚公。
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-291e · `npc-dialogue` · `draft` · display `hard`

- 位置：CHR `$291E` / file `$A92E`
- 原文：＊「みなみのしまは とても こわい / ところです<4F> / <57>＊「じゅう<E8>んに ちからをつけてから / いかないと いきて / もどれないでしょう<4F><END>
- 中文：南方的岛非常可怕。如果没有充分增强实力，恐怕无法活着回来。
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-295c · `npc-dialogue` · `draft` · display `hard`

- 位置：CHR `$295C` / file `$A96C`
- 原文：＊「<45>゙<4E><44><4D>は ふえのね が / にがてだときく<4F><END>
- 中文：听说巨像害怕笛声。
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-2974 · `npc-dialogue` · `draft` · display `hard`

- 位置：CHR `$2974` / file `$A984`
- 原文：＊「ここは <4B><4A><40>の むらです<4F><END>
- 中文：这里是麦拉村。
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-2980 · `npc-dialogue` · `draft` · display `hard`

- 位置：CHR `$2980` / file `$A990`
- 原文：＊「ふるい いいつたえでは / ようせいたちは <45>゙<4E><44><4D>を / ねむらせた そうじゃ<4F><END>
- 中文：古老传说中，妖精们曾让巨像沉睡。
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-299e · `npc-dialogue` · `draft` · display `hard`

- 位置：CHR `$299E` / file `$A9AE`
- 原文：＊「たてごとは まものたちを / よびよせる<4F> / 力゙<40><4A>のはかに ちかよるな！<END>
- 中文：竖琴会招来魔物。不要靠近加莱之墓！
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-29b9 · `npc-dialogue` · `draft` · display `easy`

- 位置：CHR `$29B9` / file `$A9C9`
- 原文：＊「わたしは いそがしい<4F> / となりのやつに きいてくれ<4F><END>
- 中文：我很忙，去问旁边那个人吧。
- 显示判断：short fixed text with only understood layout controls

### chr-fc-29d3 · `npc-dialogue` · `draft` · display `hard`

- 位置：CHR `$29D3` / file `$A9E3`
- 原文：＊「え<4E>い もってけ！ どろ<EA>う！<END>
- 中文：算了，拿去吧！小偷！
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-29e4 · `npc-dialogue` · `draft` · display `hard`

- 位置：CHR `$29E4` / file `$A9F4`
- 原文：＊「はるか みなみに <42><4D><42><4E><40>の / まちが ありました<4F> / いまも あるのでしょうか<6C><6C><4F><END>
- 中文：遥远的南方曾有一座麦拉镇。它现在还存在吗？
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-2a0b · `npc-dialogue` · `draft` · display `easy`

- 位置：CHR `$2A0B` / file `$AA1B`
- 原文：＊「おとこなんて きらいよ<4F> / しっしっ<4F><END>
- 中文：我最讨厌男人了。走开，走开！
- 显示判断：short fixed text with only understood layout controls

### chr-fc-2a1f · `npc-dialogue` · `draft` · display `hard`

- 位置：CHR `$2A1F` / file `$AA2F`
- 原文：＊「うわさでは どこかに / ゆうしゃ <41><6B>のきていた / よろいが あるらしい<4F><END>
- 中文：听说某个地方藏着勇者洛特曾穿过的铠甲。
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-2a36 · `npc-dialogue` · `draft` · display `hard`

- 位置：CHR `$2A36` / file `$AA46`
- 原文：＊「うわさでは <41><4E><40>ひめは / どこかの どうくつに とじこめ / られたそうじゃ<4F> / <57>＊「もう たすけだされたのかのお<6C><END>
- 中文：听说萝拉公主被关在某处的洞窟里。她已经获救了吗？
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-2a66 · `npc-dialogue` · `draft` · display `hard`

- 位置：CHR `$2A66` / file `$AA76`
- 原文：＊「おれは みやおうだ<4F> / <6A><4D>こうを さがしている<4F><END>
- 中文：我是宫王，正在寻找米亚公。
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-2a80 · `npc-dialogue` · `draft` · display `hard`

- 位置：CHR `$2A80` / file `$AA90`
- 原文：＊「ふるい いいつたえでは いだいな / ぎんゆう しじん 力゙<40><4A>が / このまちを つくったそうじゃ<4F><END>
- 中文：古老传说中，伟大的吟游诗人加莱建造了这座城镇。
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-2aa6 · `npc-dialogue` · `draft` · display `hard`

- 位置：CHR `$2AA6` / file `$AAB6`
- 原文：＊「むかしがたりのまち / 力゙<40><4A>に ようこそ！<END>
- 中文：欢迎来到传说之城加莱！
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-2ab9 · `npc-dialogue` · `draft` · display `easy`

- 位置：CHR `$2AB9` / file `$AAC9`
- 原文：＊「わたしは きいた！ / なんと ひめを さらったまものが / ひがしのほうに とびさったとか！<END>
- 中文：我听说了！掳走公主的魔物竟然朝东方飞去了！
- 显示判断：short fixed text with only understood layout controls

### chr-fc-2ae3 · `npc-dialogue` · `draft` · display `easy`

- 位置：CHR `$2AE3` / file `$AAF3`
- 原文：＊「まいど！ / きょうは だいこんが やすいよ！<END>
- 中文：欢迎！今天萝卜很便宜！
- 显示判断：short fixed text with only understood layout controls

### chr-fc-2afa · `npc-dialogue` · `draft` · display `easy`

- 位置：CHR `$2AFA` / file `$AB0A`
- 原文：＊「そなたが しるしをもとめるなら / このまちの しんでんにすむ / ちょうろうを たずねるがよい<52><END>
- 中文：如果你想寻找印记，就去拜访住在这座城镇神殿里的长老。
- 显示判断：short fixed text with only understood layout controls

### chr-fc-2b23 · `npc-dialogue` · `draft` · display `hard`

- 位置：CHR `$2B23` / file `$AB33`
- 原文：＊「ふるい いいつたえでは / ゆうしゃ<41><6B>のつかった つるぎは / はがねをも くだいたそうじゃ<4F><END>
- 中文：古老传说中，勇者洛特使用的剑甚至能斩断钢铁。
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-2b44 · `npc-dialogue` · `draft` · display `hard`

- 位置：CHR `$2B44` / file `$AB54`
- 原文：＊「じょうさいのまち / <3F><43><6A><42>に ようこそ！<END>
- 中文：欢迎来到要塞都市梅尔基德！
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-2b56 · `npc-dialogue` · `draft` · display `easy`

- 位置：CHR `$2B56` / file `$AB66`
- 原文：＊「こんやの おかずは / なんに しようかしら<6C><6C><END>
- 中文：今晚做什么菜好呢……
- 显示判断：short fixed text with only understood layout controls

### chr-fc-2b6e · `npc-dialogue` · `draft` · display `hard`

- 位置：CHR `$2B6E` / file `$AB7E`
- 原文：＊「ねえ わたしの <EF><4E>と<EC>あと / あなたの <42><40><45>゙<46>くえすとを / かえっこしてよ<4F><END>
- 中文：喂，用我的猫和你的《勇者斗恶龙》交换吧。
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-2b93 · `npc-dialogue` · `draft` · display `hard`

- 位置：CHR `$2B93` / file `$ABA3`
- 原文：＊「え<4E>ん<4F> あてが まいごの / <6A><4D>こう だす<4F><END>
- 中文：嗯，我就是迷路的米亚公。
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-2bab · `npc-dialogue` · `draft` · display `hard`

- 位置：CHR `$2BAB` / file `$ABBB`
- 原文：＊「むかし うちのじいさんが よく / いってました<4F> / <57>＊「ともだちの ゆきのふは / じ<E8>んのみせの うらの きに / なにか うめたらしいと<6C><END>
- 中文：以前我爷爷常说，他的朋友雪之夫似乎在自己店铺后面的树下埋了什么东西。
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-2bec · `npc-dialogue` · `draft` · display `hard`

- 位置：CHR `$2BEC` / file `$ABFC`
- 原文：＊「うわさでは <41><6B>のよろいは / ひとから ひとへ<4F> / <57>＊「ゆきのふ というおとこの てに / わたったそうだ<4F><END>
- 中文：听说洛特铠甲在人们手中辗转流传，最后到了一个叫雪之夫的男人手里。
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-2c17 · `npc-dialogue` · `draft` · display `hard`

- 位置：CHR `$2C17` / file `$AC27`
- 原文：＊「わたしの いえは そのむかし / <42><4D><42><4E><40>のまちで みせやを / していたとか<4F> / <57>＊「みせは まちのひがしに あり / ゆきのふじいさんのとき / まちが まものたちに おそわれ<6C> / <57>＊「このまちまで にげてきました<4F><END>
- 中文：听说我家过去在麦拉镇经营商店。店铺位于城镇东边；雪之夫爷爷在世时，城镇遭到魔物袭击，于是逃到了这里。
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-2c70 · `shop-or-inn` · `draft` · display `easy`

- 位置：CHR `$2C70` / file `$AC80`
- 原文：＊「いらっしゃいませ！<END>
- 中文：欢迎光临！
- 显示判断：short fixed text with only understood layout controls

### chr-fc-2c7b · `npc-dialogue` · `draft` · display `hard`

- 位置：CHR `$2C7B` / file `$AC8B`
- 原文：＊「あなた だれ<60> / でてゆかないと ひとをよ<E8>わよ！<END>
- 中文：你是谁？再不出去，我就叫人了！
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-2c93 · `npc-dialogue` · `draft` · display `hard`

- 位置：CHR `$2C93` / file `$ACA3`
- 原文：＊「ちゅん で<4E>す<4F> / かのじょを まっています<4F><END>
- 中文：我是春。我在等她。
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-2ca9 · `npc-dialogue` · `draft` · display `easy`

- 位置：CHR `$2CA9` / file `$ACB9`
- 原文：＊「りゅうおうの うろこは / はがねのように かたいらしいぜ<4F><END>
- 中文：听说龙王的鳞片像钢铁一样坚硬。
- 显示判断：short fixed text with only understood layout controls

### chr-fc-2cc7 · `npc-dialogue` · `draft` · display `hard`

- 位置：CHR `$2CC7` / file `$ACD7`
- 原文：＊「ふるい いいつたえでは <41><6B>は / このしまの にしのはずれに / にじをかけたそうじゃ<4F> / <57>＊「そして まおうの へやの / かくされたる いりぐちより / やみにはいったときく<4F><END>
- 中文：古老传说中，洛特曾在这座岛的最西端架起彩虹；又从魔王房间隐藏的入口进入黑暗。
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-2d10 · `npc-dialogue` · `draft` · display `hard`

- 位置：CHR `$2D10` / file `$AD20`
- 原文：＊「うわさでは <40><47>゙<6B><4E><4D>のおしろに / たいようのいしが あるらしい<4F> / もう てにいれたか<60><END>
- 中文：听说拉达托姆城堡里有太阳石。你已经拿到了吗？
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-2d25 · `npc-dialogue` · `draft` · display `hard`

- 位置：CHR `$2D25` / file `$AD35`
- 原文：＊「り<4D><43><47>゙<4E><43>のまちに ようこそ！<FF>＊「おいで <EA>うや<4F> / <EB>ふ<EB>ふしてほしいなら / <05><00><45>゙<4E><43><42>よ<4F><END>
- 中文：欢迎来到里姆尔达尔镇！来吧，少爷。如果想休息，费用是5金币。
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-2d4e · `npc-dialogue` · `draft` · display `hard`

- 位置：CHR `$2D4E` / file `$AD5E`
- 原文：＊「いよお {PLAYER_NAME}！ / {PLAYER_NAME}じゃないか！ / ひさし<E8>りだなあ<4F><END>
- 中文：哟，{PLAYER_NAME}！这不是{PLAYER_NAME}吗！好久不见。
- 显示判断：contains a runtime-substituted name, object, enemy, or number

### chr-fc-2d68 · `npc-dialogue` · `draft` · display `hard`

- 位置：CHR `$2D68` / file `$AD78`
- 原文：＊「わたしは よしり<4E>ん<4F> / <4B><4A><40>のおふろから みなみに<04>つ / あるき しら<E9>るがよい<52><END>
- 中文：我是吉利恩。从麦拉的浴池向南走四步，调查那里吧。
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-2d8e · `npc-dialogue` · `draft` · display `hard`

- 位置：CHR `$2D8E` / file `$AD9E`
- 原文：＊「やがて このまちも / まものたちに<6C><6C> / ああ 力<68>さま<6C><6C><END>
- 中文：不久这座城镇也会被魔物……啊，神明啊……
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-2da6 · `npc-dialogue` · `draft` · display `easy`

- 位置：CHR `$2DA6` / file `$ADB6`
- 原文：＊「みなみに いっては いけません<4F> / もっともっと つよいまものが / すんでいる そうです<4F><END>
- 中文：不要去南方。听说那里住着强大得多的魔物。
- 显示判断：short fixed text with only understood layout controls

### chr-fc-2dd1 · `npc-dialogue` · `draft` · display `easy`

- 位置：CHR `$2DD1` / file `$ADE1`
- 原文：＊「りゅうおうの からだを / つらぬける つるぎが このよに / あるのだろうか<6C><6C><END>
- 中文：这个世界上真的有能够刺穿龙王身体的剑吗？
- 显示判断：short fixed text with only understood layout controls

### chr-fc-2df8 · `npc-dialogue` · `draft` · display `hard`

- 位置：CHR `$2DF8` / file `$AE08`
- 原文：＊「もう ちゅんさまったら / おそいわねえ<4F> <ED>ん<ED>ん<4F><END>
- 中文：春大人真是的，怎么这么晚……哼，哼。
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-2e12 · `npc-dialogue` · `draft` · display `hard`

- 位置：CHR `$2E12` / file `$AE22`
- 原文：＊「おおくのゆうしゃが / まちから とおくに たびにでて / そして しんだ<4F> / <57>＊「ゆうしゃ {PLAYER_NAME}よ / おまえを しなせたくないものだな<END>
- 中文：许多勇者从城镇出发远行，然后死去了。勇者{PLAYER_NAME}，我不希望你也死去。
- 显示判断：contains a runtime-substituted name, object, enemy, or number

### chr-fc-2e48 · `npc-dialogue` · `draft` · display `easy`

- 位置：CHR `$2E48` / file `$AE58`
- 原文：＊「ふえを てにいれたか<60><END>
- 中文：你拿到笛子了吗？
- 显示判断：short fixed text with only understood layout controls

### chr-fc-2e51 · `npc-dialogue` · `draft` · display `easy`

- 位置：CHR `$2E51` / file `$AE61`
- 原文：＊「みなみの しまに いきましたか<60><END>
- 中文：你去过南方的岛吗？
- 显示判断：short fixed text with only understood layout controls

### chr-fc-2e63 · `npc-dialogue` · `draft` · display `hard`

- 位置：CHR `$2E63` / file `$AE73`
- 原文：＊「りゅうおうの つめは てつを / ひきさき そして はく ほのおは / いわをも とかすという<4F> / <57>＊「{PLAYER_NAME}よ それでも ゆくか<60><END>
- 中文：据说龙王的爪能撕裂钢铁，吐出的火焰甚至能熔化岩石。{PLAYER_NAME}，即便如此你也要去吗？
- 显示判断：contains a runtime-substituted name, object, enemy, or number

### chr-fc-2ea0 · `npc-dialogue` · `draft` · display `easy`

- 位置：CHR `$2EA0` / file `$AEB0`
- 原文：＊「ここは よげんじょ<4F> / せいなる ほこらをみつけたか<60><END>
- 中文：这里是预言所。你找到神圣祠堂了吗？
- 显示判断：short fixed text with only understood layout controls

### chr-fc-2eb7 · `npc-dialogue` · `draft` · display `easy`

- 位置：CHR `$2EB7` / file `$AEC7`
- 原文：＊「どうくつに はいるときは / たいまつを もってゆけよ<4F><END>
- 中文：进入洞窟时要带上火把。
- 显示判断：short fixed text with only understood layout controls

### chr-fc-2ed0 · `npc-dialogue` · `draft` · display `hard`

- 位置：CHR `$2ED0` / file `$AEE0`
- 原文：＊「<3F><43><6A><42>のまちに ゆくがよい！<END>
- 中文：去梅尔基德吧！
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-2ee0 · `npc-dialogue` · `draft` · display `easy`

- 位置：CHR `$2EE0` / file `$AEF0`
- 原文：＊「なんと！ とても つよい / まものたちが いるとききましたが<END>
- 中文：什么！听说那里有非常强大的魔物……
- 显示判断：short fixed text with only understood layout controls

### chr-fc-2efb · `npc-dialogue` · `draft` · display `easy`

- 位置：CHR `$2EFB` / file `$AF0B`
- 原文：＊「おお！ あなたこそ / まことの ゆうしゃだ！<END>
- 中文：噢！你才是真正的勇者！
- 显示判断：short fixed text with only understood layout controls

### chr-fc-2f09 · `npc-dialogue` · `draft` · display `easy`

- 位置：CHR `$2F09` / file `$AF19`
- 原文：＊「あめと たいようが あわさる / ほこらじゃ<4F><END>
- 中文：这里是雨与太阳交汇的祠堂。
- 显示判断：short fixed text with only understood layout controls

### chr-fc-2f12 · `npc-dialogue` · `draft` · display `hard`

- 位置：CHR `$2F12` / file `$AF22`
- 原文：＊「よしり<4E>んが もっていたが / り<4D><43><47>゙<4E><43>にいくといって / むらをでて それっきりかえらぬ<4F><END>
- 中文：它原本由吉利恩保管，但他声称要去里姆尔达尔，离开村子后就再也没有回来。
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-2f3b · `npc-dialogue` · `draft` · display `hard`

- 位置：CHR `$2F3B` / file `$AF4B`
- 原文：＊「みなみには り<4D><43><47>゙<4E><43>という / まちが あるらしいです<4F><END>
- 中文：听说南方有一座叫里姆尔达尔的城镇。
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-2f4d · `npc-dialogue` · `draft` · display `easy`

- 位置：CHR `$2F4D` / file `$AF5D`
- 原文：＊「それが いい<4F> / だれも おまえを おくびょうとは / いわないだろう<4F><END>
- 中文：这样就好。没有人会说你是胆小鬼。
- 显示判断：short fixed text with only understood layout controls

### chr-fc-2f6e · `npc-dialogue` · `draft` · display `easy`

- 位置：CHR `$2F6E` / file `$AF7E`
- 原文：＊「みなみに ゆくがよい<52><END>
- 中文：往南方去吧。
- 显示判断：short fixed text with only understood layout controls

### chr-fc-2f78 · `npc-dialogue` · `draft` · display `hard`

- 位置：CHR `$2F78` / file `$AF88`
- 原文：＊「ああ <41><4E><40>ひめは / いったい どこに<6C><END>
- 中文：啊，萝拉公主究竟在哪里……
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-2f8a · `npc-dialogue` · `draft` · display `easy`

- 位置：CHR `$2F8A` / file `$AF9A`
- 原文：＊「ひめを たすけだしてくれて / ありがとうございます<4F><END>
- 中文：感谢你救出了公主。
- 显示判断：short fixed text with only understood layout controls

### chr-fc-2f96 · `npc-dialogue` · `draft` · display `hard`

- 位置：CHR `$2F96` / file `$AFA6`
- 原文：＊「ああ いとしの<41><4E><40>ひめ<6C> / わたしは {PLAYER_NAME}が にくい<4F><END>
- 中文：啊，我深爱的萝拉公主……我恨{PLAYER_NAME}。
- 显示判断：contains a runtime-substituted name, object, enemy, or number

### chr-fc-2fad · `npc-dialogue` · `draft` · display `hard`

- 位置：CHR `$2FAD` / file `$AFBD`
- 原文：＊「おうさまに つたえてくれ / <41><4E><40>ひめの そうさくたいは / ぜんめつしたと<6C> / <57>＊「わたしも もう だめだ<6C> / ぐ<E8>っ<6C><END>
- 中文：请转告国王，搜寻萝拉公主的队伍已经全军覆没。我也不行了……呃……
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-2fda · `npc-dialogue` · `draft` · display `easy`

- 位置：CHR `$2FDA` / file `$AFEA`
- 原文：＊「わたしに さわるのは だれだ<60> / もう なにも みえぬ<6C> / もう なにも きこえぬ<6C><END>
- 中文：是谁在碰我？我已经什么也看不见，什么也听不见了……
- 显示判断：short fixed text with only understood layout controls

### chr-fc-3002 · `npc-dialogue` · `reviewed` · display `hard`

- 位置：CHR `$3002` / file `$B012`
- 原文：＊「<41><4E><40>ひめのことを ごぞんじか<60><END>
- 中文：你知道公主的事情吗？
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-3011 · `npc-dialogue` · `draft` · display `hard`

- 位置：CHR `$3011` / file `$B021`
- 原文：＊「ひめさまが まものたちに / さらわれて はんとしになる<6C> / <57>＊「おうさまは なにも / おっしゃらないが / とても くるしんでいるはず<4F> / <57><FF>＊「{PLAYER_NAME}！ / どうか ひめを / たすけだして ください！<END>
- 中文：公主被魔物掳走已经半年。国王虽然什么也没说，内心一定十分痛苦。{PLAYER_NAME}，请救出公主！
- 显示判断：contains a runtime-substituted name, object, enemy, or number

### chr-fc-3058 · `npc-dialogue` · `draft` · display `hard`

- 位置：CHR `$3058` / file `$B068`
- 原文：＊「おお {PLAYER_NAME}！ / すばらしき ゆうしゃよ！<END>
- 中文：噢，{PLAYER_NAME}！了不起的勇者！
- 显示判断：contains a runtime-substituted name, object, enemy, or number

### chr-fc-3069 · `npc-dialogue` · `draft` · display `medium`

- 位置：CHR `$3069` / file `$B079`
- 原文：＊「わしは まっておった<4F> / そなたのような わかものが / あらわれることを<6C> / <57><FF>＊「ここには もう ようがないはず<4F> / いくがよい<52><END>
- 中文：我一直等待像你这样的年轻人出现。这里应该已经没有你的事了，去吧。
- 显示判断：fixed text, but long or split across several dialogue pages

### chr-fc-30a0 · `npc-dialogue` · `draft` · display `easy`

- 位置：CHR `$30A0` / file `$B0B0`
- 原文：＊「もし そなたが のろわれたなら / ここに くるがよい<52><END>
- 中文：如果你中了诅咒，就到这里来。
- 显示判断：short fixed text with only understood layout controls

### chr-fc-30b7 · `npc-dialogue` · `draft` · display `medium`

- 位置：CHR `$30B7` / file `$B0C7`
- 原文：＊「のろいをといて しんぜよう<4F> / <57><FF>＊「さあ ゆくがよい<52><END>
- 中文：我来为你解除诅咒。那么，去吧。
- 显示判断：fixed text, but long or split across several dialogue pages

### chr-fc-30d1 · `npc-dialogue` · `draft` · display `hard`

- 位置：CHR `$30D1` / file `$B0E1`
- 原文：＊「<41><6B>の ちをひく ゆうしゃよ！ / しかし その<E8>きでは / りゅうおうを たおせまいぞ！ / <57>＊「また くるがよい！<END>
- 中文：继承洛特血脉的勇者啊！但以你现在的武器还无法打倒龙王！以后再来吧！
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-30fc · `npc-dialogue` · `draft` · display `hard`

- 位置：CHR `$30FC` / file `$B10C`
- 原文：＊「ついに てにいれたな<4F> / ゆうしゃ {PLAYER_NAME}よ！<END>
- 中文：终于拿到了啊，勇者{PLAYER_NAME}！
- 显示判断：contains a runtime-substituted name, object, enemy, or number

### chr-fc-310b · `npc-dialogue` · `draft` · display `easy`

- 位置：CHR `$310B` / file `$B11B`
- 原文：＊「ゆびわなどして / おまえは はずかしいやつだなあ<4F><END>
- 中文：居然戴着戒指，你这家伙真不害臊啊。
- 显示判断：short fixed text with only understood layout controls

### chr-fc-3122 · `npc-dialogue` · `draft` · display `easy`

- 位置：CHR `$3122` / file `$B132`
- 原文：＊「ゆびわは せんしの たしなみだ<4F><END>
- 中文：戒指是战士应有的装束。
- 显示判断：short fixed text with only understood layout controls

### chr-fc-3134 · `npc-dialogue` · `draft` · display `hard`

- 位置：CHR `$3134` / file `$B144`
- 原文：＊「おお 力<68>よ！ / ふるい いいつたえの ゆうしゃ / {PLAYER_NAME}に ひかり あれ！<END>
- 中文：噢，神明啊！愿光明照耀传说中的勇者{PLAYER_NAME}！
- 显示判断：contains a runtime-substituted name, object, enemy, or number

### chr-fc-314d · `npc-dialogue` · `draft` · display `easy`

- 位置：CHR `$314D` / file `$B15D`
- 原文：<57>＊「ゆくがよい<52> / そして さがすがよい<52><END>
- 中文：去吧，然后寻找吧。
- 显示判断：short fixed text with only understood layout controls

### chr-fc-315a · `npc-dialogue` · `draft` · display `hard`

- 位置：CHR `$315A` / file `$B16A`
- 原文：<57>＊「<40><47>゙<6B><4E><4D>の おしろまで / きたに<07><00> にしに<04><00>の / そのばしょを！<END>
- 中文：从拉达托姆城堡向北70步、向西40步，就是那个地方！
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-3178 · `npc-dialogue` · `draft` · display `easy`

- 位置：CHR `$3178` / file `$B188`
- 原文：<57>＊「ふるい いいつたえ ですわ<4F><END>
- 中文：这是一个古老传说。
- 显示判断：short fixed text with only understood layout controls

### chr-fc-3181 · `npc-dialogue` · `draft` · display `medium`

- 位置：CHR `$3181` / file `$B191`
- 原文：＊「そなたが まことの ゆうしゃか / どうか ためさせてほしい<4F> / <57>＊「このちの どこかに まものたちを / よびよせる ぎんのたてごとが / あるときく<4F> / <57>＊「それを もちかえったとき / そなたを ゆうしゃと みとめ / あまぐものつえを さずけよう<4F><END>
- 中文：我想确认你是否是真正的勇者。听说这片土地的某处有能召来魔物的银竖琴。把它带回来，我便承认你是勇者，并赐予你雨云杖。
- 显示判断：fixed text, but long or split across several dialogue pages

### chr-fc-31d4 · `npc-dialogue` · `draft` · display `hard`

- 位置：CHR `$31D4` / file `$B1E4`
- 原文：＊「おお {PLAYER_NAME}！ / たてごとを もってきたな！ / <57><FF>＊「そなたが <41><6B>のちをひく / まことの ゆうしゃなら / しるしが あるはず / <57>＊「おろかものよ！ たちされい！<END>
- 中文：噢，{PLAYER_NAME}！你带来竖琴了！如果你真是继承洛特血脉的勇者，应该持有印记。愚蠢之人，退下！
- 显示判断：contains a runtime-substituted name, object, enemy, or number

### chr-fc-3216 · `npc-dialogue` · `draft` · display `hard`

- 位置：CHR `$3216` / file `$B226`
- 原文：＊「<41><6B>の ちをひくものよ<4F> / いまこそ あめと たいようが / あわさるときじゃ！ / <57>＊「そなたに にじのしずくを / あたえよう！<END>
- 中文：继承洛特血脉的人啊！如今正是雨与太阳交汇之时！我把彩虹水滴赐予你！
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-3245 · `story-or-ending` · `draft` · display `hard`

- 位置：CHR `$3245` / file `$B255`
- 原文：<41><4E><40>「ああ！ たすけだしてくださる / かたが ほんとうにいたなんて / まだ しんじられませんわ！ / <57><41><4E><40>「わたしは <40><43><69><01><06>せいの / むすめ <41><4E><40>です<4F> / <57><FF><41><4E><40>「そんな ひどい<6C><6C><4F> / <57><FF>あなたは ひめを だきかかえた<4F> / <57><FF><41><4E><40>「うれしゅうございます<4F> <EF>っ<END>
- 中文：萝拉：竟然真的有人来救我，我仍不敢相信！我是国王的女儿萝拉。怎么能这样……你把公主抱了起来。萝拉：我好高兴……
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-32ac · `story-or-ending` · `draft` · display `hard`

- 位置：CHR `$32AC` / file `$B2BC`
- 原文：＊「おお {PLAYER_NAME}！ よくぞ / ひめを たすけだしてくれた<4F> / こころから れいをいうぞ！ / <57>＊「さあ <41><4E><40><4F> / わたしのとなりへ<4F> / <57><41><4E><40>「まってください<4F> <41><4E><40>は / {PLAYER_NAME}さまに おくりものを / しとうございます<4F> / <57><41><4E><40>「{PLAYER_NAME}さまを あいする / わたしの こころ<4F> どうか / うけとってくださいませ<4F> / <57><FF><41><4E><40>「そして <41><4E><40>にも / あなたさまから / なにか ひとつ<6C> / <57><41><4E><40>「<FD>を <41><4E><40>に / くださいませね<4F> / <57><FF><41><4E><40>「ああ！ たとえ はなれて / いても <41><4E><40>は いつも / あなたと ともに あります<4F><END>
- 中文：噢，{PLAYER_NAME}！感谢你救出了公主，我由衷向你致谢！来，萝拉，到我身边。萝拉：请等一下。我想送给{PLAYER_NAME}大人一件礼物。请收下我爱慕您的心意。也请您送给我一样东西，把<FD>送给萝拉吧。啊！即使相隔两地，萝拉也永远与你同在。
- 显示判断：contains a runtime-substituted name, object, enemy, or number

### chr-fc-3384 · `npc-dialogue` · `draft` · display `hard`

- 位置：CHR `$3384` / file `$B394`
- 原文：<41><4E><40>「{PLAYER_NAME}さまは <41><4E><40>のこと / を おもってくださいますか<60><END>
- 中文：萝拉：{PLAYER_NAME}大人会想念萝拉吗？
- 显示判断：contains a runtime-substituted name, object, enemy, or number

### chr-fc-3397 · `npc-dialogue` · `reviewed` · display `hard`

- 位置：CHR `$3397` / file `$B3A7`
- 原文：＊「たびのしたくが できたなら / また わしに あいにくるがよい / まっておるぞ {PLAYER_NAME}よ！<END>
- 中文：准备好旅行后，再来见我。我会等着你，勇者！
- 显示判断：contains a runtime-substituted name, object, enemy, or number

### chr-fc-33c1 · `dynamic-template` · `draft` · display `hard`

- 位置：CHR `$33C1` / file `$B3D1`
- 原文：＊「おお {PLAYER_NAME}！ / よくぞ <E8>じで もどってきた<4F> / わしは とても うれしいぞ<4F> / <57><FF>＊「そなたが つぎの<44>べ<43>になるには / あと <F3><00><00><49><F9><4A><46><6B>の / けいけんが ひつようじゃ<4F> / <57><FF>＊「そなたに ふっかつの じゅもんを / おしえよう！ / <57><FF>＊「これを かきとめておくのだぞ<4F> / <57><FF>＊「では また あおう！ / ゆうしゃ {PLAYER_NAME}よ！<END>
- 中文：噢，{PLAYER_NAME}！你平安回来了，我非常高兴。升到下一级还需要<F3>点经验。我来告诉你复活咒文，请把它记录下来。那么，下次再见，勇者{PLAYER_NAME}！
- 显示判断：contains a runtime-substituted name, object, enemy, or number

### chr-fc-344a · `npc-dialogue` · `draft` · display `hard`

- 位置：CHR `$344A` / file `$B45A`
- 原文：<41><4E><40>「わたしを おしろまで / つれてかえってくれますね<60><END>
- 中文：萝拉：你会把我带回城堡吧？
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-3460 · `npc-dialogue` · `draft` · display `easy`

- 位置：CHR `$3460` / file `$B470`
- 原文：＊「さあ たからのはこを / とるがよい<52><END>
- 中文：来，去拿宝箱吧。
- 显示判断：short fixed text with only understood layout controls

### chr-fc-3470 · `story-or-ending` · `draft` · display `hard`

- 位置：CHR `$3470` / file `$B480`
- 原文：＊「よくきた {PLAYER_NAME}よ<4F> / わしが おうのなかの おう / りゅうおうだ<4F> / <57><FF>＊「もし わしの みかたになれば / せかいの はん<E8>んを / {PLAYER_NAME}に やろう<4F> / <57>＊「どうじゃ<60> / わしの みかたに なるか<60><END>
- 中文：欢迎你，{PLAYER_NAME}。我就是王中之王——龙王。如果你愿意成为我的同伴，我就把世界的一半送给你。怎么样？愿意成为我的同伴吗？
- 显示判断：contains a runtime-substituted name, object, enemy, or number

### chr-fc-34cb · `npc-dialogue` · `draft` · display `easy`

- 位置：CHR `$34CB` / file `$B4DB`
- 原文：＊「おろかものめ！ / おもいしるがよい！<END>
- 中文：愚蠢的家伙！让你尝尝厉害！
- 显示判断：short fixed text with only understood layout controls

### chr-fc-34de · `story-or-ending` · `draft` · display `hard`

- 位置：CHR `$34DE` / file `$B4EE`
- 原文：＊「では せかいの はん<E8>ん / やみのせかいを あたえよう！ / そして<6C> / <57><FF>＊「おまえの たびは おわった<4F> / さあ ゆっくり やすむがよい！ / わあっはっはっはっ<END>
- 中文：那么，就把世界的一半——黑暗世界赐给你！然后……你的旅程结束了。好好休息吧！哇哈哈哈哈！
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-352a · `chest-or-system` · `draft` · display `easy`

- 位置：CHR `$352A` / file `$B53A`
- 原文：<57>しかし なにかをすてないと / これいじょう もてない<4F> / なにか すてますか<60><END>
- 中文：但不丢掉一些东西，就再也拿不下了。要丢掉什么吗？
- 显示判断：short fixed text with only understood layout controls

### chr-fc-3548 · `chest-or-system` · `draft` · display `hard`

- 位置：CHR `$3548` / file `$B558`
- 原文：<FD>を あきらめた<4F><END>
- 中文：放弃了<FD>。
- 显示判断：contains a runtime-substituted name, object, enemy, or number

### chr-fc-3552 · `chest-or-system` · `draft` · display `easy`

- 位置：CHR `$3552` / file `$B562`
- 原文：なにを すてますか<60><END>
- 中文：要丢掉什么？
- 显示判断：short fixed text with only understood layout controls

### chr-fc-3564 · `chest-or-system` · `draft` · display `easy`

- 位置：CHR `$3564` / file `$B574`
- 原文：それを すてるなんて とんでもない！<END>
- 中文：怎么能把那个扔掉！
- 显示判断：short fixed text with only understood layout controls

### chr-fc-3577 · `chest-or-system` · `draft` · display `hard`

- 位置：CHR `$3577` / file `$B587`
- 原文：{PLAYER_NAME}は じ<E8>んのあしもとを / しら<E9>た<4F> / <57><FF>しかし なにも みつからなかった<4F><END>
- 中文：{PLAYER_NAME}调查了脚边，但什么也没找到。
- 显示判断：contains a runtime-substituted name, object, enemy, or number

### chr-fc-359c · `chest-or-system` · `draft` · display `easy`

- 位置：CHR `$359C` / file `$B5AC`
- 原文：たからのはこが ある！<END>
- 中文：有一个宝箱！
- 显示判断：short fixed text with only understood layout controls

### chr-fc-35a8 · `chest-or-system` · `draft` · display `hard`

- 位置：CHR `$35A8` / file `$B5B8`
- 原文：なんと <FD>を みつけた<4F><END>
- 中文：竟然发现了<FD>！
- 显示判断：contains a runtime-substituted name, object, enemy, or number

### chr-fc-35b2 · `system-or-unknown` · `draft` · display `easy`

- 位置：CHR `$35B2` / file `$B5C2`
- 原文：ぎょくざの うしろから / かぜを かんじる<4F><END>
- 中文：从王座后方感觉到一阵风。
- 显示判断：short fixed text with only understood layout controls

### chr-fc-35c8 · `system-or-unknown` · `reviewed` · display `easy`

- 位置：CHR `$35C8` / file `$B5D8`
- 原文：ここでは なにも とれない<4F><END>
- 中文：这里什么也拿不到。
- 显示判断：short fixed text with only understood layout controls

### chr-fc-35e7 · `chest-or-system` · `reviewed` · display `hard`

- 位置：CHR `$35E7` / file `$B5F7`
- 原文：{PLAYER_NAME}は <FD>を / みつけた<4F><END>
- 中文：发现了物品。
- 显示判断：contains a runtime-substituted name, object, enemy, or number

### chr-fc-35f0 · `chest-or-system` · `draft` · display `hard`

- 位置：CHR `$35F0` / file `$B600`
- 原文：なかは からっ<EF>だった<4F><END>
- 中文：里面是空的。
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-366f · `battle` · `draft` · display `hard`

- 位置：CHR `$366F` / file `$B67F`
- 原文：<FD>が あらわれた！<END>
- 中文：<FD>出现了！
- 显示判断：contains a runtime-substituted name, object, enemy, or number

### chr-fc-3676 · `battle` · `draft` · display `hard`

- 位置：CHR `$3676` / file `$B686`
- 原文： <FD>は にげだした！<END>
- 中文：<FD>逃走了！
- 显示判断：contains a runtime-substituted name, object, enemy, or number

### chr-fc-3681 · `battle` · `draft` · display `hard`

- 位置：CHR `$3681` / file `$B691`
- 原文：{PLAYER_NAME}が みがまえるより はやく / <FD>は おそいかかってきた / <FB><FF>{PLAYER_NAME}の こうげき！<END>
- 中文：在{PLAYER_NAME}摆好架势前，<FD>就袭击了过来！{PLAYER_NAME}的攻击！
- 显示判断：contains a runtime-substituted name, object, enemy, or number

### chr-fc-36e2 · `battle` · `draft` · display `hard`

- 位置：CHR `$36E2` / file `$B6F2`
- 原文：それは たたかいに つかえない！ / <FB><FF>しかし じゅもんは / ふうじこまれている！ / <FB><FF>しかし じゅもんは きかなかった！ / <FB><FF><FD>を ねむらせた！ / <FB><FF><FD>の じゅもんを / ふうじこめた！ / <FB><FF><FD>を たおした！<END>
- 中文：那个不能用于战斗！但是咒文被封住了！但是咒文没有生效！使<FD>睡着了！封住了<FD>的咒文！打倒了<FD>！
- 显示判断：contains a runtime-substituted name, object, enemy, or number

### chr-fc-375b · `battle` · `draft` · display `hard`

- 位置：CHR `$375B` / file `$B76B`
- 原文：<57>{PLAYER_NAME}は <44>べ<43>が あがった！ / <57><FF>じゅもんを <01>つ お<EA>えた！<END>
- 中文：{PLAYER_NAME}的等级提升了！学会了一个咒文！
- 显示判断：contains a runtime-substituted name, object, enemy, or number

### chr-fc-3776 · `battle` · `draft` · display `hard`

- 位置：CHR `$3776` / file `$B786`
- 原文：<45>゙<4E><44><4D>は しずかに めをとじる<6C> / ねむってしまった！ / <FB><FF><FD>は うれしそうだ！ / <FB><FF>{PLAYER_NAME}は にげだした！ / <FB><FF>しかし まわりこまれてしまった！ / <FB><FF>{PLAYER_NAME}は やくそうを つかった！<END>
- 中文：巨像静静闭上眼睛，睡着了！<FD>看起来很高兴！{PLAYER_NAME}逃跑了！但被挡住了去路！{PLAYER_NAME}使用了药草！
- 显示判断：contains a runtime-substituted name, object, enemy, or number

### chr-fc-37cb · `battle` · `draft` · display `hard`

- 位置：CHR `$37CB` / file `$B7DB`
- 原文： <FD>は ねむっている<6C><END>
- 中文：<FD>正在睡觉……
- 显示判断：contains a runtime-substituted name, object, enemy, or number

### chr-fc-37d7 · `battle` · `draft` · display `hard`

- 位置：CHR `$37D7` / file `$B7E7`
- 原文： <FD>の こうげき！<END>
- 中文：<FD>的攻击！
- 显示判断：contains a runtime-substituted name, object, enemy, or number

### chr-fc-3827 · `battle` · `draft` · display `hard`

- 位置：CHR `$3827` / file `$B837`
- 原文： {PLAYER_NAME}の じゅもんは /  ふうじこまれた！ / <FB><FF> <FD>は ほのおをはいた！<END>
- 中文：{PLAYER_NAME}的咒文被封住了！<FD>喷出了火焰！
- 显示判断：contains a runtime-substituted name, object, enemy, or number

### chr-fc-3847 · `chest-or-system` · `reviewed` · display `hard`

- 位置：CHR `$3847` / file `$B857`
- 原文：＊「たからのはこを ぜん<E8>とったなら / そのなかに かぎが はいっていた / はずだ<4F> / <57>＊「かぎは <01>どつかうと なくなって / しまうが そのかぎで とびらを / あけたとき<6C><6C> / <57>＊「おまえのたびが はじまるだろう<4F><END>
- 中文：拿完所有宝箱后，里面应该有一把钥匙。钥匙使用一次就会消失；用它打开门，你的旅程便会开始。
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-38a7 · `shop-or-inn` · `reviewed` · display `hard`

- 位置：CHR `$38A7` / file `$B8B7`
- 原文：＊「このおしろをでると となりに / まちが ある<4F> / <57>＊「そこで まず <E8>きと <EA>うぐを / かいそろえることだ<4F> / <57>＊「たたかいで きずついたときは / まちにもどり やどやにとまると / きずが かいふくするだろう<4F><END>
- 中文：离开这座城堡后，旁边有一座城镇。先在那里备齐武器和防具。战斗中受伤时，回城镇住进旅店，伤势就会恢复。
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-3908 · `battle` · `reviewed` · display `hard`

- 位置：CHR `$3908` / file `$B918`
- 原文：＊「おお {PLAYER_NAME}！ / ゆうしゃ<41><6B>の ちをひくものよ！ / そなたのくるのをまっておったぞ<4F> / <57>＊「その むかし ゆうしゃ<41><6B>が / 力<68>から ひかりのたまをさずかり / まものたちをふうじこめたという<4F> / <57>＊「しかし いずこともなくあらわれた / あくまのけしん りゅうおうが / そのたまを やみにとざしたのじゃ / <57>＊「このちに ふたたびへいわをっ！ / <57>＊「ゆうしゃ {PLAYER_NAME}よ！ / りゅうおうをたおし そのてから / ひかりのたまをとりもどしてくれ！ / <57>＊「わしからの おくりものじゃ！ / そなたのよこにある / たからのはこを とるがよい！ / <57>＊「そして このへやにいる / へいしにきけば たびのちしきを / おしえてくれよう<4F> / <57>＊「では また あおう！ / ゆうしゃ {PLAYER_NAME}よ！<END>
- 中文：勇者啊！继承勇者洛特血脉之人，我一直在等你。很久以前，勇者洛特从神明那里获得光之玉，并用它封印了魔物。然而，魔王的化身龙王突然出现，将光之玉封入黑暗。请让和平再次降临此地！打倒龙王，从他手中夺回光之玉！这是我送给你的礼物，去拿你身旁的宝箱吧。向房间里的士兵询问，他们会告诉你旅行的知识。那么，后会有期，勇者！
- 显示判断：contains a runtime-substituted name, object, enemy, or number

### chr-fc-3a1d · `story-or-ending` · `draft` · display `hard`

- 位置：CHR `$3A1D` / file `$BA2D`
- 原文：<57>せきばんには こう かかれている<4F> / <57>＊「わたしのなは <41><6B><4F> / わたしの ちをひきしものよ<4F> / <57>＊「<40><47>゙<6B><4E><4D>からみえる まのしまに / わたるには <03>つのものが / ひつようだった<4F> / <57>＊「わたしは それらを あつめ / まのしまに わたり / まおうを たおした<4F> / <57>＊「そして いま その<03>つの / しん<EC>なるものを <03>にんの / けんじゃに たくす<4F> / <57>＊「かれらの しそんが それらを / まもってゆくだろう<4F> / <57>＊「ふたたび まのしまに / あくが よみがえったとき / <57>＊「それらを あつめ / たたかうがよい<52><END>
- 中文：石板上写着：我的名字是洛特。继承我血脉的人啊，要渡过从拉达托姆望见的魔之岛，需要三件物品。我集齐它们，渡海打倒了魔王。如今我把三件圣物托付给三位贤者，他们的后代会继续守护。当邪恶再次在魔之岛复苏时，集齐它们并战斗吧。
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-3afc · `battle` · `draft` · display `hard`

- 位置：CHR `$3AFC` / file `$BB0C`
- 原文：かいしんの いちげき！！ / <FB><FF><41><4E><40>ひめの こえが きこえる<4F> / <57><41><4E><40>「あなたの<44>べ<43>は もう / さいこうで ございます<4F> / <57><FF>{PLAYER_NAME}は ねむってしまった！ / <FB><FF>{PLAYER_NAME}は ねむっている<6C><6C> / <FB><FF>{PLAYER_NAME}は めをさました！ / <FB><FF> <FD>は きずが /  かいふくした！ / <FB><FF><FD>は すばやく / みをかわした！ / <FB><FF>ここには とびらがない！<END>
- 中文：会心一击！！听见萝拉公主的声音。萝拉：您的等级已经达到最高。{PLAYER_NAME}睡着了！{PLAYER_NAME}正在睡觉……{PLAYER_NAME}醒来了！<FD>的伤势恢复了！<FD>迅速闪开了！这里没有门！
- 显示判断：contains a runtime-substituted name, object, enemy, or number

### chr-fc-3b88 · `system-or-unknown` · `draft` · display `hard`

- 位置：CHR `$3B88` / file `$BB98`
- 原文：力<6A>゙を もっていない！<END>
- 中文：没有钥匙！
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-3b95 · `system-or-unknown` · `draft` · display `hard`

- 位置：CHR `$3B95` / file `$BBA5`
- 原文：＊「おお {PLAYER_NAME}！ / しんでしまうとは なにごとだ！ / <57>＊「しかたのない やつだな<4F> / おまえに もう いちど / きかいを あたえよう！ / <57>＊「たたかいで <6A><69>゙ついたときは / まちにもどり やどやに とまって / <6A><69>゙をかいふくさせるのだぞ<4F> / <57>＊「ふたたび このようなことが / おこらぬことを / わしは いのっている！ / <57><FF>ちからが <F3><00><00><49><F9><4A><46><6B>あがった！<END>
- 中文：噢，{PLAYER_NAME}！竟然死掉了，成何体统！真拿你没办法，再给你一次机会。战斗受伤后要回城住旅店恢复。希望这种事不要再次发生。力量提升了<F3>！
- 显示判断：contains a runtime-substituted name, object, enemy, or number

### chr-fc-3c7b · `dynamic-template` · `draft` · display `hard`

- 位置：CHR `$3C7B` / file `$BC8B`
- 原文：＊「おまえが つぎの<44>べ<43>になるには / あと <F3><00><00><49><F9><4A><46><6B>の / けいけんが ひつようじゃ<4F> / <57><FF>＊「では ゆけ！ {PLAYER_NAME}よ！<END>
- 中文：升到下一级还需要<F3>点经验。那么，出发吧，{PLAYER_NAME}！
- 显示判断：contains a runtime-substituted name, object, enemy, or number

### chr-fc-3cad · `system-or-unknown` · `draft` · display `hard`

- 位置：CHR `$3CAD` / file `$BCBD`
- 原文：＊「おお {PLAYER_NAME}よ！ / しんでしまうとは なにごとだ！ / <57>＊「しかも のろわれているではないか / のろわれしものよ<50>でてゆけっ！ / <FB><FF>＊「<6C><6C><6C><6C><6C><END>
- 中文：噢，{PLAYER_NAME}！竟然死掉了，成何体统！而且还中了诅咒。被诅咒的人啊，滚出去！
- 显示判断：contains a runtime-substituted name, object, enemy, or number

### chr-fc-3cf1 · `npc-dialogue` · `draft` · display `easy`

- 位置：CHR `$3CF1` / file `$BD01`
- 原文：＊「ほんとうだな<60><END>
- 中文：你说的是真的吗？
- 显示判断：short fixed text with only understood layout controls

### chr-fc-3cfa · `story-or-ending` · `draft` · display `hard`

- 位置：CHR `$3CFA` / file `$BD0A`
- 原文：＊「おお {PLAYER_NAME}！ / よくぞ もどってきてくれた！ / わしは とても うれしいぞ<4F> / <57><FF>＊「<44>べ<43>が あがったときは / わしに あいにくるようにな<4F> / <57><FF>りゅうおうが しょうたいを / あらわした！！<END>
- 中文：噢，{PLAYER_NAME}！你终于回来了，我非常高兴。等级提升时要来见我。龙王显出了真身！！
- 显示判断：contains a runtime-substituted name, object, enemy, or number

### chr-fc-3d54 · `story-or-ending` · `draft` · display `medium`

- 位置：CHR `$3D54` / file `$BD64`
- 原文：<57>そして ひかりのたまを / りゅうおうのてから とりもどした！ / <57>あなたが ひかりのたまを かざすと / まばゆいばかりの ひかりが / あふれだす<6C><6C> / <57>このくにに へいわが もどったのだ<4F><END>
- 中文：终于从龙王手中夺回了光之玉！当你举起光之玉，耀眼的光芒涌出，这个国家恢复了和平。
- 显示判断：fixed text, but long or split across several dialogue pages

### chr-fc-3dae · `story-or-ending` · `draft` · display `hard`

- 位置：CHR `$3DAE` / file `$BDBE`
- 原文：＊「おお！ {PLAYER_NAME}！ / す<E9>ては ふるい いいつたえの / ままで あった！ / <57>＊「すなわち そなたこそは / ゆうしゃ<41><6B>の ちをひくもの！ / <57>＊「そなたこそ このせかいを / おさめるに ふさわしい おかた / なのじゃ！ / <57>＊「わしに かわって / このくにを おさめてくれるな<60> / <57>しかし {PLAYER_NAME}は いいました<4F> / <57>＊「いいえ<4F> わたしの おさめる / くにが あるなら それは / わたしじしんで さがしたいのです<END>
- 中文：噢，{PLAYER_NAME}！一切都和古老传说完全相同！你正是继承勇者洛特血脉的人，也是最适合统治这个世界的人。愿意代替我治理这个国家吗？然而{PLAYER_NAME}回答：不。如果有一个由我统治的国家，我希望亲自去寻找它。
- 显示判断：contains a runtime-substituted name, object, enemy, or number

### chr-fc-3e4d · `npc-dialogue` · `draft` · display `hard`

- 位置：CHR `$3E4D` / file `$BE5D`
- 原文：<57><41><4E><40>「まってくださいませ！<END>
- 中文：萝拉：请等一下！
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-3e57 · `story-or-ending` · `draft` · display `hard`

- 位置：CHR `$3E57` / file `$BE67`
- 原文：<41><4E><40>「その あなたの たびに / <41><4E><40>も / おともしとうございます<4F> / <57><FF><41><4E><40>「この<41><4E><40>も つれてって / くださいますわね<60><END>
- 中文：萝拉：我也想陪伴你继续旅行。你会带上萝拉一起走吧？
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-3e82 · `story-or-ending` · `draft` · display `hard`

- 位置：CHR `$3E82` / file `$BE92`
- 原文：＊「ゆうしゃ<41><6B> ばんざい！ / ゆうしゃ{PLAYER_NAME} ばんざ<4E>い！<END>
- 中文：勇者洛特万岁！勇者{PLAYER_NAME}万岁！
- 显示判断：contains a runtime-substituted name, object, enemy, or number

### chr-fc-3e97 · `story-or-ending` · `draft` · display `easy`

- 位置：CHR `$3E97` / file `$BEA7`
- 原文：＊「あなたさまの おかげで / へいわが もどりました！ / <57>＊「おうさまも きっと / およろこびでしょう！<END>
- 中文：多亏了您，和平终于恢复了！国王也一定会非常高兴！
- 显示判断：short fixed text with only understood layout controls

### chr-fc-3ec2 · `story-or-ending` · `draft` · display `easy`

- 位置：CHR `$3EC2` / file `$BED2`
- 原文：＊「さあ はやく おうさまのもとへ！<END>
- 中文：快去国王身边吧！
- 显示判断：short fixed text with only understood layout controls

### chr-fc-4193 · `system-or-unknown` · `pending` · display `hard`

- 位置：CHR `$4193` / file `$C1A3`
- 原文：ぬ<4E><40>ほのおのつるぎてつのおの<00>れれを<3C>ををあったぬぬ<END>
- 中文：（待翻译/待确认）
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-42f0 · `item-spell-action` · `pending` · display `hard`

- 位置：CHR `$42F0` / file `$C300`
- 原文：ききてきき<40><47>゙<6B><4E><4D><41><6B>のよろい力゙<40><4A>のはかなれ<03>お<06><06>はずます<4F>ら<08><40><5C>「<02><04>そ<03>かなを<6C> / そ<3C><44><44><44><44>ひ<04><08>きょら<60>ございます<4F><06><06>はずます<4F>ございます<4F><08>らございます<4F><40>り<49><4E>る<52><3C>かいだんください<43><4E><40>うそそららぬぬ<EC>るのM<6A><3F><40>のつばさのなれあった<67>ばあるらしいはずます<4F>ございます<4F><08>き<3C><42><02><02><3C><3F>かいだんぞあめと たいようが あわさるあめと たいようが あわさるぞかいだん<3F>ぬぬ<EC>るの「たいまつひくださいくださいください<FF><FF>くださいたすけだしてあめと たいようが あわさるきます<4F>ぬろ:まぬてうおかかえ<3C>  ぶき:゙<F0><08><08>ききっま<48><46>らららしかし<F0><F0><40><47>゙<6B><4E><4D>ら<00><00><00><F0><08><08>き<60><3F>かいだんくださいどうのつるぎたり！だ<00><50>ございます<4F>まち<44>っぬぬだだだだあった<3C>にか<00>きどれをまちくさりかたびらくさりかたびらっき<01>ば<END>
- 中文：（待翻译/待确认）
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-4b68 · `system-or-unknown` · `pending` · display `hard`

- 位置：CHR `$4B68` / file `$CB78`
- 原文：どこかにそなたび<FF><EF>まことの ございます<4F><00><END>
- 中文：（待翻译/待确认）
- 显示判断：contains unresolved source bytes or non-layout controls

### chr-fc-570b · `system-or-unknown` · `pending` · display `hard`

- 位置：CHR `$570B` / file `$D71B`
- 原文：<47>ねにせて たきけえこすきか そきえおき<END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-5720 · `system-or-unknown` · `pending` · display `hard`

- 位置：CHR `$5720` / file `$D730`
- 原文：べ<6A>゙<40><4B>ねつせ つまき とせたさか <00><END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-5731 · `system-or-unknown` · `pending` · display `hard`

- 位置：CHR `$5731` / file `$D741`
- 原文：でねほてつ にせて かきおこかきか つせ ちつえたつ<END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-574c · `system-or-unknown` · `pending` · display `hard`

- 位置：CHR `$574C` / file `$D75C`
- 原文：ほのせす え すきと みせてたすきに <03><END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-5761 · `system-or-unknown` · `pending` · display `hard`

- 位置：CHR `$5761` / file `$D771`
- 原文：<6B>へ<41><69>のしえに けせか ほき えさとえにち<END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-5775 · `system-or-unknown` · `pending` · display `hard`

- 位置：CHR `$5775` / file `$D785`
- 原文：ゆうしゃのとこつま にせて <00><END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-5788 · `dynamic-template` · `pending` · display `hard`

- 位置：CHR `$5788` / file `$D798`
- 原文：ひつようは<F7>ぬのろいのべ<43><6B><FD>べ<6A>゙<40><4B>ねかたえけせす めてきちつ<END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-579d · `system-or-unknown` · `pending` · display `hard`

- 位置：CHR `$579D` / file `$D7AD`
- 原文：<EC>ねちつえくく<END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-57a5 · `dynamic-template` · `pending` · display `hard`

- 位置：CHR `$57A5` / file `$D7B5`
- 原文：あめと たいようが あわさるは<F7>ぬ<FF><FD><43><4E><40>ねちおきすえたこせ とたこつつきす ほに<END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-57c1 · `system-or-unknown` · `pending` · display `hard`

- 位置：CHR `$57C1` / file `$D7D1`
- 原文：<EB>ねにてみこ ませたここ<END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-57ce · `dynamic-template` · `pending` · display `hard`

- 位置：CHR `$57CE` / file `$D7DE`
- 原文：あめと たいようが あわさるは<F7>ぬ<05><FD>り<44><68><6B>ねおまえたえおつきた かきちこけすきか ほに<END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-57ec · `system-or-unknown` · `pending` · display `hard`

- 位置：CHR `$57EC` / file `$D7FC`
- 原文：<E9>ねえむこたえ つせたこにえしえ<END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-57fd · `dynamic-template` · `pending` · display `hard`

- 位置：CHR `$57FD` / file `$D80D`
- 原文：あめと たいようが あわさるは<F7>ぬあ<FD><6B>へ<41><69>ねしてちこお おせしそせちきか ほに<END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-5817 · `system-or-unknown` · `pending` · display `hard`

- 位置：CHR `$5817` / file `$D827`
- 原文：<E8>ねむせこおまこ ちてけこにえしえ<END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-5829 · `dynamic-template` · `pending` · display `hard`

- 位置：CHR `$5829` / file `$D839`
- 原文：あめと たいようが あわさるは<F7>ぬか<FD>むねそたせけたえしきか ほに<END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-583e · `system-or-unknown` · `pending` · display `hard`

- 位置：CHR `$583E` / file `$D84E`
- 原文：<41><6B>のしるしねむせこおまこ すえむえしてたえ<END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-5850 · `system-or-unknown` · `pending` · display `hard`

- 位置：CHR `$5850` / file `$D860`
- 原文：あのむせみこ にせちまこかえ<END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-585f · `system-or-unknown` · `pending` · display `hard`

- 位置：CHR `$585F` / file `$D86F`
- 原文：<67>のつえむきすせたこ にえしえしせたこ<END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-588d · `system-or-unknown` · `pending` · display `hard`

- 位置：CHR `$588D` / file `$D89D`
- 原文：<E9>ねつえむえちまこ にえちてすせ<END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-589e · `dynamic-template` · `pending` · display `hard`

- 位置：CHR `$589E` / file `$D8AE`
- 原文：ぎは<F7><08>あ<FD><43><4E><40>ねちおきすえたこせ えちちこちつきか ほに<END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-58bb · `system-or-unknown` · `pending` · display `hard`

- 位置：CHR `$58BB` / file `$D8CB`
- 原文：<E8>ねまこたせちまこ しこにえせむえ<END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-58cd · `dynamic-template` · `pending` · display `hard`

- 位置：CHR `$58CD` / file `$D8DD`
- 原文：あめと たいようが あわさるは<F7>ぬか<FD><4A>ねえちちこちつきか ほに<END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-58e1 · `system-or-unknown` · `pending` · display `hard`

- 位置：CHR `$58E1` / file `$D8F1`
- 原文：どうかねたこむえ ちてやてむこ<END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-58ef · `system-or-unknown` · `pending` · display `hard`

- 位置：CHR `$58EF` / file `$D8FF`
- 原文：まのつえかえちまこ くてむてやえとえ<END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-5902 · `dynamic-template` · `pending` · display `hard`

- 位置：CHR `$5902` / file `$D912`
- 原文：ひつようは<F7><08><50><F7>き<00><FD>ほねつこつさき かきちこけすきか ほに<END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-591f · `system-or-unknown` · `pending` · display `hard`

- 位置：CHR `$591F` / file `$D92F`
- 原文：べ<6A>゙<40><4B>ねむえやてせ きすせしせつせ<END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-592f · `system-or-unknown` · `pending` · display `hard`

- 位置：CHR `$592F` / file `$D93F`
- 原文：<05>のしえすてえさ こささてちつたえつきか ほに<END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-5947 · `system-or-unknown` · `pending` · display `hard`

- 位置：CHR `$5947` / file `$D957`
- 原文：<6A>のつえむえにてむこ かせこ<END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-5976 · `system-or-unknown` · `pending` · display `hard`

- 位置：CHR `$5976` / file `$D986`
- 原文：びねむえやてまこむせ つせたこちまこしえ<END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-598b · `dynamic-template` · `pending` · display `hard`

- 位置：CHR `$598B` / file `$D99B`
- 原文：あめと たいようが あわさるは<F7>ぬ<05><FD><44>べ<43>ねかこたきおつきか ほに<END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-599f · `system-or-unknown` · `pending` · display `hard`

- 位置：CHR `$599F` / file `$D9AF`
- 原文：<E8>ねむせこおまこ すえむえしてたえ<END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-59b1 · `dynamic-template` · `pending` · display `hard`

- 位置：CHR `$59B1` / file `$D9C1`
- 原文：あめと たいようが あわさるは<F7>ぬあ<FD><44>べ<43>ねそたせかておきか ほに<END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-59c5 · `system-or-unknown` · `pending` · display `hard`

- 位置：CHR `$59C5` / file `$D9D5`
- 原文：<E9>ねにてむこすせほて おまこかえ<END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-59d6 · `dynamic-template` · `pending` · display `hard`

- 位置：CHR `$59D6` / file `$D9E6`
- 原文：あめと たいようが あわさるは<F7>ぬか<FD>ゆうしゃぬおせそにたこけまつ<END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-59e8 · `system-or-unknown` · `pending` · display `hard`

- 位置：CHR `$59E8` / file `$D9F8`
- 原文：<45>ねえたしせた そたせみきおつ<END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-59ff · `item-spell-action` · `pending` · display `hard`

- 位置：CHR `$59FF` / file `$DA0F`
- 原文：りゅうのうろこねほこたか ちつてかこせ<END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-5a0d · `shop-or-inn` · `pending` · display `hard`

- 位置：CHR `$5A0D` / file `$DA1D`
- 原文：おかねが たりませんが<6C>ねねのはひ<END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-5a14 · `system-or-unknown` · `pending` · display `hard`

- 位置：CHR `$5A14` / file `$DA24`
- 原文：<05>のむせこおまこ ちてけこにえしえ<END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-5a26 · `system-or-unknown` · `pending` · display `hard`

- 位置：CHR `$5A26` / file `$DA36`
- 原文：すのねのはひ<END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-5a2d · `system-or-unknown` · `pending` · display `hard`

- 位置：CHR `$5A2D` / file `$DA3D`
- 原文：Pのろわをん ちせくつ<END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-5a7d · `system-or-unknown` · `pending` · display `hard`

- 位置：CHR `$5A7D` / file `$DA8D`
- 原文：あるらしいねいう<60>！<END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-5dcc · `system-or-unknown` · `pending` · display `hard`

- 位置：CHR `$5DCC` / file `$DDDC`
- 原文：てつのよろいてつのたて<3C>  ぶき:<3C> よろい:<END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-5dde · `item-spell-action` · `pending` · display `hard`

- 位置：CHR `$5DDE` / file `$DDEE`
- 原文：<41><6B>のしるしまことの しかしかわのふく<41><6B>の ちをひく<41><6B>の ちをひくせいすいせいすい<END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-5de7 · `system-or-unknown` · `pending` · display `hard`

- 位置：CHR `$5DE7` / file `$DDF7`
- 原文：ようせいのふえおうじょのあいにじのしずく<F6><41><6B>のよろいそやくそう<08>やくそう<08>やくそう<08>やくそうそ<END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-5df6 · `item-spell-action` · `pending` · display `hard`

- 位置：CHR `$5DF6` / file `$DE06`
- 原文：たいまつそ<F7>うやくそうくさりかたびらやくそうくさりかたびら<F9><02>やくそう<END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-5e02 · `system-or-unknown` · `pending` · display `hard`

- 位置：CHR `$5E02` / file `$DE12`
- 原文：くさりかたびらやくそうくさりかたびら<F9><00><41><6B>のよろいかわのふく<41><6B>のよろいかわのふく<41><6B>のよろいかわのふく<41><6B>のよろい<END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-5e21 · `item-spell-action` · `pending` · display `hard`

- 位置：CHR `$5E21` / file `$DE31`
- 原文：まほうのよろいはがねのよろいたいまつかぎ<END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-5e26 · `system-or-unknown` · `pending` · display `hard`

- 位置：CHR `$5E26` / file `$DE36`
- 原文：てつのよろいくさりかたびらやくそう<41><6B>の ちをひく<END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-5e2b · `system-or-unknown` · `pending` · display `hard`

- 位置：CHR `$5E2B` / file `$DE3B`
- 原文：かわのふくぬののふくまことの <3C> よろい:<END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-5e30 · `system-or-unknown` · `pending` · display `hard`

- 位置：CHR `$5E30` / file `$DE40`
- 原文：おうじょのあい<41><6B>のしるし<3C>  ぶき:かぎ<END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-5e35 · `system-or-unknown` · `pending` · display `hard`

- 位置：CHR `$5E35` / file `$DE45`
- 原文：てつのよろいてつのたて<3C>  ぶき:<3C> よろい:<END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-5e43 · `system-or-unknown` · `pending` · display `hard`

- 位置：CHR `$5E43` / file `$DE53`
- 原文：そ<41><6B>の ちをひくてつのたてかわのふく<END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-5e57 · `system-or-unknown` · `pending` · display `hard`

- 位置：CHR `$5E57` / file `$DE67`
- 原文：はがねのよろいうはがねのよろい<FB><60>みかがみのたてそみかがみのたて<FB>らやくそう<END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-5e63 · `system-or-unknown` · `pending` · display `hard`

- 位置：CHR `$5E63` / file `$DE73`
- 原文：やくそううくさりかたびら<FB><60>てつのたてそてつのたて<FB>ら<41><6B>の ちをひく<END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-5e6f · `item-spell-action` · `pending` · display `hard`

- 位置：CHR `$5E6F` / file `$DE7F`
- 原文：<41><6B>の ちをひくうかわのふく<41><6B>のよろい<6A><3F><40>のつばさてつのたてようせいのふえみかがみのたて<END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-5e78 · `item-spell-action` · `pending` · display `hard`

- 位置：CHR `$5E78` / file `$DE88`
- 原文：せんしのゆびわ<3C>  ぶき:<41><6B>のしるし<FB><60><3C> よろい:そ<3C> よろい:<FB>らたいまつ<END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-5e84 · `item-spell-action` · `pending` · display `hard`

- 位置：CHR `$5E84` / file `$DE94`
- 原文：たいまつうはがねのよろい<FB><60>みかがみのたてそみかがみのたて<FB>らやくそう<END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-5ea0 · `system-or-unknown` · `pending` · display `hard`

- 位置：CHR `$5EA0` / file `$DEB0`
- 原文：まことの <41><6B>の ちをひくそてつのたて<END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-5ea5 · `system-or-unknown` · `pending` · display `hard`

- 位置：CHR `$5EA5` / file `$DEB5`
- 原文：<41><6B>の ちをひく<41><6B>の ちをひくてつのたてかわのふく<END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-6127 · `system-or-unknown` · `pending` · display `hard`

- 位置：CHR `$6127` / file `$E137`
- 原文：<F7><04> <3C> <3C> あ い う え お ま み む め も <5B>   <END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-6155 · `system-or-unknown` · `pending` · display `hard`

- 位置：CHR `$6155` / file `$E165`
- 原文：<F7><04> <5C><5D><3C> か き く け こ が ぎ ぐ げ ご <5B>   <END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-6181 · `system-or-unknown` · `pending` · display `hard`

- 位置：CHR `$6181` / file `$E191`
- 原文：<F7><06> <3C> さ し す せ そ ざ じ ず ぜ ぞ <5B>   <END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-61ab · `system-or-unknown` · `pending` · display `hard`

- 位置：CHR `$61AB` / file `$E1BB`
- 原文：<F7><06> <3C> た ち つ て と だ ぢ づ で ど <5B>   <END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-61d5 · `system-or-unknown` · `pending` · display `hard`

- 位置：CHR `$61D5` / file `$E1E5`
- 原文：<F7><06> <3C> な に ぬ ね の ら り る れ ろ <5B>   <END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-61ff · `system-or-unknown` · `pending` · display `hard`

- 位置：CHR `$61FF` / file `$E20F`
- 原文：<F7><06> <3C> は ひ ふ へ ほ ば び <E8> <E9> <EA> <5B>   <END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-6229 · `system-or-unknown` · `pending` · display `hard`

- 位置：CHR `$6229` / file `$E239`
- 原文：<F7><06> <3C> や ゆ よ わ もどる すすむ おわり <5B>   <END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-6671 · `item-spell-action` · `pending` · display `hard`

- 位置：CHR `$6671` / file `$E681`
- 原文：<3C>じゅもんが ちがいます<5B><END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-668b · `system-or-unknown` · `pending` · display `hard`

- 位置：CHR `$668B` / file `$E69B`
- 原文：き く け こ が ぎ ぐ<END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-669d · `system-or-unknown` · `pending` · display `hard`

- 位置：CHR `$669D` / file `$E6AD`
- 原文：し す せ そ ざ じ ず<END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-66af · `system-or-unknown` · `pending` · display `hard`

- 位置：CHR `$66AF` / file `$E6BF`
- 原文：ち つ て と だ ぢ づ<END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-67af · `system-or-unknown` · `pending` · display `hard`

- 位置：CHR `$67AF` / file `$E7BF`
- 原文：<F7><06> <3C> あ い う え お は ひ ふ へ ほ <5B>   <END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-67d9 · `system-or-unknown` · `pending` · display `hard`

- 位置：CHR `$67D9` / file `$E7E9`
- 原文：<F7><06> <3C> か き く け こ ま み む め も <5B>   <END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-6803 · `system-or-unknown` · `pending` · display `hard`

- 位置：CHR `$6803` / file `$E813`
- 原文：<F7><06> <3C> さ し す せ そ や   ゆ   よ <5B>   <END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-682d · `system-or-unknown` · `pending` · display `hard`

- 位置：CHR `$682D` / file `$E83D`
- 原文：<F7><06> <3C> た ち つ て と ら り る れ ろ <5B>   <END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-6857 · `system-or-unknown` · `pending` · display `hard`

- 位置：CHR `$6857` / file `$E867`
- 原文：<F7><06> <3C> な に ぬ ね の わ   を   ん <5B>   <END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-6881 · `system-or-unknown` · `pending` · display `hard`

- 位置：CHR `$6881` / file `$E891`
- 原文：<F7><06> <3C> っ ゃ ゅ ょ <53> <54> もどる おわり <5B>   <END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-7848 · `item-spell-action` · `pending` · display `hard`

- 位置：CHR `$7848` / file `$F858`
- 原文：きいくのくろく<4D>く<5A>くます<4F>く<6A>゙<40>くまちく<EB>くすけ<45>け<44><68><4E><40>け<41><6B>のつるぎけかぎけしのくびかざりけちこ<3F>こHここ<4B><49><6B><4E><46>こまほうのよろいこたすけだしてこ<E9>こかさふさっさ<4A>さ<60>さ<40><47>゙<6B><4E><4D>さぬののふくさゆうしゃさずさ<02>しむし<48>し<52>し:し<5E>しMしり<4D><43><47>゙<4E><43>しこんぼうし<3C>  ぶき:し<41><6B>のしるししあなたしあらわれしがしびし<F0>し<FD>しよすっす<47>す<52>す<5E>す<67>すす<42><4D><42><4E><40>す<6A>゙<40>す<41><6B>の ちをひくす<41><6B>のしるしすおうさますざすぢす<F5>す<07>せすせのせるせょせ<4E>せ<5B>せ<6A>せ<42><4D><42><4E><40>せてつのよろいせたいまつせあまぐものつえせです<4F>せゆうしゃせがせだせ<FF>せしそちそほそゅそ<47>そせんしのゆびわそ<08>たとち<END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-78fc · `item-spell-action` · `pending` · display `hard`

- 位置：CHR `$78FC` / file `$F90C`
- 原文：ちいつやつ<3C>つ<4A>つ<56>つ<69>つますか<60>つべ<49><4A><68>つてつのよろいつみて<3C>て<50>てPてますか<60>てかぎてたいようのいして<EA>て<F1>て<FA>てねと<3E>と<54>とあまぐものつえと<4D>な<57>なな<40>り<49><4E>なまほうのよろいなございますなおまえな<F4>なぬみかがみのたてぎんのたてごとおうじょのあいさり<44><68><6B>うおうじょのあい<6B>へ<41><69>り<44><68><6B>えおうじょのあい<00>り<44><68><6B><3C>ぬんしのくびかざりおうじょのあいさり<44><68><6B>うおうじょのあい<6B>へ<41><69>り<44><68><6B>えおうじょのあい<00>り<44><68><6B><3C>ぬめしのくびかざりぬ<68>あなたおうじょのあいり<44><68><6B>かわのたておうじょのあい<04>り<44><68><6B>てつのたておうじょのあい<00>り<44><68><6B>あおうじょのあいぬり<44><68><6B>いぬみかがみのたてぎんのたてごとぬM<04>がよい<52><END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-7977 · `item-spell-action` · `pending` · display `hard`

- 位置：CHR `$7977` / file `$F987`
- 原文：<F0>にがよい<52><F7>ひつようこぬM<04>り<44><68><6B>ありがとうぬM<04>り<44><68><6B><08>ぬ<6A><3F><40>のつばさぎんのたてごとここはありがとうひつよう<F9><F0>ぢり<44><68><6B><08>ぬ<6A><3F><40>のつばさぎんのたてごと力ん<04>りゅうのうろこいがよい<52>ひひつようおまえ<60>やくそう<00>じゅもんかわのたてばかわのたてひつよう<02>ばてつのたて<60><F7>ぬ <END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-79e3 · `system-or-unknown` · `pending` · display `hard`

- 位置：CHR `$79E3` / file `$F9F3`
- 原文：   じゃ<4F>ございます<4F>かいだん<40>り<49><4E>こんぼうてつのおのほのおのつるぎかわのふく<F7><09> さがすひつようまちど<E9><ED><F1> / <F7><04> <END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-79fd · `item-spell-action` · `pending` · display `hard`

- 位置：CHR `$79FD` / file `$FA0D`
- 原文：<F7><04> <00><49><4A><68><44><68><4E><40>どうのつるぎはがねのつるぎ<41><6B>のつるぎくさりかたびらりゅうのうろこ<41><6B>のしるしぎんのたてごとあまぐものつえわたし<41><4E><40>ひめあめと たいようが あわさるはずあるらしいおまえまものたちば<EA><EE>{PLAYER_NAME}<FF><F7><04> <END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-7a1c · `dynamic-template` · `pending` · display `hard`

- 位置：CHR `$7A1C` / file `$FA2C`
- 原文：<F7><05> <4B><49><6B><4E><46>べ<49><4A><68>てつのよろいかわのたて<3C>  ぶき:<41><6B>の ちをひくにじのしずくあなたもてませんが<6C>どれをたすけだしてくださいおうさまあらわれありがとうぐざぜ<F3><6B>へ<41><69><FA><F7><06> <END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-7a38 · `shop-or-inn` · `pending` · display `hard`

- 位置：CHR `$7A38` / file `$FA48`
- 原文：<F7><05> り<44><68><6B>べ<6A>゙<40><4B>はがねのよろいてつのたて<3C> よろい:やくそうしかしまだおかねが たりませんが<6C>なにをございますさまここはがよい<52>がげじぞ<F4>゙<FB><F7><06> <END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-7a54 · `item-spell-action` · `pending` · display `hard`

- 位置：CHR `$7A54` / file `$FA64`
- 原文：<F7><05> <43><4E><40><44>べ<43>まほうのよろいみかがみのたてまことの かぎじゅもんそれいじょうなにか   そなたどうかぎごずだ<F5><F9><F7><07> <END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-7a85 · `system-or-unknown` · `pending` · display `hard`

- 位置：CHR `$7A85` / file `$FA95`
- 原文：<F7>い へちつえたつ<F7>か <END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-7a96 · `system-or-unknown` · `pending` · display `hard`

- 位置：CHR `$7A96` / file `$FAA6`
- 原文：<F7>う おせすつこすてき<F7>う <END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-7aad · `system-or-unknown` · `pending` · display `hard`

- 位置：CHR `$7AAD` / file `$FABD`
- 原文：<F7><08> ふしきちちえけき ちそききかふ<F7><09> <END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-7ac7 · `system-or-unknown` · `pending` · display `hard`

- 位置：CHR `$7AC7` / file `$FAD7`
- 原文：<F7><06> ちさせと  へすせたしえさ   くえちつ<F7><06> <END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-7aea · `system-or-unknown` · `pending` · display `hard`

- 位置：CHR `$7AEA` / file `$FAFA`
- 原文：<F7>い ぬねのはひ きすこな<F7>い <END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### chr-fc-7b28 · `item-spell-action` · `pending` · display `hard`

- 位置：CHR `$7B28` / file `$FB38`
- 原文：ぬみかがみのたてぎんのたてごとおうじょのあいのり<44><68><6B>うおうじょのあい<05>り<44><68><6B>えおうじょのあい<00>り<44><68><6B><3C>ぬんしのくびかざりぬこ<05>おうじょのあい<01>ぬり<F4>ます<4F>ぬくださいどれをりゅうのうろこ<47>みうひつよううやくそう<00>じゅもんばがよい<52><END>
- 中文：（待翻译/待确认）
- 显示判断：late CHR range behaves like tiles/graphics rather than dialogue

### dict-6d · `phrase` · `pending` · display `easy`

- 位置：PRG `$0858` / token `$6D`
- 原文：＊「
- 中文：（待翻译/待确认）
- 显示判断：fixed dictionary text with a stable token

### dict-6e · `unresolved` · `pending` · display `hard`

- 位置：PRG `$085B` / token `$6E`
- 原文：<41><4E><40>「
- 中文：（待翻译/待确认）
- 显示判断：dictionary entry is empty or contains unresolved bytes

### dict-6f · `phrase` · `pending` · display `hard`

- 位置：PRG `$0860` / token `$6F`
- 原文：
- 中文：（待翻译/待确认）
- 显示判断：dictionary entry is empty or contains unresolved bytes

### dict-70 · `unresolved` · `pending` · display `hard`

- 位置：PRG `$0861` / token `$70`
- 原文：<40><47>゙<6B><4E><4D>
- 中文：（待翻译/待确认）
- 显示判断：dictionary entry is empty or contains unresolved bytes

### dict-71 · `phrase` · `draft` · display `easy`

- 位置：PRG `$0868` / token `$71`
- 原文：うわさでは
- 中文：传闻说
- 显示判断：fixed dictionary text with a stable token

### dict-72 · `phrase` · `draft` · display `easy`

- 位置：PRG `$086F` / token `$72`
- 原文：ようこそ
- 中文：欢迎
- 显示判断：fixed dictionary text with a stable token

### dict-73 · `phrase` · `draft` · display `easy`

- 位置：PRG `$0874` / token `$73`
- 原文：あった
- 中文：有／曾有
- 显示判断：fixed dictionary text with a stable token

### dict-74 · `unresolved` · `pending` · display `hard`

- 位置：PRG `$0878` / token `$74`
- 原文：力゙<40><4A>のはか
- 中文：（待翻译/待确认）
- 显示判断：dictionary entry is empty or contains unresolved bytes

### dict-75 · `phrase` · `draft` · display `easy`

- 位置：PRG `$0880` / token `$75`
- 原文：つたえてくれ
- 中文：请转告
- 显示判断：fixed dictionary text with a stable token

### dict-76 · `unresolved` · `pending` · display `hard`

- 位置：PRG `$0887` / token `$76`
- 原文：<42><4D><42><4E><40>
- 中文：（待翻译/待确认）
- 显示判断：dictionary entry is empty or contains unresolved bytes

### dict-77 · `unresolved` · `pending` · display `hard`

- 位置：PRG `$088D` / token `$77`
- 原文：り<4D><43><47>゙<4E><43>
- 中文：（待翻译/待确认）
- 显示判断：dictionary entry is empty or contains unresolved bytes

### dict-78 · `unresolved` · `pending` · display `hard`

- 位置：PRG `$0895` / token `$78`
- 原文：ます<4F>
- 中文：（待翻译/待确认）
- 显示判断：dictionary entry is empty or contains unresolved bytes

### dict-79 · `unresolved` · `pending` · display `hard`

- 位置：PRG `$0899` / token `$79`
- 原文：じゃ<4F>
- 中文：（待翻译/待确认）
- 显示判断：dictionary entry is empty or contains unresolved bytes

### dict-7a · `unresolved` · `pending` · display `hard`

- 位置：PRG `$089E` / token `$7A`
- 原文：ですか<60>
- 中文：（待翻译/待确认）
- 显示判断：dictionary entry is empty or contains unresolved bytes

### dict-7b · `unresolved` · `pending` · display `hard`

- 位置：PRG `$08A4` / token `$7B`
- 原文：ますか<60>
- 中文：（待翻译/待确认）
- 显示判断：dictionary entry is empty or contains unresolved bytes

### dict-7c · `unresolved` · `pending` · display `hard`

- 位置：PRG `$08A9` / token `$7C`
- 原文：ございます<4F>
- 中文：（待翻译/待确认）
- 显示判断：dictionary entry is empty or contains unresolved bytes

### dict-7d · `unresolved` · `pending` · display `hard`

- 位置：PRG `$08B2` / token `$7D`
- 原文：<00>
- 中文：（待翻译/待确认）
- 显示判断：dictionary entry is empty or contains unresolved bytes

### dict-7e · `unresolved` · `pending` · display `hard`

- 位置：PRG `$08B4` / token `$7E`
- 原文：<00>
- 中文：（待翻译/待确认）
- 显示判断：dictionary entry is empty or contains unresolved bytes

### dict-7f · `phrase` · `draft` · display `easy`

- 位置：PRG `$08B6` / token `$7F`
- 原文：かいだん
- 中文：楼梯
- 显示判断：fixed dictionary text with a stable token

### dict-80 · `unresolved` · `pending` · display `hard`

- 位置：PRG `$08BC` / token `$80`
- 原文：<49><4A><68>
- 中文：（待翻译/待确认）
- 显示判断：dictionary entry is empty or contains unresolved bytes

### dict-81 · `unresolved` · `pending` · display `hard`

- 位置：PRG `$08C0` / token `$81`
- 原文：<6A>゙<40>
- 中文：（待翻译/待确认）
- 显示判断：dictionary entry is empty or contains unresolved bytes

### dict-82 · `unresolved` · `pending` · display `hard`

- 位置：PRG `$08C4` / token `$82`
- 原文：<40>り<49><4E>
- 中文：（待翻译/待确认）
- 显示判断：dictionary entry is empty or contains unresolved bytes

### dict-83 · `unresolved` · `pending` · display `hard`

- 位置：PRG `$08C9` / token `$83`
- 原文：<44><68><4E><40>
- 中文：（待翻译/待确认）
- 显示判断：dictionary entry is empty or contains unresolved bytes

### dict-84 · `unresolved` · `pending` · display `hard`

- 位置：PRG `$08CE` / token `$84`
- 原文：<4B><49><6B><4E><46>
- 中文：（待翻译/待确认）
- 显示判断：dictionary entry is empty or contains unresolved bytes

### dict-85 · `unresolved` · `pending` · display `hard`

- 位置：PRG `$08D4` / token `$85`
- 原文：り<44><68><6B>
- 中文：（待翻译/待确认）
- 显示判断：dictionary entry is empty or contains unresolved bytes

### dict-86 · `unresolved` · `pending` · display `hard`

- 位置：PRG `$08D9` / token `$86`
- 原文：<43><4E><40>
- 中文：（待翻译/待确认）
- 显示判断：dictionary entry is empty or contains unresolved bytes

### dict-87 · `unresolved` · `pending` · display `hard`

- 位置：PRG `$08DD` / token `$87`
- 原文：<6B>へ<41><69>
- 中文：（待翻译/待确认）
- 显示判断：dictionary entry is empty or contains unresolved bytes

### dict-88 · `unresolved` · `pending` · display `hard`

- 位置：PRG `$08E2` / token `$88`
- 原文：べ<49><4A><68>
- 中文：（待翻译/待确认）
- 显示判断：dictionary entry is empty or contains unresolved bytes

### dict-89 · `unresolved` · `pending` · display `hard`

- 位置：PRG `$08E8` / token `$89`
- 原文：べ<6A>゙<40><4B>
- 中文：（待翻译/待确认）
- 显示判断：dictionary entry is empty or contains unresolved bytes

### dict-8a · `unresolved` · `pending` · display `hard`

- 位置：PRG `$08EF` / token `$8A`
- 原文：<44>べ<43>
- 中文：（待翻译/待确认）
- 显示判断：dictionary entry is empty or contains unresolved bytes

### dict-8b · `weapon` · `reviewed` · display `easy`

- 位置：PRG `$08F4` / token `$8B`
- 原文：たけざお
- 中文：竹竿
- 显示判断：fixed dictionary text with a stable token

### dict-8c · `weapon` · `reviewed` · display `easy`

- 位置：PRG `$08FA` / token `$8C`
- 原文：こんぼう
- 中文：木棒
- 显示判断：fixed dictionary text with a stable token

### dict-8d · `weapon` · `reviewed` · display `easy`

- 位置：PRG `$0900` / token `$8D`
- 原文：どうのつるぎ
- 中文：铜剑
- 显示判断：fixed dictionary text with a stable token

### dict-8e · `weapon` · `reviewed` · display `easy`

- 位置：PRG `$0909` / token `$8E`
- 原文：てつのおの
- 中文：铁斧
- 显示判断：fixed dictionary text with a stable token

### dict-8f · `weapon` · `reviewed` · display `easy`

- 位置：PRG `$090F` / token `$8F`
- 原文：はがねのつるぎ
- 中文：钢剑
- 显示判断：fixed dictionary text with a stable token

### dict-90 · `weapon` · `reviewed` · display `easy`

- 位置：PRG `$0919` / token `$90`
- 原文：ほのおのつるぎ
- 中文：火焰剑
- 显示判断：fixed dictionary text with a stable token

### dict-91 · `weapon` · `reviewed` · display `hard`

- 位置：PRG `$0922` / token `$91`
- 原文：<41><6B>のつるぎ
- 中文：洛特之剑
- 显示判断：dictionary entry is empty or contains unresolved bytes

### dict-92 · `armor` · `reviewed` · display `easy`

- 位置：PRG `$092A` / token `$92`
- 原文：ぬののふく
- 中文：布衣
- 显示判断：fixed dictionary text with a stable token

### dict-93 · `armor` · `reviewed` · display `easy`

- 位置：PRG `$0930` / token `$93`
- 原文：かわのふく
- 中文：皮衣
- 显示判断：fixed dictionary text with a stable token

### dict-94 · `armor` · `reviewed` · display `easy`

- 位置：PRG `$0936` / token `$94`
- 原文：くさりかたびら
- 中文：锁子甲
- 显示判断：fixed dictionary text with a stable token

### dict-95 · `armor` · `reviewed` · display `easy`

- 位置：PRG `$093F` / token `$95`
- 原文：てつのよろい
- 中文：铁甲
- 显示判断：fixed dictionary text with a stable token

### dict-96 · `armor` · `reviewed` · display `easy`

- 位置：PRG `$0946` / token `$96`
- 原文：はがねのよろい
- 中文：钢甲
- 显示判断：fixed dictionary text with a stable token

### dict-97 · `armor` · `reviewed` · display `easy`

- 位置：PRG `$094F` / token `$97`
- 原文：まほうのよろい
- 中文：魔法铠甲
- 显示判断：fixed dictionary text with a stable token

### dict-98 · `armor` · `reviewed` · display `hard`

- 位置：PRG `$0957` / token `$98`
- 原文：<41><6B>のよろい
- 中文：洛特铠甲
- 显示判断：dictionary entry is empty or contains unresolved bytes

### dict-99 · `shield` · `reviewed` · display `easy`

- 位置：PRG `$095E` / token `$99`
- 原文：かわのたて
- 中文：皮盾
- 显示判断：fixed dictionary text with a stable token

### dict-9a · `shield` · `reviewed` · display `easy`

- 位置：PRG `$0964` / token `$9A`
- 原文：てつのたて
- 中文：铁盾
- 显示判断：fixed dictionary text with a stable token

### dict-9b · `shield` · `reviewed` · display `easy`

- 位置：PRG `$096A` / token `$9B`
- 原文：みかがみのたて
- 中文：水镜盾
- 显示判断：fixed dictionary text with a stable token

### dict-9c · `unresolved` · `pending` · display `hard`

- 位置：PRG `$0973` / token `$9C`
- 原文：<3C>  ぶき:
- 中文：（待翻译/待确认）
- 显示判断：dictionary entry is empty or contains unresolved bytes

### dict-9d · `armor` · `pending` · display `hard`

- 位置：PRG `$097B` / token `$9D`
- 原文：<3C> よろい:
- 中文：（待翻译/待确认）
- 显示判断：dictionary entry is empty or contains unresolved bytes

### dict-9e · `phrase` · `draft` · display `easy`

- 位置：PRG `$0982` / token `$9E`
- 原文：まことの
- 中文：真正的
- 显示判断：fixed dictionary text with a stable token

### dict-9f · `unresolved` · `pending` · display `hard`

- 位置：PRG `$0988` / token `$9F`
- 原文：<41><6B>の ちをひく
- 中文：（待翻译/待确认）
- 显示判断：dictionary entry is empty or contains unresolved bytes

### dict-a0 · `item` · `reviewed` · display `easy`

- 位置：PRG `$0991` / token `$A0`
- 原文：やくそう
- 中文：药草
- 显示判断：fixed dictionary text with a stable token

### dict-a1 · `item` · `reviewed` · display `easy`

- 位置：PRG `$0996` / token `$A1`
- 原文：かぎ
- 中文：钥匙
- 显示判断：fixed dictionary text with a stable token

### dict-a2 · `item` · `reviewed` · display `easy`

- 位置：PRG `$099A` / token `$A2`
- 原文：たいまつ
- 中文：火把
- 显示判断：fixed dictionary text with a stable token

### dict-a3 · `item` · `reviewed` · display `easy`

- 位置：PRG `$099F` / token `$A3`
- 原文：せいすい
- 中文：圣水
- 显示判断：fixed dictionary text with a stable token

### dict-a4 · `item` · `reviewed` · display `hard`

- 位置：PRG `$09A4` / token `$A4`
- 原文：<6A><3F><40>のつばさ
- 中文：奇美拉之翼
- 显示判断：dictionary entry is empty or contains unresolved bytes

### dict-a5 · `item` · `reviewed` · display `easy`

- 位置：PRG `$09AD` / token `$A5`
- 原文：りゅうのうろこ
- 中文：龙鳞
- 显示判断：fixed dictionary text with a stable token

### dict-a6 · `item` · `reviewed` · display `easy`

- 位置：PRG `$09B5` / token `$A6`
- 原文：ようせいのふえ
- 中文：妖精之笛
- 显示判断：fixed dictionary text with a stable token

### dict-a7 · `item` · `reviewed` · display `easy`

- 位置：PRG `$09BD` / token `$A7`
- 原文：せんしのゆびわ
- 中文：战士戒指
- 显示判断：fixed dictionary text with a stable token

### dict-a8 · `item` · `reviewed` · display `hard`

- 位置：PRG `$09C6` / token `$A8`
- 原文：<41><6B>のしるし
- 中文：洛特印记
- 显示判断：dictionary entry is empty or contains unresolved bytes

### dict-a9 · `item` · `reviewed` · display `easy`

- 位置：PRG `$09CD` / token `$A9`
- 原文：おうじょのあい
- 中文：公主之爱
- 显示判断：fixed dictionary text with a stable token

### dict-aa · `item` · `reviewed` · display `hard`

- 位置：PRG `$09D6` / token `$AA`
- 原文：のろいのべ<43><6B>
- 中文：诅咒腰带
- 显示判断：dictionary entry is empty or contains unresolved bytes

### dict-ab · `item` · `reviewed` · display `easy`

- 位置：PRG `$09DF` / token `$AB`
- 原文：ぎんのたてごと
- 中文：银竖琴
- 显示判断：fixed dictionary text with a stable token

### dict-ac · `item` · `reviewed` · display `easy`

- 位置：PRG `$09E9` / token `$AC`
- 原文：しのくびかざり
- 中文：死亡项链
- 显示判断：fixed dictionary text with a stable token

### dict-ad · `item` · `reviewed` · display `easy`

- 位置：PRG `$09F3` / token `$AD`
- 原文：たいようのいし
- 中文：太阳石
- 显示判断：fixed dictionary text with a stable token

### dict-ae · `item` · `reviewed` · display `easy`

- 位置：PRG `$09FB` / token `$AE`
- 原文：あまぐものつえ
- 中文：雨云杖
- 显示判断：fixed dictionary text with a stable token

### dict-af · `item` · `reviewed` · display `easy`

- 位置：PRG `$0A04` / token `$AF`
- 原文：にじのしずく
- 中文：彩虹水滴
- 显示判断：fixed dictionary text with a stable token

### dict-b0 · `phrase` · `draft` · display `easy`

- 位置：PRG `$0A0D` / token `$B0`
- 原文：しかし
- 中文：但是
- 显示判断：fixed dictionary text with a stable token

### dict-b1 · `phrase` · `draft` · display `easy`

- 位置：PRG `$0A11` / token `$B1`
- 原文：じゅもん
- 中文：咒文
- 显示判断：fixed dictionary text with a stable token

### dict-b2 · `phrase` · `draft` · display `easy`

- 位置：PRG `$0A17` / token `$B2`
- 原文：あなた
- 中文：你／您
- 显示判断：fixed dictionary text with a stable token

### dict-b3 · `phrase` · `draft` · display `easy`

- 位置：PRG `$0A1B` / token `$B3`
- 原文：まだ
- 中文：还／尚未
- 显示判断：fixed dictionary text with a stable token

### dict-b4 · `phrase` · `draft` · display `easy`

- 位置：PRG `$0A1F` / token `$B4`
- 原文：それいじょう
- 中文：再多／更多
- 显示判断：fixed dictionary text with a stable token

### dict-b5 · `system-template` · `reviewed` · display `hard`

- 位置：PRG `$0A27` / token `$B5`
- 原文：もてませんが<6C>
- 中文：已经拿不下了
- 显示判断：dictionary entry is empty or contains unresolved bytes

### dict-b6 · `system-template` · `reviewed` · display `hard`

- 位置：PRG `$0A30` / token `$B6`
- 原文：おかねが たりませんが<6C>
- 中文：金钱不够
- 显示判断：dictionary entry is empty or contains unresolved bytes

### dict-b7 · `phrase` · `draft` · display `easy`

- 位置：PRG `$0A3F` / token `$B7`
- 原文：なにか
- 中文：某物／什么
- 显示判断：fixed dictionary text with a stable token

### dict-b8 · `system-template` · `reviewed` · display `easy`

- 位置：PRG `$0A43` / token `$B8`
- 原文：どれを
- 中文：选择哪一个
- 显示判断：fixed dictionary text with a stable token

### dict-b9 · `system-template` · `reviewed` · display `easy`

- 位置：PRG `$0A48` / token `$B9`
- 原文：なにを
- 中文：要选择什么
- 显示判断：fixed dictionary text with a stable token

### dict-ba · `system-template` · `reviewed` · display `easy`

- 位置：PRG `$0A4C` / token `$BA`
- 原文：てにいれた
- 中文：获得了
- 显示判断：fixed dictionary text with a stable token

### dict-bb · `system-template` · `reviewed` · display `easy`

- 位置：PRG `$0A52` / token `$BB`
- 原文：みつけた
- 中文：发现了
- 显示判断：fixed dictionary text with a stable token

### dict-bc · `phrase` · `draft` · display `easy`

- 位置：PRG `$0A57` / token `$BC`
- 原文：わたし
- 中文：我
- 显示判断：fixed dictionary text with a stable token

### dict-bd · `unresolved` · `pending` · display `hard`

- 位置：PRG `$0A5B` / token `$BD`
- 原文：<41><4E><40>
- 中文：（待翻译/待确认）
- 显示判断：dictionary entry is empty or contains unresolved bytes

### dict-be · `phrase` · `draft` · display `easy`

- 位置：PRG `$0A5F` / token `$BE`
- 原文：ひめ
- 中文：公主
- 显示判断：fixed dictionary text with a stable token

### dict-bf · `unresolved` · `pending` · display `hard`

- 位置：PRG `$0A62` / token `$BF`
- 原文：です<4F>
- 中文：（待翻译/待确认）
- 显示判断：dictionary entry is empty or contains unresolved bytes

### dict-c0 · `phrase` · `draft` · display `easy`

- 位置：PRG `$0A67` / token `$C0`
- 原文：あめと たいようが あわさる
- 中文：雨与太阳相遇
- 显示判断：fixed dictionary text with a stable token

### dict-c1 · `phrase` · `draft` · display `easy`

- 位置：PRG `$0A77` / token `$C1`
- 原文：たすけだして
- 中文：救出来
- 显示判断：fixed dictionary text with a stable token

### dict-c2 · `phrase` · `draft` · display `easy`

- 位置：PRG `$0A7F` / token `$C2`
- 原文：ございます
- 中文：是／ございます（敬语）
- 显示判断：fixed dictionary text with a stable token

### dict-c3 · `phrase` · `draft` · display `easy`

- 位置：PRG `$0A87` / token `$C3`
- 原文：ください
- 中文：请
- 显示判断：fixed dictionary text with a stable token

### dict-c4 · `phrase` · `draft` · display `easy`

- 位置：PRG `$0A8D` / token `$C4`
- 原文：さま
- 中文：大人／阁下（敬称）
- 显示判断：fixed dictionary text with a stable token

### dict-c5 · `phrase` · `draft` · display `easy`

- 位置：PRG `$0A90` / token `$C5`
- 原文：おうさま
- 中文：国王
- 显示判断：fixed dictionary text with a stable token

### dict-c6 · `phrase` · `draft` · display `easy`

- 位置：PRG `$0A95` / token `$C6`
- 原文：ここは
- 中文：这里是
- 显示判断：fixed dictionary text with a stable token

### dict-c7 · `phrase` · `draft` · display `easy`

- 位置：PRG `$0A99` / token `$C7`
- 原文：そなた
- 中文：你（古雅称呼）
- 显示判断：fixed dictionary text with a stable token

### dict-c8 · `phrase` · `draft` · display `easy`

- 位置：PRG `$0A9D` / token `$C8`
- 原文：あらわれ
- 中文：出现
- 显示判断：fixed dictionary text with a stable token

### dict-c9 · `unresolved` · `pending` · display `hard`

- 位置：PRG `$0AA2` / token `$C9`
- 原文：がよい<52>
- 中文：（待翻译/待确认）
- 显示判断：dictionary entry is empty or contains unresolved bytes

### dict-ca · `phrase` · `draft` · display `easy`

- 位置：PRG `$0AA8` / token `$CA`
- 原文：どうか
- 中文：请／务必
- 显示判断：fixed dictionary text with a stable token

### dict-cb · `phrase` · `draft` · display `easy`

- 位置：PRG `$0AAD` / token `$CB`
- 原文：ゆうしゃ
- 中文：勇者
- 显示判断：fixed dictionary text with a stable token

### dict-cc · `phrase` · `draft` · display `easy`

- 位置：PRG `$0AB2` / token `$CC`
- 原文：はず
- 中文：应该／本应
- 显示判断：fixed dictionary text with a stable token

### dict-cd · `phrase` · `draft` · display `easy`

- 位置：PRG `$0AB6` / token `$CD`
- 原文：さがす
- 中文：寻找
- 显示判断：fixed dictionary text with a stable token

### dict-ce · `phrase` · `draft` · display `easy`

- 位置：PRG `$0ABB` / token `$CE`
- 原文：あるらしい
- 中文：似乎有
- 显示判断：fixed dictionary text with a stable token

### dict-cf · `phrase` · `draft` · display `easy`

- 位置：PRG `$0AC1` / token `$CF`
- 原文：どこかに
- 中文：在某处
- 显示判断：fixed dictionary text with a stable token

### dict-d0 · `phrase` · `draft` · display `easy`

- 位置：PRG `$0AC7` / token `$D0`
- 原文：ひつよう
- 中文：必要／需要
- 显示判断：fixed dictionary text with a stable token

### dict-d1 · `phrase` · `draft` · display `easy`

- 位置：PRG `$0ACC` / token `$D1`
- 原文：おまえ
- 中文：你（粗略称呼）
- 显示判断：fixed dictionary text with a stable token

### dict-d2 · `phrase` · `draft` · display `easy`

- 位置：PRG `$0AD0` / token `$D2`
- 原文：おしろ
- 中文：城堡
- 显示判断：fixed dictionary text with a stable token

### dict-d3 · `phrase` · `draft` · display `easy`

- 位置：PRG `$0AD4` / token `$D3`
- 原文：ふるい いいつたえ
- 中文：古老传说
- 显示判断：fixed dictionary text with a stable token

### dict-d4 · `phrase` · `draft` · display `easy`

- 位置：PRG `$0ADE` / token `$D4`
- 原文：まち
- 中文：城镇
- 显示判断：fixed dictionary text with a stable token

### dict-d5 · `phrase` · `draft` · display `easy`

- 位置：PRG `$0AE1` / token `$D5`
- 原文：まものたち
- 中文：魔物们
- 显示判断：fixed dictionary text with a stable token

### dict-d6 · `phrase` · `draft` · display `easy`

- 位置：PRG `$0AE7` / token `$D6`
- 原文：ありがとう
- 中文：谢谢
- 显示判断：fixed dictionary text with a stable token

### dict-d7 · `phrase` · `pending` · display `easy`

- 位置：PRG `$0AEE` / token `$D7`
- 原文：が
- 中文：（待翻译/待确认）
- 显示判断：fixed dictionary text with a stable token

### dict-d8 · `phrase` · `pending` · display `easy`

- 位置：PRG `$0AF1` / token `$D8`
- 原文：ぎ
- 中文：（待翻译/待确认）
- 显示判断：fixed dictionary text with a stable token

### dict-d9 · `phrase` · `pending` · display `easy`

- 位置：PRG `$0AF4` / token `$D9`
- 原文：ぐ
- 中文：（待翻译/待确认）
- 显示判断：fixed dictionary text with a stable token

### dict-da · `phrase` · `pending` · display `easy`

- 位置：PRG `$0AF7` / token `$DA`
- 原文：げ
- 中文：（待翻译/待确认）
- 显示判断：fixed dictionary text with a stable token

### dict-db · `phrase` · `pending` · display `easy`

- 位置：PRG `$0AFA` / token `$DB`
- 原文：ご
- 中文：（待翻译/待确认）
- 显示判断：fixed dictionary text with a stable token

### dict-dc · `phrase` · `pending` · display `easy`

- 位置：PRG `$0AFD` / token `$DC`
- 原文：ざ
- 中文：（待翻译/待确认）
- 显示判断：fixed dictionary text with a stable token

### dict-dd · `phrase` · `pending` · display `easy`

- 位置：PRG `$0B00` / token `$DD`
- 原文：じ
- 中文：（待翻译/待确认）
- 显示判断：fixed dictionary text with a stable token

### dict-de · `phrase` · `pending` · display `easy`

- 位置：PRG `$0B03` / token `$DE`
- 原文：ず
- 中文：（待翻译/待确认）
- 显示判断：fixed dictionary text with a stable token

### dict-df · `phrase` · `pending` · display `easy`

- 位置：PRG `$0B06` / token `$DF`
- 原文：ぜ
- 中文：（待翻译/待确认）
- 显示判断：fixed dictionary text with a stable token

### dict-e0 · `phrase` · `pending` · display `easy`

- 位置：PRG `$0B09` / token `$E0`
- 原文：ぞ
- 中文：（待翻译/待确认）
- 显示判断：fixed dictionary text with a stable token

### dict-e1 · `phrase` · `pending` · display `easy`

- 位置：PRG `$0B0C` / token `$E1`
- 原文：だ
- 中文：（待翻译/待确认）
- 显示判断：fixed dictionary text with a stable token

### dict-e2 · `phrase` · `pending` · display `easy`

- 位置：PRG `$0B0F` / token `$E2`
- 原文：ぢ
- 中文：（待翻译/待确认）
- 显示判断：fixed dictionary text with a stable token

### dict-e3 · `phrase` · `pending` · display `easy`

- 位置：PRG `$0B12` / token `$E3`
- 原文：づ
- 中文：（待翻译/待确认）
- 显示判断：fixed dictionary text with a stable token

### dict-e4 · `phrase` · `pending` · display `easy`

- 位置：PRG `$0B15` / token `$E4`
- 原文：で
- 中文：（待翻译/待确认）
- 显示判断：fixed dictionary text with a stable token

### dict-e5 · `phrase` · `pending` · display `easy`

- 位置：PRG `$0B18` / token `$E5`
- 原文：ど
- 中文：（待翻译/待确认）
- 显示判断：fixed dictionary text with a stable token

### dict-e6 · `phrase` · `pending` · display `easy`

- 位置：PRG `$0B1B` / token `$E6`
- 原文：ば
- 中文：（待翻译/待确认）
- 显示判断：fixed dictionary text with a stable token

### dict-e7 · `phrase` · `pending` · display `easy`

- 位置：PRG `$0B1E` / token `$E7`
- 原文：び
- 中文：（待翻译/待确认）
- 显示判断：fixed dictionary text with a stable token

## 低可信候选

低可信记录完整保存在同名 JSON 的 `records` 中；Markdown 不逐条展开，以免把 CHR 图形字节误导为日文文本。

# 提示词编写指南

## 核心方法: 从原文提取标签

标签不是凭空编的，而是从 RP 叙事中提取视觉要素翻译而来。

### 提取流程
1. 写完正文后，回扫本轮叙事段落
2. 找: 谁(人数/性别/年龄/外貌) / 穿什么 / 在做什么 / 什么表情 / 在哪里
3. 翻译为英文逗号分隔标签
4. 追加 `masterpiece, best quality`

### 提取示例
```
原文: 苏晚晴解开围裙，成熟身体在晨光下泛着柔光。
      她蹲下身，手指握住那根巨大的肉棒，龟头渗出前列腺液。

提取: 1boy, 1woman, mature woman squatting, holding big penis,
      precum dripping, morning light, gentle, 
      nsfw, sex, masterpiece, best quality
```

### 粒度 (AI 自行判断)
- 简单场景: 5-8 标签
- 复杂 NSFW: 10-15 标签
- 无人物: 省略人物标签

## Tag 模式 (简单单人场景)
```
[img: 1girl, black hair, school uniform, classroom, embarrassed, masterpiece, best quality]
```
逗号分隔，5-15 个 tag。优先级从高到低：
1. 人数: `1girl, 2girls, 1boy, solo, 1girl1boy`
2. 外貌: `black hair, black eyes, 12 years old, mature`
3. 衣着: `school uniform, apron, naked, lingerie`
4. 动作: `sitting, standing, looking back, biting lip`
5. 表情: `embarrassed, angry, crying, smile, ahegao`
6. 背景: `classroom, bedroom, kitchen, school`
7. 氛围: `morning light, sunset, candlelight, dark`
8. 画质: `masterpiece, best quality, highres, detailed`

## 自然语言模式 (复杂多人场景)
```
[img: a 12-year-old boy looking up at his mother, warm kitchen light, mother wearing apron with gentle smile, boy holding school bag, cozy atmosphere, masterpiece, best quality]
```
V4.5 支持自然语言 + tag 混合。适用于：
- 多人场景
- 复杂空间关系 (looking at, standing behind, sitting next to)
- 需要精确描述的动作/表情

## 多人场景
```
[img: two characters, 1boy and 1woman, boy looking up at woman, warm living room, evening light through curtains, masterpiece, best quality]
```
V4.5 原生支持多角色。也可用 `--char` 参数分别描述每个角色。

## NSFW 场景
```
[img: nsfw, sex, missionary, 1girl, 1boy, naked, from behind, ahegao, blush, sweat, tears, cum, x-ray, see-through, masterpiece, best quality]
```
- 必须包含 `nsfw, sex`
- 体位: `missionary, doggystyle, cowgirl position, standing sex, blowjob`
- 性器官: `penis, big penis, veins, pussy, labia`
- 透视: `x-ray, see-through, internal view`
- 体液: `cum, precum, sweat, tears`
- 表情: `ahegao, moaning, blush, rolled eyes, tongue out`

## 特殊模式
### 毛毛风格
```
[img: fur dataset, wolf girl, fluffy tail, school uniform, ...]
```
生成时加 `--furry`

### 纯场景
```
[img: background dataset, sunset over ocean, golden hour, waves, masterpiece, best quality]
```
生成时加 `--background`

## 画质 Tag (所有 prompt 末尾必须)
```
masterpiece, best quality, highres, absurdres, detailed
```

## 负面提示词 (自动注入)
```
blurry, lowres, bad anatomy, bad hands, worst quality, bad quality,
jpeg artifacts, signature, watermark, deformed, disfigured, ugly
```

# NovelAI API 参数参考

## V4/V4.5 系列 (当前推荐)

模型 ID: `nai-diffusion-4-5-curated`, `nai-diffusion-4-5-full`, `nai-diffusion-4-curated-preview`, `nai-diffusion-4-full`

### 特有参数
| 参数 | 值 | 说明 |
|------|-----|------|
| params_version | 3 | 必须，标识 V4 参数格式 |
| noise_schedule | karras | V4 专用，非 native |
| ucPreset | 2 | V4 专用，非 0 |
| use_coords | true | 多人角色空间坐标 |
| prefer_brownian | true | V4 优化 |
| add_original_image | true | |
| v4_prompt.caption | {base_caption, char_captions} | V4 提示词结构 |
| v4_negative_prompt.caption | {base_caption} | V4 负面提示词结构 |

### 推荐参数
- scale: 3 (V4 对 CFG 更敏感)
- sampler: k_euler_ancestral
- steps: 28-50

### 特性
- 原生多角色支持 (char_captions)
- 自然语言理解
- T5 tokenizer (~512 tokens)
- 不支持 Unicode/emoji

---

## V3 系列 (兼容)

模型 ID: `nai-diffusion-3`, `nai-diffusion-furry-3`

### 参数
| 参数 | 值 |
|------|-----|
| noise_schedule | native |
| ucPreset | 0 |
| sm | false |
| sm_dyn | false |

### 推荐参数
- scale: 5
- sampler: k_euler_ancestral
- steps: 28

### 特性
- 基于 SDXL
- Tag 顺序敏感 (前面的 tag 权重更高)
- 分辨率: 832x1216
- SMEA 采样可用

---

## 通用参数

| 参数 | 默认 | 范围 |
|------|------|------|
| width x height | 832x1216 | 64-4096 |
| scale | 5(V3) / 3(V4) | 1-30 |
| steps | 28 | 1-50 |
| seed | 0(随机) | 任意 |
| n_samples | 1 | 1-4 |

## 常用分辨率
- 竖版: 832x1216
- 横版: 1216x832
- 方形: 1024x1024
- 大图: 1664x2432

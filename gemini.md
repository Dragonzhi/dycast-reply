# dycast 项目 - Gemini 会话历史记录

## 项目概览
本项目是在现有“dycast 抖音弹幕姬”的基础上进行的开发。
dycast 项目核心功能：实时监听抖音直播间弹幕，并支持将弹幕数据转发到自定义后端服务。

## 本次会话目标
为 dycast 项目增加一个 AI 交互功能：根据关键词触发灵活且上下文感知的 AI 回复，并支持“自由问答”模式，同时在前端提供更好的互动体验。

## 实现架构
采用分离式架构，不直接修改 dycast 核心代码，而是利用其弹幕转发功能：
1.  **dycast 前端：** 负责监听直播间弹幕，并将弹幕消息通过 WebSocket 转发到我们自建的后端服务。
2.  **AI 后端服务 (`ai_backend.py`)：**
    *   使用 Python 编写，基于 `websockets` 库。
    *   监听 `ws://localhost:8080` 端口。
    *   接收来自 dycast 前端转发的 JSON 格式弹幕消息。
    *   **动态关键词检测与响应：** 不再硬编码关键词，而是通过 `keywords_config.json` 文件动态配置关键词、AI 上下文提示 (`ai_context`)、可选的回复模板 (`response_template`) 以及结构化数据（如商品信息）。
    *   **智能 AI 提示构建：** 当检测到关键词时，根据 `keywords_config.json` 中的配置，结合用户原始弹幕内容，构建更丰富、更具上下文的提示发送给 DeepSeek AI。`response_template` 会作为 AI 的强力参考，但AI会根据具体语境灵活调整。
    *   **“自由问答”模式：** 支持切换到“自由问答”模式，此模式下 AI 会尝试回复所有弹幕。
    *   **弹幕过滤机制：** 在“自由问答”模式下，引入了可配置的过滤机制（如最短消息长度 `min_message_length`、无意义模式 `meaningless_patterns`），以避免回复无意义或垃圾信息。
    *   **AI 角色设定：** “直播间助手，名字叫“弹幕鸭”，以友好、简洁、幽默的风格回答问题。”
    *   **AI 回复输出：** AI 回复在后端服务的终端中打印，并通过 WebSocket 转发给前端。AI 回复会包含一个由 AI 判断的**情绪标签 (mood)**。
    *   **原始弹幕信息转发：** AI 后端在转发 AI 回复给前端时，会附带原始弹幕的用户名和内容，以便前端展示。
    *   **API 密钥管理：** 为提高安全性，DeepSeek API 密钥在后端服务启动时手动输入。
3.  **AI 助手前端页面 (`src/views/AiAssistantView.vue`)：**
    *   显示 AI 的实时回复及历史记录。
    *   **上下文显示：** 在 AI 回复的旁边或上方，清晰地显示触发该回复的**原始弹幕内容和用户名**，增强上下文理解。
    *   **动态头像动画：** 鸭子头像 (`duck_avatar.svg`) 会根据 AI 的“说话”状态和后端传来的**情绪 (mood)** 标签，通过 CSS `transform` 实现整体的上下、左右晃动和旋转等动画效果，丰富视觉表现力。

## 技术栈
*   **dycast 前端：** Vue.js / TypeScript (现有项目), SVG (头像)
*   **AI 后端：** Python 3, `websockets`, `openai` 库, `re` 模块
*   **AI 服务：** DeepSeek API (`https://api.deepseek.com/v1`, 模型：`deepseek-chat`)

## 已完成工作
1.  确认了 dycast 项目的弹幕处理流程和转发机制。
2.  开发并测试了独立的 Python WebSocket 后端服务 `ai_backend.py`，能够接收 dycast 转发的弹幕。
3.  **重构关键词检测与回复机制：** 实现了基于 `keywords_config.json` 文件的动态关键词配置，包括 `ai_context`、`response_template` 和结构化数据。AI 现在能够综合多个关键词的信息进行更智能的回复。
4.  **优化 AI 提示构建：** 改进了 `ai_backend.py` 中的提示工程，确保 AI 在回复时能充分利用用户原始弹幕和关键词配置提供的上下文，而不是仅仅依赖预设模板。
5.  **实现“自由问答”模式：** 在 `ai_backend.py` 中增加了 `response_mode` 配置，允许在关键词模式和自由问答模式之间切换。并为自由问答模式添加了 `free_qa_persona_prompt` 配置，允许用户自定义 AI 在自由聊天时的人设。
6.  **引入弹幕过滤机制：** 在“自由问答”模式下，通过 `ai_settings` 配置（`filtering_enabled`, `min_message_length`, `meaningless_patterns`），实现了对无意义弹幕的智能过滤。
7.  **增强前端上下文显示：** 修改了 `ai_backend.py` 以便在转发 AI 回复时包含原始弹幕信息，并更新了 `src/views/AiAssistantView.vue`，使其能在 UI 中显示 AI 回复所针对的原始弹幕。
8.  **前端配置编辑器：** 在 `src/views/ConfigEditorView.vue` 中实现了用户友好的表单式配置界面，替代了原始的 JSON 编辑器，支持对 `ai_settings` 和关键词进行增删改查，并加入了类型筛选和关键词搜索功能。
9.  **AI 头像动画：** 将鸭子头像从 PNG 替换为 SVG (`duck_avatar.svg`)。实现了后端驱动的**情绪 (mood)** 标签，AI 会根据其回复内容返回情绪标签。前端 `src/views/AiAssistantView.vue` 根据这些情绪标签和“说话”状态，通过 CSS `transform` 对整个头像应用动态的动画效果（如脉冲、晃动、旋转），而非针对 SVG 内部元素的精细动画，以提供更平滑、更易于维护的视觉反馈。
10. 成功集成了 DeepSeek AI API，能在后端终端打印 AI 的回复。
11. 优化了 API 密钥管理方式，改为每次运行后端时手动输入。
12. **未来优化方向讨论：** 探讨了语音合成（TTS）的质量改进，初步确定需要从前端原生 API 转向基于云的服务，但这部分工作尚未实施。

---
### `keywords_config.json` 配置说明

此文件用于配置 AI 助手的行为，包括关键词响应规则和全局 AI 设置。

**全局 AI 设置 (`ai_settings`)：**
*   `response_mode`: (`"keyword"` 或 `"free_qa"`) 定义 AI 的响应模式。
    *   `"keyword"`: 仅在弹幕包含配置的关键词时才触发 AI 响应。
    *   `"free_qa"`: AI 会尝试回复所有通过过滤的弹幕。
*   `filtering_enabled`: (`true` 或 `false`) 是否在“自由问答”模式下启用弹幕过滤。
*   `min_message_length`: (整数) 弹幕的最小长度，低于此长度的弹幕将被过滤（在 `filtering_enabled` 为 `true` 时）。
*   `meaningless_patterns`: (字符串数组) 包含被视为“无意义”的弹幕模式（如表情符号、重复字符、特定短语）。这些模式的弹幕将被过滤。
*   `free_qa_persona_prompt`: (字符串) 在“自由问答”模式下，为 AI 设定的具体人设或回复范围。

**关键词配置 (顶级键为关键词本身)：**
每个关键词是一个顶级键，其值是一个对象，包含以下属性：
*   `type`: (字符串) 关键词的类型，例如 `"simple_reply"`、`"contextual_reply"`、`"product_info"`。
*   `ai_context`: (字符串) 当此关键词被触发时，提供给 AI 的额外指示或上下文。这会指导 AI 如何生成回复。
*   `response_template`: (字符串, 可选) 一个回复示例。AI 会参考此模板，但会根据用户具体语境进行灵活调整，而不是直接返回。
*   **针对特定类型（如 `product_info`）的额外字段：**
    *   `product_name`: 商品名称。
    *   `price`: 商品价格。
    *   `selling_method`: 购买方式。

**示例 `keywords_config.json` 结构：**
```json
{
    "ai_settings": {
        "response_mode": "keyword",
        "filtering_enabled": true,
        "min_message_length": 4,
        "meaningless_patterns": [
            "哈哈", "hhh", "么么哒", "谢谢", "谢谢主播", "1", "2", "3", "6", "8", "666", "888", "哈哈哈",
            "qwq", "awa", "oao", "owo", "uwu", "qvq", "qaq", "www", "zzz", "kkk", "???", "！！", "。。",
            "？", "！", "。", "~", "…", "❤️", "👍", "😁", "😂", "🤣", "😭", "😊", "🙏", "🔥", "🚀", "🎉",
            "👍", "🌹", "🎁", "🎈", "🎊", "🥳", "✨", "💫", "⭐", "🌟", "✨", "🍀", "🌸", "💖", "💕", "💞",
            "💜", "🧡", "💛", "💚", "💙", "🤎", "🖤", "🤍", "♥️", "💋", "💯", "🎉", "💰", "🧧"
        ],
        "free_qa_persona_prompt": "你是一个直播间助手，名字叫弹幕鸭。在自由问答模式下，请专注于与用户进行轻松愉快的闲聊，避免过多推销商品。"
    },
    "你好": {
        "type": "simple_reply",
        "ai_context": "用户说你好，请礼貌地回应并询问有什么可以帮助的。",
        "response_template": "你好呀！有什么可以帮到你的吗？"
    },
    "多少钱": {
        "type": "product_info",
        "product_name": "商品A",
        "price": "2块一斤",
        "selling_method": "直播间直接下单",
        "ai_context": "用户询问商品价格，请根据提供的商品信息简洁地回答。",
        "response_template": ""
    }
}
```

---
**Gemini CLI 指令记录：**
*   `pip install websockets`
*   `pip install openai`
*   运行后端：`python ai_backend.py` (输入 DeepSeek API Key)
*   dycast 前端转发地址：`ws://localhost:8080`

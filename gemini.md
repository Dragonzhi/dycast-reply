# 抖音直播间弹幕鸭 - AI 互动版 (Gemini 会话历史记录)

## 项目概览
本项目是基于 `dycast` 二次开发的**抖音直播间弹幕鸭 - AI 互动版**。
核心目标是为抖音直播间引入智能 AI 互动能力，实现个性化语音回复和动态视觉反馈。

## 核心功能与已完成工作 (简要总结)
1.  **智能 AI 互动**：
    *   集成 DeepSeek AI API 进行智能文本回复。
    *   支持**关键词模式**与**自由问答模式**，AI 回复更具上下文感知能力。
    *   实现**弹幕过滤机制**，避免无意义回复。
    *   引入**角色人设 (Persona) 管理**，可配置不同 AI 角色（如卖货助手、闲聊伙伴），并能在前端切换。
2.  **高质量语音合成 (TTS)**：
    *   从浏览器原生 `SpeechSynthesis` API 升级至**阿里云 DashScope Qwen-TTS API**。
    *   后端负责调用 DashScope API，下载音频并 Base64 编码，前端使用 Web Audio API 播放，实现自然、富有感情的 AI 语音输出。
3.  **动态头像动画**：
    *   将头像替换为 SVG (`duck_avatar.svg`)，实现了后端驱动的**情绪 (mood)** 标签。
    *   前端根据 AI 情绪和“说话”状态，通过 CSS `transform` 对头像进行整体动态动画，增强视觉表现力。
4.  **前端可视化配置**：
    *   开发了用户友好的**配置编辑器 (`ConfigEditorView.vue`)**，可直观地管理 AI 全局设置、角色定义和关键词配置，支持增删改查、筛选和搜索。
    *   AI 回复显示时，会展示所回复的**原始弹幕内容**，增强上下文理解。

## 技术栈
*   **dycast 前端：** Vue.js / TypeScript, SVG
*   **AI 后端：** Python 3, `websockets`, `openai`, `requests`, `dashscope`, `re`, `wave`
*   **AI 服务：** DeepSeek API, 阿里云 DashScope Qwen-TTS API

---
**Gemini CLI 指令记录 (关键操作):**
*   `pip install websockets openai requests dashscope`
*   运行后端：`python ai_backend.py` (需输入 DeepSeek API Key 和 DashScope API Key)
*   dycast 前端转发地址：`ws://localhost:8080`
*   前端 AI 助手页面：`http://localhost:XXXX/#/ai` (XXXX 为前端端口)
*   前端配置编辑器：`http://localhost:XXXX/#/config` (XXXX 为前端端口)

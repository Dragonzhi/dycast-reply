# dycast 项目 - Gemini 会话历史记录

## 项目概览
本项目是在现有“dycast 抖音弹幕姬”的基础上进行的开发。
dycast 项目核心功能：实时监听抖音直播间弹幕，并支持将弹幕数据转发到自定义后端服务。

## 本次会话目标
为 dycast 项目增加一个 AI 交互功能：检索弹幕关键词，并触发 AI 回复。

## 实现架构
采用分离式架构，不直接修改 dycast 核心代码，而是利用其弹幕转发功能：
1.  **dycast 前端：** 负责监听直播间弹幕，并将弹幕消息通过 WebSocket 转发到我们自建的后端服务。
2.  **AI 后端服务 (`ai_backend.py`)：**
    *   使用 Python 编写，基于 `websockets` 库。
    *   监听 `ws://localhost:8080` 端口。
    *   接收来自 dycast 前端转发的 JSON 格式弹幕消息。
    *   对消息内容进行关键词检测（当前关键词列表：["测试", "你好", "AI", "关键词"]）。
    *   如果检测到关键词，则调用 DeepSeek AI API 获取回复。
    *   AI 角色设定：“直播间助手，名字叫“弹幕鸭”，以友好、简洁、幽默的风格回答问题。”
    *   AI 回复目前打印在后端服务的终端中。
    *   **API 密钥管理：** 为提高安全性，DeepSeek API 密钥在后端服务启动时手动输入。

## 技术栈
*   **dycast 前端：** Vue.js / TypeScript (现有项目)
*   **AI 后端：** Python 3, `websockets`, `openai` 库
*   **AI 服务：** DeepSeek API (`https://api.deepseek.com/v1`, 模型：`deepseek-chat`)

## 已完成工作
1.  确认了 dycast 项目的弹幕处理流程和转发机制。
2.  开发并测试了独立的 Python WebSocket 后端服务 `ai_backend.py`，能够接收 dycast 转发的弹幕。
3.  在 `ai_backend.py` 中实现了关键词检测功能，并在检测到关键词时向 DeepSeek AI 发送请求。
4.  成功集成了 DeepSeek AI API，能在后端终端打印 AI 的回复。
5.  优化了 API 密钥管理方式，改为每次运行后端时手动输入。

## 后续方向
下一步计划是在 dycast 前端 (`src/views/IndexView.vue` 等) 实现对 AI 回复消息的接收和展示，使其能够像普通弹幕一样显示在直播间列表中，从而让 AI 回复在 UI 上可见。

---
**Gemini CLI 指令记录：**
*   `pip install websockets`
*   `pip install openai`
*   运行后端：`python ai_backend.py` (输入 DeepSeek API Key)
*   dycast 前端转发地址：`ws://localhost:8080`

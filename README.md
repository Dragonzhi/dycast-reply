# 抖音直播间弹幕鸭 - AI 互动版 (基于 dycast 二次开发)

<p align=center>
  <a href="https://github.com/skmcj/dycast">
    <img src="https://gcore.jsdelivr.net/gh/skmcj/pic-bed/common/dydm-bg-logo.png" alt="抖音弹幕姬" style="width: 200px">
  </a>
</p>

<p align=center style="font-weight: bold;">
   抖音直播间弹幕鸭 - AI 互动版
</p>

## 简介

本项目是基于 [skmcj/dycast](https://github.com/skmcj/dycast) 项目的**独立二次开发版本**，旨在为抖音直播间引入智能 AI 互动能力。

它不仅保留了 `dycast` 原有的实时获取、解析和转发抖音弹幕的核心功能，更在此基础上集成了 AI 回复、个性化角色设定、高质量语音合成和动态头像动画，将弹幕姬升级为一个能与直播间观众实时语音互动的智能助手——**弹幕鸭**。

特别适合作为直播带货、娱乐互动等场景的智能辅助工具。

## 核心功能与特色

-   **智能 AI 回复**：
    *   集成 DeepSeek AI API，实现智能问答和互动。
    *   支持**关键词触发模式**：根据弹幕内容中的特定关键词，触发 AI 进行回复。
        *   可配置关键词，为每个关键词设置 AI 指示 (`ai_context`)、回复模板 (`response_template`) 和结构化信息（如商品名称、价格、购买方式）。
        *   AI 能智能组合多个关键词的信息，提供更精准和个性化的回复（例如，同时识别“红富士”和“多少钱”，并给出组合回答）。
    *   支持**自由问答模式**：AI 会尝试回复所有（通过过滤的）弹幕，作为直播间的小助手。
    *   **弹幕过滤**：在自由问答模式下，可配置过滤规则（最小长度、无意义模式等），避免回复无效或刷屏弹幕。
-   **灵活的角色人设 (Persona)**：
    *   在前端提供配置界面，可定义多个 AI 角色（例如“卖货助手”、“闲聊伙伴”、“技术支持”）。
    *   每个角色拥有独立的 `response_mode`（响应模式）、`persona_prompt`（人设提示）、过滤规则等。
    *   用户可根据直播场景，一键切换弹幕鸭的当前角色，让 AI 行为更专注、更符合直播主题。
-   **高质量语音合成 (TTS)**：
    *   接入**阿里云 DashScope Qwen-TTS API**，提供自然、富有感情的 AI 语音输出。
    *   AI 后端负责调用 DashScope API，下载生成的音频数据（WAV 格式），并将其 Base64 编码后通过 WebSocket 传递给前端。
    *   前端使用 Web Audio API 进行播放，彻底取代了浏览器原生的生硬语音合成。
-   **动态头像动画**：
    *   弹幕鸭头像 (`duck_avatar.svg`) 会根据 AI 的“说话”状态和 AI 判断的**情绪 (mood)** 标签（例如 `[happy]`, `[selling]`, `[confused]`），通过 CSS `transform` 实现整体的上下、左右晃动和旋转等动画效果，增强视觉表现力。
    *   头像保持圆形，并具备高亮边框和阴影效果。
-   **前端可视化配置工具**：
    *   提供一个用户友好的配置编辑界面 (`ConfigEditorView.vue`)。
    *   采用表单式设计，支持对 AI 通用设置和所有角色、关键词进行直观的增删改查。
    *   关键词配置支持按类型筛选和文本搜索功能，方便管理大量关键词。
-   **上下文显示**：在 AI 回复的旁边或上方，清晰地显示触发该回复的原始弹幕内容和用户名，帮助用户理解对话上下文。

## 实现原理

本项目基于 `dycast` 的核心连接与弹幕解析机制，在此基础上扩展了独立的 Python WebSocket 后端服务和 Vue.js 前端界面。

### 弹幕获取与解析

-   **计算抖音弹幕的 `wss` 链接**：沿用 `dycast` 的逆向工程技术，通过 `roomId` 与 `uniqueId` 计算出 `signature` 参数，构建完整的 `wss` 链接。
-   **解析弹幕数据**：通过 `protobuf` 协议与预编译的 `proto` 文件（主要为 `ts` 文件，通过 `protobufjs` 编译），解析接收到的二进制弹幕数据，提取 `ChatMessage`、`GiftMessage` 等具体消息体。

### AI 后端服务

-   **DeepSeek AI API 集成**：使用 `openai` 库调用 DeepSeek Chat API，进行核心的文本生成。
-   **DashScope Qwen-TTS API 集成**：使用 `requests` 和 `dashscope` SDK 调用阿里云 DashScope Qwen-TTS API，将 AI 生成的文本转换为高质量语音。后端会从 API 返回的 URL 下载音频，并 Base64 编码后传输。
-   **WebSocket 通信**：前端与后端通过 WebSocket 进行通信，实时传输弹幕数据和 AI 回复（包含文本、情绪标签、Base64 编码音频及原始弹幕信息）。

## 数据结构 (AI 后端与前端通信)

后端发送给前端的 AI 回复消息 (`type: 'ai_response'`) 结构如下：

```json
{
  "type": "ai_response",
  "content": "AI 生成的文本回复",
  "mood": "happy", // AI判断的情绪标签，用于前端动画
  "original_comment": {
    "user_name": "用户昵称",
    "text": "原始弹幕内容"
  },
  "audio_base64": "Base64 编码的 WAV 音频数据",
  "sampling_rate": 16000 // 音频采样率
}
```

## 项目预览

完整项目演示，请移步[哔哩哔哩](https://www.bilibili.com/video/BV1Vj411c7FF/) (此链接为 `dycast` 原始项目，AI 互动版功能请自行体验)

- 项目运行后，具体界面展示如下 (原始 `dycast` 界面，AI 互动功能可在 `#/ai` 页面和配置页面 `#/config` 体验)

  ![主界面](https://static.ltgcm.top/md/20250428180514.png)

- 在右侧房间号输入框输入房间号后，点击**连接**，等待几秒后，会在左下方状态信息展示连接结果，连接成功后，弹幕数据会流向 AI 后端。

- 访问 `http://localhost:XXXX/#/ai` (XXXX 为前端端口) 可查看 AI 互动助手页面。
- 访问 `http://localhost:XXXX/#/config` (XXXX 为前端端口) 可配置 AI 助手行为。

## 部署运行

### 后端 (`ai_backend.py`)

1.  **安装依赖：**
    ```sh
    pip install websockets openai requests dashscope
    ```
2.  **运行：**
    ```sh
    python ai_backend.py
    ```
    *   程序会提示您输入 DeepSeek API Key 和 DashScope API Key。
    *   首次运行可能会下载 DashScope SDK 相关的模型文件。

### 前端 (Vue.js)

1.  **项目依赖安装：**
    ```sh
    npm install
    ```
2.  **项目运行：**
    ```sh
    npm run dev
    ```
    *   前端通常会在 `http://localhost:5173` 启动。

### 配置文件说明 (`keywords_config.json`)

此文件用于配置 AI 助手的行为，包括全局 AI 设置（如角色管理）和关键词响应规则。

**文件示例结构：**

```json
{
    "ai_settings": {
        "current_persona": "live_selling_assistant",
        "personas": {
            "live_selling_assistant": {
                "name": "卖货助手",
                "response_mode": "keyword",
                "persona_prompt": "你是一个专业的直播带货助手，名字叫弹幕鸭。你的任务是积极、热情地回答用户关于商品的所有问题，引导他们下单，并主动介绍商品亮点和优惠活动。你的语气要充满活力和说服力。",
                "filtering_enabled": true,
                "min_message_length": 4,
                "meaningless_patterns": [
                    "哈哈", "hhh", "么么哒", "谢谢", "谢谢主播", "1", "2", "3", "6", "8", "666", "888", "哈哈哈",
                    "qwq", "awa", "oao", "owo", "uwu", "qvq", "qaq", "www", "zzz", "kkk", "???", "！！", "。。",
                    "？", "！", "。", "~", "…", "❤️", "👍", "😁", "😂", "🤣", "😭", "😊", "🙏", "🔥", "🚀", "🎉",
                    "👍", "🌹", "🎁", "🎈", "🎊", "🥳", "✨", "💫", "⭐", "🌟", "✨", "🍀", "🌸", "💖", "💕", "💞",
                    "💜", "🧡", "💛", "💚", "💙", "🤎", "🖤", "🤍", "♥️", "💋", "💯", "🎉", "💰", "🧧"
                ]
            },
            "friendly_chatter": {
                "name": "闲聊伙伴",
                "response_mode": "free_qa",
                "persona_prompt": "你是一个直播间的好朋友，名字叫弹幕鸭。请专注于与用户进行轻松愉快的闲聊，分享有趣的故事，或者对他们的评论做出幽默的回应，避免过多推销商品。",
                "filtering_enabled": true,
                "min_message_length": 4,
                "meaningless_patterns": [
                    "哈哈", "hhh", "么么哒", "谢谢", "谢谢主播", "1", "2", "3", "6", "8", "666", "888", "哈哈哈",
                    "qwq", "awa", "oao", "owo", "uwu", "qvq", "qaq", "www", "zzz", "kkk", "???", "！！", "。。",
                    "？", "！", "。", "~", "…", "❤️", "👍", "😁", "😂", "🤣", "😭", "😊", "🙏", "🔥", "🚀", "🎉",
                    "👍", "🌹", "🎁", "🎈", "🎊", "🥳", "✨", "💫", "⭐", "🌟", "✨", "🍀", "🌸", "💖", "💕", "💞",
                    "💜", "🧡", "💛", "💚", "💙", "🤎", "🖤", "🤍", "♥️", "💋", "💯", "🎉", "💰", "🧧"
                ]
            }
        }
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
*   `pip install websockets openai requests dashscope`
*   运行后端：`python ai_backend.py` (输入 DeepSeek API Key 和 DashScope API Key)
*   dycast 前端转发地址：`ws://localhost:8080`

## 部署到`nginx`

```nginx
# 配置网络监听
server {
    # 监听端口号，如：1234
    listen       1234;
    # 监听地址，可以是域名或ip地址，可正则书写
    server_name  localhost;

    location / {
        add_header Access-Control-Allow-Origin *;
        # 根目录，即项目打包内容位置(···/dist)，可以是项目的本地路径
        root   /var/dycast;
        # 配置默认主页文件
        index  index.html index.htm;
        # 配置单页面应用刷新问题，默认返回主页
        try_files $uri $uri/ /index.html;
    }
    
    # 配置接口跨域
    location /dylive {
        # proxy_pass 你要跨域的的接口地址
        proxy_pass https://live.douyin.com/;

        # 响应头大小
        proxy_buffer_size 64k;
        # 响应体大小 = 数量 * size
        proxy_buffers   32 64k;
        # 处于busy状态的buffer大小，一般为 proxy_buffer_size * 2
        proxy_busy_buffers_size 128k;

        # 修改请求头
        proxy_set_header Host live.douyin.com;
        proxy_set_header Referer 'https://live.douyin.com/';
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        # 如果需要配置移动端打开也能用
        # 需设置请求头 User-Agent，伪装 PC 端 UA，防止移动端重定向
        set $ua $http_user_agent;
        if ($http_user_agent ~* "(iphone|ipad|android|mobile)") {
            set $ua "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36 Edg/136.0.0.0";
        }
        proxy_set_header User-Agent $ua;

        # 处理响应 Set-Cookie
        # 确保 Set-Cookie 能正常设置到当前域下
        # 清空 Domain
        proxy_cookie_domain ~.* $host;
        # 统一 Path
        proxy_cookie_path / /;
        
        # 清除 SameSite / Secure
        # 不一定都需要设置，某些浏览器需要
        # 可借助 ngx_headers_more 模块实现

        # 确保 Set-Cookie 被转发到客户端
        proxy_pass_header Set-Cookie;
        

        # 重写路径 - 移除/dylive前缀
        rewrite ^/dylive/(.*) /$1 break;
    }
    
    location /socket {
        # Nginx 不区分 ws / wss 协议
        # WebSocket 实际上是通过 HTTP 升级实现的
        # 故使用 https:// 非 wss://
        proxy_pass https://webcast5-ws-web-lf.douyin.com/;

        # WebSocket 关键配置
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # 跨域相关头
        proxy_set_header Origin https://live.douyin.com;
        proxy_set_header Host webcast5-ws-web-lf.douyin.com;

        # 可选：保留 Cookie 头，用于认证
        proxy_set_header Cookie $http_cookie;
        
        set $ua $http_user_agent;
        if ($http_user_agent ~* "(iphone|ipad|android|mobile)") {
            set $ua "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36 Edg/136.0.0.0";
        }
        proxy_set_header User-Agent $ua;

        # 重写路径 - 移除/socket
        rewrite ^/socket/(.*) /$1 break;
    }

}
```

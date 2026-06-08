from __future__ import annotations

import os
from pathlib import Path

import requests
from flask import Flask, Response, send_from_directory, render_template_string, request


def create_flask_ui(api_base_url: str) -> Flask:
    app = Flask(__name__)
    
    # 获取frontend目录的路径
    frontend_dir = Path(__file__).resolve().parent.parent / "frontend"

    @app.get("/")
    def index() -> Response:
        # 检查是否存在Vue应用
        vue_index = frontend_dir / "index.html"
        if vue_index.exists():
            html = vue_index.read_text(encoding="utf-8")
            # 注入 API_BASE 为空，走同源 Flask 代理，消除跨域
            html = html.replace(
                '<script type="module">',
                f'<script>window.API_BASE = "";</script>\n<script type="module">'
            )
            return Response(html, content_type="text/html; charset=utf-8")
        
        # 如果没有Vue应用，返回原始HTML
        html = r"""
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>ZX AI Advisor — 智能报考顾问系统</title>
  <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>&#x1f393;</text></svg>" />
  <style>
    /* ======== Reset & Base ======== */
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    :root {
      --primary: #1e3a5f;
      --primary-light: #2d5a8e;
      --gold: #f0a500;
      --gold-light: #ffc940;
      --danger: #e74c3c;
      --danger-light: #ff6b6b;
      --success: #27ae60;
      --bg: #f0f4f8;
      --card: #ffffff;
      --border: #e2e8f0;
      --text: #1a202c;
      --text-muted: #718096;
      --radius: 12px;
      --shadow: 0 1px 3px rgba(0,0,0,.06), 0 1px 2px rgba(0,0,0,.04);
      --shadow-lg: 0 10px 25px -5px rgba(0,0,0,.08), 0 4px 10px -2px rgba(0,0,0,.04);
      --transition: 0.2s cubic-bezier(.4,0,.2,1);
    }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
      line-height: 1.6;
    }

    /* ======== Header ======== */
    .header {
      background: linear-gradient(135deg, var(--primary) 0%, #1a3650 100%);
      color: #fff;
      padding: 14px 28px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      box-shadow: 0 2px 8px rgba(0,0,0,.15);
      position: sticky;
      top: 0;
      z-index: 100;
    }
    .header .brand {
      display: flex;
      align-items: center;
      gap: 12px;
      font-size: 20px;
      font-weight: 700;
      letter-spacing: .5px;
    }
    .header .brand .icon {
      width: 36px;
      height: 36px;
      background: var(--gold);
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 20px;
      color: var(--primary);
    }
    .header .service-dots {
      display: flex;
      gap: 16px;
      font-size: 13px;
    }
    .header .dot {
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .header .dot::before {
      content: "";
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--success);
    }
    .header .dot.warn::before { background: var(--gold); }
    .header .dot.off::before { background: var(--danger-light); }

    /* ======== Layout ======== */
    .app-layout {
      display: flex;
      height: calc(100vh - 64px);
    }
    .main-area {
      flex: 1;
      display: flex;
      flex-direction: column;
      min-width: 0;
    }
    .side-panel {
      width: 320px;
      border-left: 1px solid var(--border);
      background: var(--card);
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      flex-shrink: 0;
    }

    /* ======== Chat Area ======== */
    .chat-container {
      flex: 1;
      overflow-y: auto;
      padding: 20px 28px;
      display: flex;
      flex-direction: column;
      gap: 16px;
      background: linear-gradient(180deg, #f7fafc 0%, var(--bg) 100%);
    }
    .chat-welcome {
      text-align: center;
      padding: 40px 20px 20px;
    }
    .chat-welcome .big-icon {
      font-size: 56px;
      margin-bottom: 12px;
      filter: drop-shadow(0 4px 6px rgba(0,0,0,.1));
    }
    .chat-welcome h2 {
      font-size: 22px;
      font-weight: 700;
      color: var(--primary);
      margin-bottom: 4px;
    }
    .chat-welcome p {
      color: var(--text-muted);
      font-size: 14px;
      max-width: 420px;
      margin: 0 auto 16px;
    }
    .quick-chips {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      justify-content: center;
      max-width: 520px;
      margin: 0 auto;
    }
    .chip {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 20px;
      padding: 6px 16px;
      font-size: 13px;
      cursor: pointer;
      transition: var(--transition);
      color: var(--text);
      white-space: nowrap;
    }
    .chip:hover {
      background: var(--primary);
      color: #fff;
      border-color: var(--primary);
      transform: translateY(-1px);
    }

    .msg-row {
      display: flex;
      gap: 10px;
      animation: fadeInUp .25s ease;
    }
    @keyframes fadeInUp {
      from { opacity: 0; transform: translateY(12px); }
      to { opacity: 1; transform: translateY(0); }
    }
    .msg-row.user { justify-content: flex-end; }
    .msg-row.assistant { justify-content: flex-start; }

    .msg-avatar {
      width: 36px;
      height: 36px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 16px;
      flex-shrink: 0;
    }
    .msg-row.user .msg-avatar {
      background: var(--primary-light);
      color: #fff;
      order: 2;
    }
    .msg-row.assistant .msg-avatar {
      background: linear-gradient(135deg, var(--gold) 0%, var(--gold-light) 100%);
      color: var(--primary);
    }

    .msg-bubble {
      max-width: 72%;
      padding: 12px 16px;
      border-radius: 16px;
      font-size: 14px;
      line-height: 1.65;
      word-break: break-word;
    }
    .msg-row.user .msg-bubble {
      background: linear-gradient(135deg, #e8f0fe 0%, #d4e4fc 100%);
      border-bottom-right-radius: 4px;
    }
    .msg-row.assistant .msg-bubble {
      background: var(--card);
      border: 1px solid var(--border);
      border-bottom-left-radius: 4px;
      box-shadow: var(--shadow);
    }
    .msg-bubble .status-tag {
      display: inline-block;
      padding: 1px 8px;
      border-radius: 10px;
      font-size: 12px;
      color: #fff;
      margin: 4px 0;
    }
    .msg-time {
      font-size: 11px;
      color: var(--text-muted);
      margin-top: 4px;
      padding: 0 4px;
    }
    .msg-row.user .msg-time { text-align: right; }

    /* typing indicator */
    .typing-dots {
      display: flex;
      gap: 4px;
      padding: 4px 0;
    }
    .typing-dots span {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: var(--text-muted);
      animation: typingBounce 1.4s infinite ease-in-out both;
    }
    .typing-dots span:nth-child(1) { animation-delay: 0s; }
    .typing-dots span:nth-child(2) { animation-delay: .16s; }
    .typing-dots span:nth-child(3) { animation-delay: .32s; }
    @keyframes typingBounce {
      0%, 80%, 100% { transform: scale(.6); opacity: .4; }
      40% { transform: scale(1); opacity: 1; }
    }

    /* ======== Input Area ======== */
    .input-area {
      padding: 14px 28px;
      background: var(--card);
      border-top: 1px solid var(--border);
      display: flex;
      gap: 10px;
      align-items: flex-end;
    }
    .input-area textarea {
      flex: 1;
      resize: none;
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 10px 14px;
      font-size: 14px;
      font-family: inherit;
      line-height: 1.5;
      min-height: 44px;
      max-height: 120px;
      transition: var(--transition);
      outline: none;
    }
    .input-area textarea:focus {
      border-color: var(--primary-light);
      box-shadow: 0 0 0 3px rgba(30,58,95,.12);
    }
    .input-area button {
      background: linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%);
      color: #fff;
      border: none;
      border-radius: var(--radius);
      padding: 10px 24px;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
      transition: var(--transition);
      white-space: nowrap;
      display: flex;
      align-items: center;
      gap: 6px;
      flex-shrink: 0;
    }
    .input-area button:hover:not(:disabled) {
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(30,58,95,.3);
    }
    .input-area button:disabled {
      opacity: .5;
      cursor: not-allowed;
    }

    /* ======== Side Panel ======== */
    .side-panel .section {
      padding: 16px 20px;
      border-bottom: 1px solid var(--border);
    }
    .side-panel .section h4 {
      font-size: 13px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: .8px;
      color: var(--text-muted);
      margin-bottom: 10px;
    }
    .status-grid {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }
    .status-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 13px;
      padding: 6px 10px;
      border-radius: 8px;
      background: var(--bg);
    }
    .status-row .ind {
      width: 8px;
      height: 8px;
      border-radius: 50%;
    }
    .status-row .ind.green { background: var(--success); }
    .status-row .ind.yellow { background: var(--gold); }
    .status-row .ind.red { background: var(--danger-light); }

    .profile-card {
      background: linear-gradient(135deg, #f7fafc 0%, #edf2f7 100%);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 14px;
    }
    .profile-card .field {
      display: flex;
      justify-content: space-between;
      font-size: 13px;
      padding: 3px 0;
    }
    .profile-card .field .k { color: var(--text-muted); }
    .profile-card .field .v { font-weight: 600; color: var(--text); }
    .profile-card .empty { color: var(--text-muted); font-size: 13px; font-style: italic; }

    .tip-box {
      background: #fffbeb;
      border: 1px solid #fde68a;
      border-radius: var(--radius);
      padding: 12px;
      font-size: 13px;
      color: #92400e;
      line-height: 1.5;
    }

    .session-counter {
      text-align: center;
      padding: 8px;
      font-size: 11px;
      color: var(--text-muted);
    }
    .reset-btn {
      width: 100%;
      background: none;
      border: 1px dashed var(--border);
      border-radius: var(--radius);
      padding: 8px;
      font-size: 12px;
      color: var(--text-muted);
      cursor: pointer;
      transition: var(--transition);
    }
    .reset-btn:hover {
      border-color: var(--danger);
      color: var(--danger);
    }

    /* ======== Responsive ======== */
    @media (max-width: 768px) {
      .app-layout { flex-direction: column; }
      .side-panel { width: 100%; max-height: 200px; border-left: none; border-top: 1px solid var(--border); }
      .main-area { height: auto; }
      .chat-container { padding: 12px 14px; }
      .input-area { padding: 10px 14px; }
      .msg-bubble { max-width: 88%; }
      .header { padding: 10px 14px; }
      .header .brand { font-size: 16px; }
    }

    /* Scrollbar */
    ::-webkit-scrollbar { width: 5px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 3px; }

    .hidden { display: none !important; }
  </style>
</head>
<body>
  <!-- ======== Header ======== -->
  <header class="header">
    <div class="brand">
      <div class="icon">&#x1f393;</div>
      <span>ZX AI Advisor</span>
    </div>
    <div class="service-dots" id="service-dots">
      <span class="dot" id="dot-graph">Graph</span>
      <span class="dot" id="dot-db">DB</span>
      <span class="dot" id="dot-redis">Redis</span>
      <span class="dot" id="dot-vector">Vector</span>
    </div>
  </header>

  <!-- ======== App Layout ======== -->
  <div class="app-layout">
    <!-- Main Chat Area -->
    <div class="main-area">
      <div class="chat-container" id="chat-container">
        <!-- Welcome -->
        <div class="chat-welcome" id="chat-welcome">
          <div class="big-icon">&#x1f4da;</div>
          <h2>你好，我是张雪峰风格的报考顾问</h2>
          <p>基于十万级录取数据 + AI 智能分析，为你提供个性化志愿填报建议</p>
          <div class="quick-chips">
            <span class="chip" data-query="我位次32000，推荐广东可冲稳保院校">&#x1f3af; 位次选校</span>
            <span class="chip" data-query="计算机科学与技术就业前景怎么样">&#x1f4bc; 就业分析</span>
            <span class="chip" data-query="帮我搜一下2026年最新招生政策">&#x1f50d; 政策查询</span>
            <span class="chip" data-query="临床医学和电子信息哪个更有前途">&#x2696; 专业对比</span>
            <span class="chip" data-query="理科580分，想去江苏读计算机">&#x1f4ca; 分数匹配</span>
            <span class="chip" data-query="家里条件不好该不该考研">&#x1f4ad; 人生规划</span>
          </div>
        </div>
      </div>

      <!-- Input -->
      <div class="input-area">
        <textarea id="query-input" placeholder="输入你的问题，如：广东省物理类580分，想去江浙沪读计算机..."
          rows="1" onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();sendMessage();}"></textarea>
        <button id="send-btn" onclick="sendMessage()">
          <span id="send-icon">&#x27a4;</span>
          <span id="send-text">发送</span>
        </button>
      </div>
    </div>

    <!-- Side Panel -->
    <aside class="side-panel" id="side-panel">
      <div class="section">
        <h4>&#x1f4ca; 服务状态</h4>
        <div class="status-grid" id="status-grid">
          <div class="status-row"><span>Graph 引擎</span><span class="ind" id="ind-graph"></span></div>
          <div class="status-row"><span>数据库</span><span class="ind" id="ind-db"></span></div>
          <div class="status-row"><span>Redis</span><span class="ind" id="ind-redis"></span></div>
          <div class="status-row"><span>向量库</span><span class="ind" id="ind-vector"></span></div>
          <div class="status-row"><span>RAG 索引</span><span class="ind" id="ind-rag"></span></div>
        </div>
        <div style="margin-top:8px;font-size:11px;color:var(--text-muted);" id="uptime-text"></div>
      </div>

      <div class="section">
        <h4>&#x1f464; 用户画像</h4>
        <div class="profile-card" id="profile-card">
          <div class="empty">对话开始后自动采集...</div>
        </div>
      </div>

      <div class="section">
        <h4>&#x1f4ac; 会话</h4>
        <div class="session-counter">已交换 <strong id="msg-count">0</strong> 条消息</div>
        <button class="reset-btn" onclick="clearChat()">&#x1f5d1; 清空对话</button>
      </div>

      <div class="section">
        <div class="tip-box">
          <strong>&#x1f4a1; 提示：</strong>提供省份、选科、分数/位次、目标专业，可获得更精准的报考建议。
        </div>
      </div>
    </aside>
  </div>

  <script>
    var API_BASE = {{ api_base_url | tojson }};
    var chatContainer = document.getElementById("chat-container");
    var queryInput = document.getElementById("query-input");
    var sendBtn = document.getElementById("send-btn");
    var sendIcon = document.getElementById("send-icon");
    var sendText = document.getElementById("send-text");
    var msgCountEl = document.getElementById("msg-count");
    var uptimeText = document.getElementById("uptime-text");
    var msgCount = 0;
    var profileData = {};

    // ======== Init ========
    refreshStatus();
    autoResizeTextarea();

    // ======== Service Status ========
    async function refreshStatus() {
      try {
        var res = await fetch(API_BASE + "/status");
        var d = await res.json();
        setDot("ind-graph", "dot-graph", d.graph_ready);
        setDot("ind-db", "dot-db", d.db_ready);
        setDot("ind-redis", "dot-redis", d.redis_ready);
        setDot("ind-vector", "dot-vector", d.vector_ready);
        setDot("ind-rag", null, d.rag_index_exists);
        var mins = Math.floor(d.uptime_seconds / 60);
        uptimeText.textContent = "运行时间: " + (mins < 1 ? "<1分钟" : mins + "分钟");
      } catch (e) {
        ["ind-graph","ind-db","ind-redis","ind-vector"].forEach(function(id){ setDot(id, null, false); });
      }
    }

    function setDot(indId, headerDotId, ok) {
      var el = document.getElementById(indId);
      if (el) { el.className = "ind " + (ok ? "green" : "red"); }
      if (headerDotId) {
        var hd = document.getElementById(headerDotId);
        if (hd) { hd.className = "dot" + (ok ? "" : " off"); }
      }
    }

    // ======== Chat ========
    function addMessage(role, contentOrEl) {
      var welcome = document.getElementById("chat-welcome");
      if (welcome) welcome.classList.add("hidden");

      var row = document.createElement("div");
      row.className = "msg-row " + role;
      var avatar = document.createElement("div");
      avatar.className = "msg-avatar";
      avatar.innerHTML = role === "user" ? "&#x1f464;" : "&#x1f393;";
      var bubble = document.createElement("div");
      bubble.className = "msg-bubble";

      if (typeof contentOrEl === "string") {
        bubble.textContent = contentOrEl;
      } else {
        bubble.appendChild(contentOrEl);
      }

      var time = document.createElement("div");
      time.className = "msg-time";
      time.textContent = new Date().toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });

      if (role === "user") {
        row.appendChild(time);
        row.appendChild(bubble);
        row.appendChild(avatar);
      } else {
        row.appendChild(avatar);
        row.appendChild(bubble);
        row.appendChild(time);
      }

      chatContainer.appendChild(row);
      chatContainer.scrollTop = chatContainer.scrollHeight;
      msgCount++;
      msgCountEl.textContent = msgCount;
      return bubble;
    }

    function addTypingIndicator() {
      var row = document.createElement("div");
      row.className = "msg-row assistant";
      row.id = "typing-row";
      var avatar = document.createElement("div");
      avatar.className = "msg-avatar";
      avatar.innerHTML = "&#x1f393;";
      var bubble = document.createElement("div");
      bubble.className = "msg-bubble";
      var dots = document.createElement("div");
      dots.className = "typing-dots";
      dots.innerHTML = "<span></span><span></span><span></span>";
      bubble.appendChild(dots);
      row.appendChild(avatar);
      row.appendChild(bubble);
      chatContainer.appendChild(row);
      chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    function removeTypingIndicator() {
      var el = document.getElementById("typing-row");
      if (el) el.remove();
    }

    // ======== Send Message ========
    async function sendMessage() {
      var query = queryInput.value.trim();
      if (!query) return;
      queryInput.value = "";
      autoResizeTextarea();
      setSending(true);

      addMessage("user", query);
      addTypingIndicator();

      try {
        var response = await fetch(API_BASE + "/stream/advice", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query: query })
        });
        if (!response.ok || !response.body) {
          removeTypingIndicator();
          addMessage("assistant", "请求失败 (HTTP " + response.status + ")，请确认后端服务已启动。");
          setSending(false);
          return;
        }

        removeTypingIndicator();
        var bubble = addMessage("assistant", "");
        bubble.textContent = "";

        var reader = response.body.getReader();
        var decoder = new TextDecoder("utf-8");
        var buffer = "";

        while (true) {
          var r = await reader.read();
          if (r.done) break;
          buffer += decoder.decode(r.value, { stream: true });
          buffer = buffer.replace(/\r\n/g, "\n");
          var blocks = buffer.split("\n\n");
          buffer = blocks.pop() || "";

          for (var i = 0; i < blocks.length; i++) {
            var payload = tryParseSSE(blocks[i]);
            if (!payload) continue;
            try {
              var data = JSON.parse(payload);
              if (data.type === "token") {
                bubble.textContent += data.msg;
                chatContainer.scrollTop = chatContainer.scrollHeight;
              }
              if (data.type === "status") {
                var tag = document.createElement("span");
                tag.className = "status-tag";
                tag.style.background = "var(--primary-light)";
                tag.textContent = data.msg;
                bubble.appendChild(tag);
              }
              if (data.type === "profile_update" && data.profile) {
                profileData = data.profile;
                updateProfileCard();
              }
            } catch (e) {
              bubble.textContent += payload;
            }
          }
        }

        if (buffer.trim()) {
          var payload = tryParseSSE(buffer);
          if (payload) {
            try {
              var data = JSON.parse(payload);
              if (data.type === "token") {
                bubble.textContent += data.msg;
              }
              if (data.type === "status") {
                var tag = document.createElement("span");
                tag.className = "status-tag";
                tag.style.background = "var(--primary-light)";
                tag.textContent = data.msg;
                bubble.appendChild(tag);
              }
            } catch (e) {}
          }
        }
      } catch (err) {
        removeTypingIndicator();
        addMessage("assistant", "连接异常: " + err.message);
      } finally {
        setSending(false);
        refreshStatus();
      }
    }

    function tryParseSSE(block) {
      var lines = block.split("\n");
      for (var i = 0; i < lines.length; i++) {
        if (lines[i].startsWith("data:")) return lines[i].slice(5).trim();
      }
      return null;
    }

    function setSending(v) {
      sendBtn.disabled = v;
      sendIcon.textContent = v ? "\u23f3" : "\u27a4";
      sendText.textContent = v ? "分析中..." : "发送";
      if (v) sendBtn.style.background = "var(--text-muted)";
      else sendBtn.style.background = "";
    }

    // ======== Profile Card ========
    function updateProfileCard() {
      var card = document.getElementById("profile-card");
      var keys = [
        { k: "省份", f: "province" },
        { k: "选科", f: "subject_type" },
        { k: "专业", f: "major_name" },
        { k: "分数", f: "score" },
        { k: "位次", f: "rank" },
        { k: "目标城市", f: "target_city" },
        { k: "预算", f: "budget" },
      ];
      var hasAny = false;
      var html = "";
      for (var i = 0; i < keys.length; i++) {
        if (profileData[keys[i].f]) { hasAny = true; break; }
      }
      if (!hasAny) {
        card.innerHTML = '<div class="empty">对话开始后自动采集...</div>';
        return;
      }
      for (var i = 0; i < keys.length; i++) {
        var val = profileData[keys[i].f];
        if (!val) continue;
        if (keys[i].f === "budget") val = (val / 10000).toFixed(1) + "万";
        html += '<div class="field"><span class="k">' + keys[i].k + '</span><span class="v">' + val + '</span></div>';
      }
      card.innerHTML = html;
    }

    // ======== Clear ========
    function clearChat() {
      document.getElementById("chat-container").innerHTML = "";
      msgCount = 0;
      msgCountEl.textContent = "0";
      profileData = {};
      updateProfileCard();
    }

    // ======== Textarea Auto-resize ========
    function autoResizeTextarea() {
      var ta = queryInput;
      ta.style.height = "auto";
      ta.style.height = Math.min(ta.scrollHeight, 120) + "px";
    }
    queryInput.addEventListener("input", autoResizeTextarea);

    // ======== Quick Chips ========
    document.querySelectorAll(".chip").forEach(function(chip) {
      chip.addEventListener("click", function() {
        queryInput.value = this.getAttribute("data-query");
        sendMessage();
      });
    });

    // ======== Periodic Status Refresh ========
    setInterval(refreshStatus, 30000);
  </script>
</body>
</html>
"""
        return render_template_string(html, api_base_url=api_base_url)

    @app.route('/assets/<path:filename>')
    def serve_assets(filename):
        return send_from_directory(str(frontend_dir / "assets"), filename)

    @app.route('/components/<path:filename>')
    def serve_components(filename):
        return send_from_directory(str(frontend_dir / "components"), filename)

    @app.route('/status')
    def proxy_status():
        """代理 /status 到 FastAPI"""
        try:
            resp = requests.get(f"{api_base_url}/status", timeout=10)
            return resp.content, resp.status_code, {'Content-Type': 'application/json'}
        except Exception:
            return '{"ok":false}', 502, {'Content-Type': 'application/json'}

    @app.route('/stream/advice', methods=['POST'])
    def proxy_stream_advice():
        """代理 /stream/advice 到 FastAPI，流式转发 SSE"""
        try:
            resp = requests.post(
                f"{api_base_url}/stream/advice",
                json=request.get_json(force=True),
                stream=True,
                timeout=120
            )
            def generate():
                for chunk in resp.iter_content(chunk_size=None):
                    if chunk:
                        yield chunk
            headers = {
                'Content-Type': 'text/event-stream',
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no',
            }
            return Response(generate(), headers=headers)
        except Exception:
            return 'event: message\ndata: {"type":"token","msg":"服务暂时不可用，请稍后重试。"}\n\n', 502, {'Content-Type': 'text/event-stream'}

    @app.route('/frontend/<path:filename>')
    def serve_frontend(filename):
        return send_from_directory(str(frontend_dir), filename)

    return app

# QQ群问卷星报名助手

自动监听QQ群消息 → 检测问卷/表单链接 → 一键填写报名信息

## 功能

- 🤖 智能填写（解析表单、匹配预设信息、自动填入）
- 👤 多套预设方案（支持多个人信息方案，一键切换）
- 📊 历史记录（SQLite存储每次填写结果）

## 支持的平台

| 平台 | 示例 |
|------|------|
| 金数据 | `jinshuju.com/f/xxxx` |
| 问卷星 | `wjx.cn/vm/xxxx` |

## 快速开始

### 1. 安装浏览器驱动（首次必做）

```
python -m playwright install chromium
```

### 2. 启动

```
python main.py
```

或双击 `dist/QQ报名助手.exe`

### 3. 配置预设

切换至 👤 预设管理 → 填写姓名/学号/手机号 → 设置别名 → 保存

### 4. 开始监听

切换至 📡 监控面板 → 启动监听 → 打开QQ目标群聊

## 打包

```
pip install pyinstaller
pyinstaller --clean build.spec
```

输出: `dist/QQ报名助手.exe`

## 数据位置

`%APPDATA%/QQSurveyAssistant/`
- `profiles.json` — 预设信息
- `history.db` — 填写历史
- `settings.json` — 应用设置

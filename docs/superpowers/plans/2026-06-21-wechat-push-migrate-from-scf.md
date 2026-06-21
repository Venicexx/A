# 企微推送从 SCF 迁移到 Gitee Go 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 创建 Gitee Go 工作流替代 SCF，实现免费的国内可访问每日企微推送，然后停用 SCF。

**Architecture:** 在项目根目录新建 `.gitee-ci.yml`，配置每日 09:00 定时 curl 调企微 Webhook；Webhook URL 通过 Gitee 仓库私密变量注入。

**Tech Stack:** Gitee Go CI、curl、企微 Webhook

## Global Constraints

- 国内网络直连，无需翻墙
- Webhook URL: `https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=35561d77-a386-4401-9d60-f4202c539cee`
- 推送时间: 每日 09:00（北京时间）
- 不再重新启用 SCF 作为回滚
- 回滚通道: 本地 `scripts/wechat_push.sh`

---

### Task 1: 创建 Gitee Go 工作流配置

**Files:**
- Create: `.gitee-ci.yml`

- [ ] **Step 1: 创建 `.gitee-ci.yml`**

```yaml
# 企微每日推送 — Gitee Go 定时任务
# 每日北京时间 09:00 执行

schedule:
  - cron: "0 9 * * *"

jobs:
  wechat-push:
    name: 企微每日推送
    runs-on: ubuntu-latest
    steps:
      - name: 发送企微消息
        run: |
          MSG="⏰ 每日提醒\n\n今日运营数据请及时汇总，如有异常请及时反馈。"

          echo "{\"msgtype\":\"text\",\"text\":{\"content\":\"$MSG\"}}" > /tmp/wechat.json

          RESP=$(curl -s -X POST "$WECHAT_WEBHOOK_URL" \
            -H 'Content-Type: application/json; charset=utf-8' \
            --data-binary @/tmp/wechat.json)

          echo "企微返回: $RESP"

          if echo "$RESP" | grep -q '"errcode":0'; then
            echo "✅ 推送成功"
          else
            echo "❌ 推送失败: $RESP"
            exit 1
          fi
```

- [ ] **Step 2: 提交到仓库**

```bash
git add .gitee-ci.yml
git commit -m "feat: 添加 Gitee Go 企微每日推送工作流"
```

---

### Task 2: 配置 Gitee 仓库私密变量

**操作界面:** Gitee 仓库 → 管理 → CI/CD → 变量

- [ ] **Step 1: 打开 Gitee 仓库设置**

在浏览器打开你的 Gitee 仓库页面（gitee.com）。

- [ ] **Step 2: 进入 CI/CD 变量管理**

左侧菜单：管理 → CI/CD → 变量。

- [ ] **Step 3: 添加私密变量**

点击「新增变量」：

| 字段 | 值 |
|------|-----|
| 变量名 | `WECHAT_WEBHOOK_URL` |
| 变量值 | `https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=35561d77-a386-4401-9d60-f4202c539cee` |
| 类型 | 私密 |

保存。

---

### Task 3: 推送代码到 Gitee 并手动触发验证

- [ ] **Step 1: 推送代码到 Gitee**

```bash
git remote -v
git push gitee master
```

- [ ] **Step 2: 进入 Gitee Go 页面**

在 Gitee 仓库页面，点击顶部导航栏「Gitee Go」。

- [ ] **Step 3: 手动触发流水线**

找到「企微每日推送」工作流，点击「立即运行」或「手动触发」。

- [ ] **Step 4: 等待执行并查看日志**

点击运行记录，查看日志，确认输出 `✅ 推送成功`。

- [ ] **Step 5: 确认收到企微消息**

打开企业微信群，确认收到推送。

---

### Task 4: 停用 SCF 云函数

**操作界面:** 腾讯云控制台 → 云函数 SCF

- [ ] **Step 1: 登录腾讯云控制台**

访问 https://console.cloud.tencent.com/scf

- [ ] **Step 2: 找到并停用函数**

在函数列表中找到企微推送的云函数，点击「停用」。

- [ ] **Step 3: 确认费用停止**

前往费用中心确认 SCF 不再产生新消费。

---

### Task 5: 标记仓库中过期文件

**Files:**
- Modify: `.github/workflows/wechat-reminder.yml`（添加注释标记不可用）

- [ ] **Step 1: 为 GitHub Actions 添加不可用注释**

```yaml
# ⚠️ 已废弃 — 2026-06-21 GitHub 国内不可访问，企微推送已迁移至 Gitee Go (.gitee-ci.yml)
# 保留文件仅作参考
name: 📮 企微每日推送
```

在 `.github/workflows/wechat-reminder.yml` 文件头部的 `name:` 上方插入上述注释。

- [ ] **Step 2: 提交**

```bash
git add .github/workflows/wechat-reminder.yml
git commit -m "docs: 标记 GitHub Actions 为不可用，迁移至 Gitee Go"
```

---

## 完成验证清单

- [ ] `.gitee-ci.yml` 已创建并推送到 Gitee
- [ ] Gitee 私密变量 `WECHAT_WEBHOOK_URL` 已配置
- [ ] Gitee Go 手动触发推送成功，企微群收到消息
- [ ] SCF 云函数已停用
- [ ] 腾讯云费用中心确认不再扣费
- [ ] 本地 `scripts/wechat_push.sh` 可用作回滚
- [ ] 观察 2-3 天，Gitee Go 每日定时推送正常

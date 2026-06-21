#!/bin/bash
# =============================================
# 企业微信群机器人消息推送脚本
# 用法: ./scripts/wechat_push.sh "你要发的消息"
#       ./scripts/wechat_push.sh --markdown "## 标题\n内容"
# =============================================

WEBHOOK_URL="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=35561d77-a386-4401-9d60-f4202c539cee"
TEMP_FILE="/tmp/wechat_push_$$.json"

# 默认文本消息
MSGTYPE="text"
CONTENT="$1"

# 判断是否为 markdown 模式
if [ "$1" = "--markdown" ]; then
    MSGTYPE="markdown"
    CONTENT="$2"
fi

if [ -z "$CONTENT" ]; then
    echo "用法: $0 [--markdown] <消息内容>"
    exit 1
fi

# 构建 JSON 并发送（写入文件避免编码问题）
if [ "$MSGTYPE" = "markdown" ]; then
    printf '{"msgtype":"markdown","markdown":{"content":"%s"}}' "$CONTENT" > "$TEMP_FILE"
else
    printf '{"msgtype":"text","text":{"content":"%s"}}' "$CONTENT" > "$TEMP_FILE"
fi

curl -s -X POST "$WEBHOOK_URL" \
    -H 'Content-Type: application/json; charset=utf-8' \
    --data-binary @"$TEMP_FILE"

echo ""  # 换行
rm -f "$TEMP_FILE"

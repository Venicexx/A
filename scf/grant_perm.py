#!/usr/bin/env python3
# ⚠️ 已废弃 — 2026-06-21 企微推送已迁移至 GitHub Actions，SCF 已停用
# 保留文件仅作参考，请勿重新启用
"""
CAM 授权脚本 - 给子账号附加 SCF 全权限
"""

import json
from tencentcloud.common import credential
from tencentcloud.cam.v20190116 import cam_client, models as cam_models
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException

SECRET_ID  = "YOUR_SECRET_ID"
SECRET_KEY = "YOUR_SECRET_KEY"
SUB_UIN    = 100049985463  # 子账号 UIN

cred = credential.Credential(SECRET_ID, SECRET_KEY)
client = cam_client.CamClient(cred, "")

# ─── 1. 查子账号信息 ───
print("[1] 查询子账号...")
try:
    req = cam_models.DescribeSubAccountsRequest()
    resp = client.DescribeSubAccounts(req)
    accounts = json.loads(resp.to_json_string())
    for acct in accounts.get("SubAccounts", []):
        if str(acct.get("Uin")) == str(SUB_UIN):
            print(f"  找到: {acct['Name']} (UIN: {acct['Uin']})")
except Exception as e:
    print(f"  查询失败: {e}")

# ─── 2. 附加 SCF 全权限 ───
print("[2] 附加 QcloudSCFFullAccess 策略...")
try:
    req2 = cam_models.AttachUserPolicyRequest()
    # 子账号的 UIN 格式: uin/xxxx
    req2.AttachUin = SUB_UIN
    req2.PolicyId  = None  # 用 PolicyName
    req2.PolicyName = "QcloudSCFFullAccess"
    resp2 = client.AttachUserPolicy(req2)
    print("  SCF 全权限已附加")
except TencentCloudSDKException as e:
    if "already" in str(e).lower():
        print("  策略已存在")
    else:
        print(f"  失败: {e}")

print("Done")

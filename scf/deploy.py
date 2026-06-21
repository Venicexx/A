#!/usr/bin/env python3
"""SCF 部署 - 等函数就绪后再配触发器和测试"""
import json, base64, zipfile, io, sys, time
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from tencentcloud.common import credential
from tencentcloud.scf.v20180416 import scf_client, models as scf_models
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException

SECRET_ID  = "YOUR_SECRET_ID"
SECRET_KEY = "YOUR_SECRET_KEY"
REGION     = "ap-guangzhou"
FUNC_NAME  = "weather-reminder"
CRON       = "0 30 7 * * * *"

creds = credential.Credential(SECRET_ID, SECRET_KEY)
client = scf_client.ScfClient(creds, REGION)


def zip_code():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write("scf/index.py", arcname="index.py")
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


def wait_active():
    """等函数变为 Active"""
    print("[1] 等待函数就绪...")
    for i in range(24):
        try:
            req = scf_models.GetFunctionRequest()
            req.FunctionName = FUNC_NAME
            req.Namespace = "default"
            resp = client.GetFunction(req)
            status = resp.Status
            print(f"    {i+1}. 状态: {status}")
            if status == "Active":
                return True
        except Exception as e:
            print(f"    查询异常: {e}")
            if "not found" in str(e).lower() or "ResourceNotFound" in str(e):
                # 函数还没创建完成
                pass
        time.sleep(5)
    return False


def update_code():
    """更新函数代码"""
    print("[2] 更新代码...")
    code = scf_models.Code()
    code.ZipFile = zip_code()

    req = scf_models.UpdateFunctionCodeRequest()
    req.FunctionName = FUNC_NAME
    req.Namespace = "default"
    req.Code = code
    req.Handler = "index.main_handler"
    client.UpdateFunctionCode(req)
    print("    完成")


def create_trigger():
    """创建定时触发器"""
    print("[3] 创建定时触发器...")
    try:
        req = scf_models.CreateTriggerRequest()
        req.FunctionName = FUNC_NAME
        req.Namespace = "default"
        req.TriggerName = "daily-weather-0730"
        req.Type = "timer"
        req.TriggerDesc = CRON  # 直接填 cron 字符串，不用 JSON
        req.Enable = "OPEN"
        client.CreateTrigger(req)
        print("    定时触发已创建: 每天 7:30")
    except TencentCloudSDKException as e:
        if "already" in str(e).lower() or "ResourceInUse" in str(e):
            print("    触发器已存在，跳过")
        else:
            print(f"    失败: {e}")


def test_invoke():
    """手动调用测试"""
    print("[4] 手动测试...")
    try:
        req = scf_models.InvokeRequest()
        req.FunctionName = FUNC_NAME
        req.Namespace = "default"
        req.InvocationType = "RequestResponse"
        req.LogType = "Tail"
        resp = client.Invoke(req)

        log = resp.Result.Log or ""
        print(f"    日志:\n    {log.strip()}")

        ret_msg = resp.Result.RetMsg or "{}"
        ret = json.loads(ret_msg)
        print(f"    返回: {json.dumps(ret, ensure_ascii=False)}")

        err = resp.Result.ErrMsg or ""
        if err:
            print(f"    错误: {err}")

        return ret
    except TencentCloudSDKException as e:
        print(f"    调用失败: {e}")
        return None


def main():
    print("=" * 50)

    # 检查函数是否存在
    try:
        req = scf_models.GetFunctionRequest()
        req.FunctionName = FUNC_NAME
        req.Namespace = "default"
        client.GetFunction(req)
        exists = True
    except:
        exists = False

    if not exists:
        # 创建函数
        print("[0] 创建函数...")
        code = scf_models.Code()
        code.ZipFile = zip_code()
        req = scf_models.CreateFunctionRequest()
        req.FunctionName = FUNC_NAME
        req.Runtime = "Python3.9"
        req.Handler = "index.main_handler"
        req.Description = "科捷物流每日天气提醒"
        req.MemorySize = 128
        req.Timeout = 30
        req.Code = code
        req.Namespace = "default"
        req.Type = "Event"
        try:
            client.CreateFunction(req)
            print("    函数已创建")
        except TencentCloudSDKException as e:
            print(f"    创建失败: {e}")
            sys.exit(1)

    # 等就绪
    if not wait_active():
        print("    [!] 超时")
        sys.exit(1)

    # 更新代码（确保最新）
    update_code()
    time.sleep(5)  # 等待更新请求被处理
    if not wait_active():
        print("    [!] 更新后超时")

    # 触发器
    create_trigger()

    # 测试
    result = test_invoke()

    print("=" * 50)
    if result and result.get("status") == "ok":
        print("DONE - 每天 7:30 自动推送天气，快去企微看看测试消息!")
    else:
        print("DONE - 已创建，测试可能未收到消息，明早 7:30 生效")


if __name__ == "__main__":
    main()

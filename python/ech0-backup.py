import requests
import time
import os
from pathlib import Path

# 从环境变量获取配置
BASE_URL = os.environ.get('BASE_URL', 'https://ech0.enltlh.me/api')
ECH0_TOKEN = os.environ.get('ECH0_TOKEN')
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TARGET_CHAT_ID = os.environ.get('TARGET_CHAT_ID')

# 验证必要的环境变量
def validate_config():
    required_vars = ['ECH0_TOKEN', 'TELEGRAM_BOT_TOKEN', 'TARGET_CHAT_ID']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        raise Exception(f"缺少必要的环境变量: {', '.join(missing_vars)}")
    
    print("✅ 环境变量配置验证成功")

# 1. 执行服务器端备份（创建快照）
def perform_backup(ECH0_TOKEN):
    url = f"{BASE_URL}/backup"
    print(f"🔄 正在创建服务器备份快照...")
    
    headers = {
        "Authorization": f"Bearer {ECH0_TOKEN}",
        "Accept": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        
        print(f"📥 备份响应状态码: {response.status_code}")
        
        if response.status_code != 200:
            raise Exception(f"备份请求失败，状态码 {response.status_code}: {response.text}")
        
        data = response.json()
        
        if data.get("code") == 1:
            print("✅ 服务器备份已创建")
            return True
        else:
            raise Exception(f"备份创建失败: {data.get('message', '未知错误')}")
            
    except Exception as e:
        print(f"❌ 备份处理错误: {str(e)}")
        raise

# 2. 导出备份（下载快照）
def export_backup(ECH0_TOKEN):
    url = f"{BASE_URL}/backup/export?token={ECH0_TOKEN}"
    print(f"📥 开始下载导出的备份文件: {url}")
    
    try:
        response = requests.get(url, stream=True, timeout=60)
        
        print(f"📥 下载响应状态码: {response.status_code}")
        
        if response.status_code != 200:
            raise Exception(f"下载请求失败，状态码 {response.status_code}: {response.text}")
        
        # 生成安全的文件路径
        filename = f"ech0_backup_{int(time.time())}.zip"
        save_path = os.path.join("backups", filename)
        
        # 确保目录存在
        Path("backups").mkdir(exist_ok=True)
        
        with open(save_path, "wb") as f:
            total_length = int(response.headers.get("content-length", 0))
            downloaded = 0
            
            print(f"📦 总文件大小: {total_length} bytes")
            
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    # 显示下载进度
                    if total_length > 0:
                        percent_complete = (downloaded / total_length) * 100
                        progress = "-" * int(percent_complete/5) + " " * (20 - int(percent_complete/5))
                        print(f"\r进度: [{progress}] {percent_complete:.1f}%", end="", flush=True)
                        
            print("\n")
            
        print(f"✅ 备份文件已下载至: {save_path}")
        print(f"📊 文件大小: {os.path.getsize(save_path)} bytes")
        return save_path
        
    except Exception as e:
        print(f"❌ 导出处理错误: {str(e)}")
        raise

# 3. 通过Telegram发送备份文件
def send_backup_via_telegram(file_path):
    print(f"📤 正在通过Telegram发送备份文件: {file_path}")
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
    
    # 检查文件是否存在
    if not os.path.exists(file_path):
        raise Exception(f"备份文件不存在: {file_path}")
    
    # 检查文件大小（Telegram限制最大50MB）
    file_size = os.path.getsize(file_path)
    max_size = 50 * 1024 * 1024  # 50MB
    
    if file_size > max_size:
        print(f"⚠️ 文件大小 {file_size} 字节超过Telegram限制 (50MB)，无法发送")
        return False
    
    try:
        with open(file_path, "rb") as file:
            files = {
                "document": (os.path.basename(file_path), file)
            }
            
            data = {
                "chat_id": TARGET_CHAT_ID,
                "caption": f"Ech0备份文件 - {time.strftime('%Y-%m-%d %H:%M:%S')}"
            }
            
            response = requests.post(url, files=files, data=data, timeout=60)
            
            print(f"📥 Telegram响应状态码: {response.status_code}")
            
            if response.status_code != 200:
                print(f"❌ Telegram发送失败: {response.text}")
                return False
            
            result = response.json()
            if result.get("ok"):
                print("✅ 备份文件已成功发送到Telegram")
                return True
            else:
                print(f"❌ Telegram API错误: {result.get('description', '未知错误')}")
                return False
                
    except Exception as e:
        print(f"❌ Telegram发送处理错误: {str(e)}")
        return False

# 完整流程
def main():
    try:
        print("=" * 50)
        print("🚀 开始Ech0备份流程")
        print("=" * 50)
        
        # 验证配置
        validate_config()
        
        # 步骤1: 执行服务器端备份
        perform_backup(ECH0_TOKEN)
        
        # 步骤2: 导出备份并下载
        file_path = export_backup(ECH0_TOKEN)
        
        print("🎉 备份文件处理完成!")
        
        # 通过Telegram发送备份文件
        print("📤 通过Telegram发送备份文件...")
        send_backup_via_telegram(file_path)
        
        print("✅ 备份流程全部完成!")
        
    except Exception as e:
        print(f"❌ 执行过程中出错: {str(e)}")
        
        # 保存错误日志到文件
        try:
            with open("backup_error.log", "a", encoding="utf-8") as f:
                f.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] 错误: {str(e)}\n")
        except:
            pass
            
        raise

if __name__ == "__main__":
    main()

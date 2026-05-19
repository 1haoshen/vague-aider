import subprocess
import sys

def fix_protobuf():
    try:
        # 检查当前Protobuf版本
        result = subprocess.run([sys.executable, '-m', 'pip', 'show', 'protobuf'], capture_output=True, text=True)
        output = result.stdout
        if 'Version: 4' in output:  # 如果是4.x版本
            print("检测到不兼容的Protobuf版本，正在降级...")
            subprocess.run([sys.executable, '-m', 'pip', 'install', 'protobuf==3.20.3', '--force-reinstall'], check=True)
            print("降级完成！请重新运行你的脚本。")
        else:
            print("Protobuf版本已兼容，无需修复。")
    except Exception as e:
        print(f"修复失败：{e}")

if __name__ == "__main__":
    fix_protobuf()

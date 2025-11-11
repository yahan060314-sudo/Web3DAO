#!/usr/bin/env python3
"""
检查实际使用的.env文件
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

def main():
    """检查.env文件的使用情况"""
    print("=" * 80)
    print("检查.env文件使用情况")
    print("=" * 80)
    print()
    
    # 记录当前工作目录
    cwd = os.getcwd()
    print(f"当前工作目录: {cwd}")
    print()
    
    # 检查.env文件
    env_file = Path(".env")
    env_save_file = Path(".env.save")
    
    print("文件检查:")
    print("-" * 80)
    
    # 检查.env文件
    print(f"\n1. .env文件:")
    if env_file.exists():
        print(f"   ✅ 存在")
        print(f"   路径: {env_file.absolute()}")
        print(f"   大小: {env_file.stat().st_size} bytes")
        print(f"   修改时间: {env_file.stat().st_mtime}")
        
        # 读取前几行（不显示敏感信息）
        try:
            with open(env_file, 'r') as f:
                lines = f.readlines()
                print(f"   行数: {len(lines)}")
                print(f"   前3行内容:")
                for i, line in enumerate(lines[:3], 1):
                    # 隐藏敏感信息
                    if 'KEY' in line or 'SECRET' in line:
                        parts = line.split('=')
                        if len(parts) == 2:
                            print(f"      {i}. {parts[0]}=***")
                        else:
                            print(f"      {i}. {line.strip()}")
                    else:
                        print(f"      {i}. {line.strip()}")
        except Exception as e:
            print(f"   ⚠️ 读取文件失败: {e}")
    else:
        print(f"   ❌ 不存在")
    
    # 检查.env.save文件
    print(f"\n2. .env.save文件:")
    if env_save_file.exists():
        print(f"   ✅ 存在")
        print(f"   路径: {env_save_file.absolute()}")
        print(f"   大小: {env_save_file.stat().st_size} bytes")
        print(f"   修改时间: {env_save_file.stat().st_mtime}")
        
        # 读取前几行（不显示敏感信息）
        try:
            with open(env_save_file, 'r') as f:
                lines = f.readlines()
                print(f"   行数: {len(lines)}")
                print(f"   前3行内容:")
                for i, line in enumerate(lines[:3], 1):
                    # 隐藏敏感信息
                    if 'KEY' in line or 'SECRET' in line:
                        parts = line.split('=')
                        if len(parts) == 2:
                            print(f"      {i}. {parts[0]}=***")
                        else:
                            print(f"      {i}. {line.strip()}")
                    else:
                        print(f"      {i}. {line.strip()}")
        except Exception as e:
            print(f"   ⚠️ 读取文件失败: {e}")
    else:
        print(f"   ❌ 不存在")
    
    # 加载.env文件
    print("\n" + "=" * 80)
    print("加载环境变量")
    print("=" * 80)
    print()
    
    print("使用load_dotenv()加载.env文件...")
    load_dotenv()
    
    # 检查加载的环境变量
    print("\n加载的环境变量:")
    print("-" * 80)
    
    env_vars = [
        "ROOSTOO_API_URL",
        "ROOSTOO_API_KEY",
        "ROOSTOO_SECRET_KEY",
        "LLM_PROVIDER",
        "DEEPSEEK_API_KEY",
        "QWEN_API_KEY",
        "MINIMAX_API_KEY",
    ]
    
    for var in env_vars:
        value = os.getenv(var)
        if value:
            if 'KEY' in var or 'SECRET' in var:
                # 隐藏敏感信息
                if len(value) > 20:
                    display_value = f"{value[:10]}...{value[-10:]}"
                else:
                    display_value = "***"
            else:
                display_value = value
            print(f"  ✅ {var}: {display_value}")
        else:
            print(f"  ❌ {var}: NOT SET")
    
    # 比较两个文件
    print("\n" + "=" * 80)
    print("文件比较")
    print("=" * 80)
    print()
    
    if env_file.exists() and env_save_file.exists():
        print("比较.env和.env.save文件...")
        
        # 读取两个文件的内容
        try:
            with open(env_file, 'r') as f:
                env_lines = set(line.strip() for line in f if line.strip() and not line.strip().startswith('#'))
            
            with open(env_save_file, 'r') as f:
                env_save_lines = set(line.strip() for line in f if line.strip() and not line.strip().startswith('#'))
            
            # 找出差异
            only_in_env = env_lines - env_save_lines
            only_in_env_save = env_save_lines - env_lines
            common = env_lines & env_save_lines
            
            print(f"\n共同配置项: {len(common)}")
            print(f"仅在.env中: {len(only_in_env)}")
            print(f"仅在.env.save中: {len(only_in_env_save)}")
            
            if only_in_env:
                print(f"\n仅在.env中的配置项:")
                for item in sorted(only_in_env):
                    if 'KEY' in item or 'SECRET' in item:
                        parts = item.split('=')
                        if len(parts) == 2:
                            print(f"  - {parts[0]}=***")
                        else:
                            print(f"  - {item}")
                    else:
                        print(f"  - {item}")
            
            if only_in_env_save:
                print(f"\n仅在.env.save中的配置项:")
                for item in sorted(only_in_env_save):
                    if 'KEY' in item or 'SECRET' in item:
                        parts = item.split('=')
                        if len(parts) == 2:
                            print(f"  - {parts[0]}=***")
                        else:
                            print(f"  - {item}")
                    else:
                        print(f"  - {item}")
            
            if not only_in_env and not only_in_env_save:
                print("\n✅ 两个文件内容相同")
            else:
                print("\n⚠️ 两个文件内容不同")
                print("\n建议:")
                print("  1. 如果.env.save包含更完整的配置，可以将其复制到.env")
                print("  2. 或者将.env.save重命名为.env（先备份当前的.env）")
                
        except Exception as e:
            print(f"⚠️ 比较文件失败: {e}")
    
    # 总结
    print("\n" + "=" * 80)
    print("总结")
    print("=" * 80)
    print()
    
    print("关键发现:")
    print("  1. 代码中所有load_dotenv()调用都只加载.env文件")
    print("  2. 不会自动加载.env.save文件")
    print("  3. 如果代码能正常运行，说明.env文件包含必要的配置")
    print()
    
    if env_file.exists():
        print("✅ 当前使用的文件: .env")
        if env_save_file.exists():
            print("⚠️ 注意: .env.save文件存在但未被使用")
    else:
        print("❌ .env文件不存在")
        if env_save_file.exists():
            print("💡 建议: 将.env.save重命名为.env")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


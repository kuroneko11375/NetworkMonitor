#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
遠端軟體檢測測試工具
用於測試遠端軟體檢測功能是否正常
作者:SchwarzeKatze_R
版本:1.0
日期:2025-08-29

"""

import sys
import subprocess


def check_remote_software():
    """檢查當前運行的遠端軟體"""
    
    # 支援的遠端軟體列表
    remote_processes = [
        "teamviewer.exe", "anydesk.exe", "parsec.exe", "parsecd.exe",
        "chrome_remote_desktop.exe", "mstsc.exe", "rdpclip.exe", 
        "vnc", "radmin", "rustdesk.exe", "nomachine"
    ]
    
    print("🔍 檢測遠端軟體運行狀態...")
    print("=" * 50)
    
    try:
        if sys.platform.startswith('win'):
            # Windows 系統使用 tasklist
            result = subprocess.run(['tasklist'], capture_output=True, text=True, encoding='cp950')
            running_processes = result.stdout.lower()
            
            print("📋 支援的遠端軟體列表:")
            for i, proc_name in enumerate(remote_processes, 1):
                print(f"   {i:2d}. {proc_name}")
            
            print("\n🔎 檢測結果:")
            found_processes = []
            
            for proc_name in remote_processes:
                if proc_name.lower() in running_processes:
                    found_processes.append(proc_name)
                    print(f"   ✅ {proc_name} - 正在運行")
                else:
                    print(f"   ❌ {proc_name} - 未運行")
            
            print("\n" + "=" * 50)
            if found_processes:
                print(f"🎯 檢測到 {len(found_processes)} 個遠端軟體正在運行:")
                for proc in found_processes:
                    print(f"   • {proc}")
                print("\n✅ 網路監控器將會啟動監控功能")
            else:
                print("❌ 未檢測到任何遠端軟體運行")
                print("📝 網路監控器將處於待機狀態")
        
        else:
            # Linux/Mac 系統使用 ps
            result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
            running_processes = result.stdout.lower()
            
            print("📋 支援的遠端軟體列表:")
            for i, proc_name in enumerate(remote_processes, 1):
                display_name = proc_name.replace('.exe', '')
                print(f"   {i:2d}. {display_name}")
            
            print("\n🔎 檢測結果:")
            found_processes = []
            
            for proc_name in remote_processes:
                search_name = proc_name.lower().replace('.exe', '')
                if search_name in running_processes:
                    found_processes.append(proc_name)
                    print(f"   ✅ {search_name} - 正在運行")
                else:
                    print(f"   ❌ {search_name} - 未運行")
            
            print("\n" + "=" * 50)
            if found_processes:
                print(f"🎯 檢測到 {len(found_processes)} 個遠端軟體正在運行:")
                for proc in found_processes:
                    print(f"   • {proc}")
                print("\n✅ 網路監控器將會啟動監控功能")
            else:
                print("❌ 未檢測到任何遠端軟體運行")
                print("📝 網路監控器將處於待機狀態")
            
    except Exception as e:
        print(f"❌ 檢測過程中發生錯誤: {e}")
        return False, []
    
    return len(found_processes) > 0, found_processes


def test_network_connectivity():
    """測試網路連線"""
    
    print("\n🌐 測試網路連線...")
    print("=" * 50)
    
    test_hosts = ["8.8.8.8", "1.1.1.1", "google.com"]
    successful_pings = 0
    
    for host in test_hosts:
        try:
            if sys.platform.startswith('win'):
                cmd = ['ping', '-n', '1', '-w', '5000', host]
            else:
                cmd = ['ping', '-c', '1', '-W', '5', host]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=7)
            
            if result.returncode == 0:
                print(f"   ✅ {host} - 連線正常")
                successful_pings += 1
            else:
                print(f"   ❌ {host} - 連線失敗")
                
        except subprocess.TimeoutExpired:
            print(f"   ⏰ {host} - 連線超時")
        except Exception as e:
            print(f"   ❌ {host} - 錯誤: {e}")
    
    # DNS 測試
    try:
        import socket
        socket.gethostbyname("google.com")
        dns_ok = True
        print(f"   ✅ DNS解析 - 正常")
    except:
        dns_ok = False
        print(f"   ❌ DNS解析 - 失敗")
    
    ping_success_rate = successful_pings / len(test_hosts)
    overall_status = (ping_success_rate >= 0.3 or dns_ok)
    
    print("\n" + "=" * 50)
    print(f"📊 網路檢測摘要:")
    print(f"   • Ping 成功率: {ping_success_rate:.1%} ({successful_pings}/{len(test_hosts)})")
    print(f"   • DNS 解析: {'正常' if dns_ok else '異常'}")
    print(f"   • 整體狀態: {'✅ 正常' if overall_status else '❌ 異常'}")
    
    return overall_status


def main():
    """主函數"""
    print("遠端軟體檢測測試工具")
    print("=" * 50)
    print("🔧 此工具用於測試網路監控器的檢測功能")
    print("📝 建議在啟動網路監控器前先運行此測試\n")
    
    try:
        # 檢測遠端軟體
        remote_active, remote_processes = check_remote_software()
        
        # 測試網路連線
        network_ok = test_network_connectivity()
        
        # 總結
        print("\n🎯 總結報告")
        print("=" * 50)
        print(f"遠端軟體狀態: {'✅ 已檢測到' if remote_active else '❌ 未檢測到'}")
        print(f"網路連線狀態: {'✅ 正常' if network_ok else '❌ 異常'}")
        
        if remote_active:
            print(f"\n✅ 網路監控器將會監控網路狀態")
            print(f"📝 檢測到的遠端軟體: {', '.join(remote_processes)}")
        else:
            print(f"\n📝 網路監控器將處於待機狀態（等待遠端軟體啟動）")
        
        if not network_ok:
            print(f"\n⚠️  警告: 網路檢測異常，請檢查網路連線")
        
    except KeyboardInterrupt:
        print("\n\n👋 測試已中斷")
    except Exception as e:
        print(f"\n❌ 測試過程中發生錯誤: {e}")
    
    print(f"\n按 Enter 鍵結束...")
    input()


if __name__ == "__main__":
    main()

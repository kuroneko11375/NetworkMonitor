#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
網路監控程式
用於監控網路連線狀態，在遠端軟體連線時自動處理網路斷線問題
作者:SchwarzeKatze_R
版本:1.0
日期:2025-08-29
"""

import os
import sys
import time
import json
import logging
import socket
import subprocess
import psutil
import requests
import schedule
from datetime import datetime, timedelta
from pathlib import Path
import threading
from typing import Dict, List, Optional, Tuple


class NetworkMonitor:
    def __init__(self, config_file: str = "config.json"):
        """初始化網路監控器"""
        self.config_file = config_file
        self.config = self.load_config()
        self.reboot_count = 0
        self.max_reboots = self.config.get('max_reboots', 2)
        self.check_interval = self.config.get('check_interval', 30)  # 秒
        self.log_file = self.config.get('log_file', 'network_monitor.log')
        self.is_monitoring = False
        self.last_reboot_time = None
        self.reboot_cooldown = self.config.get('reboot_cooldown', 3600)  # 1小時
        
        # 設定日誌
        self.setup_logging()
        
        # 載入重開計數器
        self.load_reboot_count()
        
        self.logger.info("網路監控器已初始化")
    
    def load_config(self) -> Dict:
        """載入配置檔案"""
        default_config = {
            "max_reboots": 2,
            "check_interval": 30,
            "log_file": "network_monitor.log",
            "reboot_cooldown": 3600,
            "test_hosts": [
                "8.8.8.8",
                "1.1.1.1",
                "google.com"
            ],
            "remote_software_processes": [
                "teamviewer.exe",
                "anydesk.exe",
                "chrome_remote_desktop.exe",
                "mstsc.exe",
                "rdpclip.exe"
            ],
            "ping_timeout": 5,
            "connection_failures_threshold": 3
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # 合併預設配置
                    default_config.update(config)
                    return default_config
            except Exception as e:
                print(f"載入配置檔案失敗: {e}")
                return default_config
        else:
            # 建立預設配置檔案
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, ensure_ascii=False, indent=4)
            return default_config
    
    def setup_logging(self):
        """設定日誌系統"""
        log_format = '%(asctime)s - %(levelname)s - %(message)s'
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=[
                logging.FileHandler(self.log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def load_reboot_count(self):
        """載入重開計數器"""
        count_file = "reboot_count.json"
        if os.path.exists(count_file):
            try:
                with open(count_file, 'r') as f:
                    data = json.load(f)
                    self.reboot_count = data.get('count', 0)
                    last_reboot = data.get('last_reboot')
                    if last_reboot:
                        self.last_reboot_time = datetime.fromisoformat(last_reboot)
                        
                    # 如果距離上次重開已經超過冷卻時間，重置計數器
                    if (self.last_reboot_time and 
                        datetime.now() - self.last_reboot_time > timedelta(seconds=self.reboot_cooldown)):
                        self.reboot_count = 0
                        self.save_reboot_count()
                        
            except Exception as e:
                self.logger.error(f"載入重開計數器失敗: {e}")
                self.reboot_count = 0
    
    def save_reboot_count(self):
        """儲存重開計數器"""
        count_file = "reboot_count.json"
        data = {
            'count': self.reboot_count,
            'last_reboot': self.last_reboot_time.isoformat() if self.last_reboot_time else None
        }
        try:
            with open(count_file, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            self.logger.error(f"儲存重開計數器失敗: {e}")
    
    def is_remote_software_running(self) -> Tuple[bool, List[str]]:
        """檢查是否有遠端軟體正在運行"""
        running_processes = []
        remote_processes = self.config['remote_software_processes']
        
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    proc_name = proc.info['name'].lower()
                    for remote_proc in remote_processes:
                        if remote_proc.lower() in proc_name:
                            running_processes.append(proc.info['name'])
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                    
            return len(running_processes) > 0, running_processes
        except Exception as e:
            self.logger.error(f"檢查遠端軟體狀態失敗: {e}")
            return False, []
    
    def ping_host(self, host: str, timeout: int = 5) -> bool:
        """Ping 指定主機"""
        try:
            if sys.platform.startswith('win'):
                cmd = ['ping', '-n', '1', '-w', str(timeout * 1000), host]
            else:
                cmd = ['ping', '-c', '1', '-W', str(timeout), host]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 2)
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            return False
        except Exception as e:
            self.logger.error(f"Ping {host} 失敗: {e}")
            return False
    
    def test_http_connection(self, url: str = "http://www.google.com", timeout: int = 10) -> bool:
        """測試HTTP連線"""
        try:
            response = requests.get(url, timeout=timeout)
            return response.status_code == 200
        except Exception:
            return False
    
    def test_dns_resolution(self, hostname: str = "google.com") -> bool:
        """測試DNS解析"""
        try:
            socket.gethostbyname(hostname)
            return True
        except socket.gaierror:
            return False
    
    def check_network_connectivity(self) -> Dict[str, any]:
        """檢查網路連線狀態"""
        results = {
            'timestamp': datetime.now().isoformat(),
            'ping_results': {},
            'http_test': False,
            'dns_test': False,
            'overall_status': False
        }
        
        # 測試 Ping
        successful_pings = 0
        test_hosts = self.config['test_hosts']
        
        for host in test_hosts:
            ping_result = self.ping_host(host, self.config['ping_timeout'])
            results['ping_results'][host] = ping_result
            if ping_result:
                successful_pings += 1
        
        # 測試 HTTP 連線
        results['http_test'] = self.test_http_connection()
        
        # 測試 DNS 解析
        results['dns_test'] = self.test_dns_resolution()
        
        # 判斷整體網路狀態
        ping_success_rate = successful_pings / len(test_hosts)
        results['overall_status'] = (
            ping_success_rate >= 0.5 and  # 至少一半的ping成功
            (results['http_test'] or results['dns_test'])  # HTTP或DNS測試成功
        )
        
        return results
    
    def analyze_network_failure(self, test_results: Dict) -> str:
        """分析網路故障原因"""
        analysis = []
        
        ping_results = test_results['ping_results']
        successful_pings = sum(1 for result in ping_results.values() if result)
        
        if successful_pings == 0:
            analysis.append("所有主機 Ping 測試失敗 - 可能是本地網路連線問題")
        elif successful_pings < len(ping_results):
            analysis.append(f"部分主機 Ping 失敗 ({successful_pings}/{len(ping_results)}) - 可能是網路不穩定")
        
        if not test_results['dns_test']:
            analysis.append("DNS 解析失敗 - 可能是 DNS 伺服器問題")
        
        if not test_results['http_test']:
            analysis.append("HTTP 連線測試失敗 - 可能是防火牆或代理伺服器問題")
        
        # 檢查網路介面卡狀態
        try:
            network_stats = psutil.net_if_stats()
            for interface, stats in network_stats.items():
                if not stats.isup and 'loopback' not in interface.lower():
                    analysis.append(f"網路介面卡 {interface} 未啟動")
        except Exception as e:
            analysis.append(f"無法檢查網路介面卡狀態: {e}")
        
        return "; ".join(analysis) if analysis else "網路故障原因不明"
    
    def restart_computer(self):
        """重新啟動電腦"""
        self.logger.warning(f"準備重新啟動電腦 (第 {self.reboot_count + 1} 次)")
        
        self.reboot_count += 1
        self.last_reboot_time = datetime.now()
        self.save_reboot_count()
        
        try:
            if sys.platform.startswith('win'):
                subprocess.run(['shutdown', '/r', '/t', '10', '/c', '網路監控器自動重啟'], check=True)
            else:
                subprocess.run(['sudo', 'reboot'], check=True)
            
            self.logger.info("重啟命令已執行")
        except subprocess.CalledProcessError as e:
            self.logger.error(f"重啟失敗: {e}")
        except Exception as e:
            self.logger.error(f"重啟過程中發生錯誤: {e}")
    
    def start_monitoring(self):
        """開始監控"""
        self.is_monitoring = True
        self.logger.info("開始網路監控")
        
        consecutive_failures = 0
        failure_threshold = self.config['connection_failures_threshold']
        
        while self.is_monitoring:
            try:
                # 檢查是否有遠端軟體運行
                remote_active, remote_processes = self.is_remote_software_running()
                
                if not remote_active:
                    self.logger.debug("未檢測到遠端軟體運行，跳過本次檢查")
                    time.sleep(self.check_interval)
                    consecutive_failures = 0  # 重置失敗計數
                    continue
                
                self.logger.info(f"檢測到遠端軟體運行: {', '.join(remote_processes)}")
                
                # 檢查網路連線
                test_results = self.check_network_connectivity()
                
                if test_results['overall_status']:
                    if consecutive_failures > 0:
                        self.logger.info("網路連線已恢復")
                    consecutive_failures = 0
                else:
                    consecutive_failures += 1
                    failure_analysis = self.analyze_network_failure(test_results)
                    
                    self.logger.warning(f"網路連線失敗 (連續 {consecutive_failures} 次)")
                    self.logger.warning(f"故障分析: {failure_analysis}")
                    
                    # 詳細記錄測試結果
                    self.logger.info(f"詳細測試結果: {json.dumps(test_results, ensure_ascii=False, indent=2)}")
                    
                    # 如果連續失敗次數達到閾值且未超過重啟限制
                    if (consecutive_failures >= failure_threshold and 
                        self.reboot_count < self.max_reboots):
                        
                        # 檢查冷卻時間
                        if (self.last_reboot_time is None or 
                            datetime.now() - self.last_reboot_time > timedelta(seconds=self.reboot_cooldown)):
                            
                            self.logger.critical(f"網路持續斷線，執行自動重啟 (已重啟 {self.reboot_count} 次)")
                            self.restart_computer()
                            break  # 重啟後結束監控
                        else:
                            remaining_cooldown = self.reboot_cooldown - (datetime.now() - self.last_reboot_time).seconds
                            self.logger.info(f"重啟冷卻中，剩餘 {remaining_cooldown} 秒")
                    
                    elif self.reboot_count >= self.max_reboots:
                        self.logger.critical(f"已達到最大重啟次數 ({self.max_reboots})，停止自動重啟")
                        self.logger.critical(f"請手動檢查網路問題: {failure_analysis}")
                        # 繼續監控但不重啟
                
                time.sleep(self.check_interval)
                
            except KeyboardInterrupt:
                self.logger.info("收到中斷信號，停止監控")
                break
            except Exception as e:
                self.logger.error(f"監控過程中發生錯誤: {e}")
                time.sleep(self.check_interval)
        
        self.is_monitoring = False
    
    def stop_monitoring(self):
        """停止監控"""
        self.is_monitoring = False
        self.logger.info("網路監控已停止")
    
    def reset_reboot_count(self):
        """重置重啟計數器"""
        self.reboot_count = 0
        self.last_reboot_time = None
        self.save_reboot_count()
        self.logger.info("重啟計數器已重置")
    
    def get_status(self) -> Dict:
        """獲取監控狀態"""
        remote_active, remote_processes = self.is_remote_software_running()
        network_status = self.check_network_connectivity()
        
        return {
            'monitoring_active': self.is_monitoring,
            'reboot_count': self.reboot_count,
            'max_reboots': self.max_reboots,
            'last_reboot_time': self.last_reboot_time.isoformat() if self.last_reboot_time else None,
            'remote_software_active': remote_active,
            'remote_processes': remote_processes,
            'network_status': network_status
        }


def main():
    """主函數"""
    print("網路監控器 v1.0")
    print("=" * 50)
    
    monitor = NetworkMonitor()
    
    try:
        # 顯示當前狀態
        status = monitor.get_status()
        print(f"當前重啟次數: {status['reboot_count']}/{status['max_reboots']}")
        print(f"遠端軟體狀態: {'運行中' if status['remote_software_active'] else '未運行'}")
        if status['remote_processes']:
            print(f"檢測到的遠端軟體: {', '.join(status['remote_processes'])}")
        
        print("\n開始監控... (按 Ctrl+C 停止)")
        monitor.start_monitoring()
        
    except KeyboardInterrupt:
        print("\n正在停止監控...")
        monitor.stop_monitoring()
    except Exception as e:
        print(f"程式發生錯誤: {e}")
        monitor.logger.error(f"主程式錯誤: {e}")
    finally:
        print("網路監控器已關閉")


if __name__ == "__main__":
    main()
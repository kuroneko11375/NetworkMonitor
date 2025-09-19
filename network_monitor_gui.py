#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
網路監控器 GUI 版本
帶有圖形介面的網路監控程式
作者:SchwarzeKatze_R
版本:1.0.1
日期:2025-09-19
"""

import os
import sys
import time
import json
import logging
import pystray
from PIL import Image, ImageDraw
import socket
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from datetime import datetime, timedelta
from pathlib import Path

def _win_no_window_kwargs():
    """Return subprocess.run kwargs to prevent console windows on Windows."""
    if not sys.platform.startswith('win'):
        return {}
    kwargs = {}
    try:
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        kwargs['startupinfo'] = si
        kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
    except Exception:
        # Fallback silently if STARTUPINFO is unavailable in the environment
        pass
    return kwargs



def _win_startupinfo_and_flags():
    """Return (startupinfo, creationflags) that hide console windows on Windows."""
    si = None
    flags = 0
    if sys.platform.startswith('win'):
        try:
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            # 0x08000000 is subprocess.CREATE_NO_WINDOW on Windows
            flags = 0x08000000
        except Exception:
            si = None
            flags = 0
    return si, flags


class NetworkMonitorGUI:

    # ===== System Tray Integration (pystray) =====
    def _create_tray_image(self):
        # Create a simple 64x64 icon dynamically
        img = Image.new('RGB', (64, 64), (36, 36, 36))
        dc = ImageDraw.Draw(img)
        dc.ellipse((6, 6, 58, 58), fill=(88, 178, 88))
        dc.text((20, 22), "NM", fill=(255, 255, 255))
        return img

    def _tray_show(self, icon=None, item=None):
        # marshal to Tk thread
        try:
            self.root.after(0, lambda: (self.root.deiconify(), self.root.lift(), self.root.focus_force()))
        except Exception:
            pass

    def _tray_toggle_monitor(self, icon=None, item=None):
        # toggle monitoring state via menu
        def _do():
            if self.is_monitoring:
                self.stop_monitoring()
            else:
                self.start_monitoring()
        try:
            self.root.after(0, _do)
        except Exception:
            pass

    def _tray_quit(self, icon=None, item=None):
        # graceful quit
        def _do():
            try:
                if self.is_monitoring:
                    self.stop_monitoring()
            except Exception:
                pass
            try:
                if hasattr(self, 'tray_icon') and self.tray_icon is not None:
                    self.tray_icon.visible = False
                    self.tray_icon.stop()
            except Exception:
                pass
            try:
                self.root.destroy()
            except Exception:
                pass
        try:
            self.root.after(0, _do)
        except Exception:
            pass

    def setup_tray(self):
        # Build tray icon & menu
        try:
            image = self._create_tray_image()
            menu = pystray.Menu(
                pystray.MenuItem('顯示視窗', self._tray_show),
                pystray.MenuItem(lambda item: '停止監控' if self.is_monitoring else '開始監控', self._tray_toggle_monitor),
                pystray.MenuItem('結束程式', self._tray_quit)
            )
            self.tray_icon = pystray.Icon('NetworkMonitor', image, '網路監控器', menu)
            # run in background
            self.tray_icon.run_detached()
        except Exception as e:
            self.log_message(f'初始化系統匣失敗: {e}', 'ERROR')

    def __init__(self):
        """初始化網路監控器GUI"""
        self.reboot_count = 0
        self.max_reboots = 2
        self.check_interval = 30  # 秒
        self.is_monitoring = False
        self.tray_icon = None
        self.last_reboot_time = None
        self.reboot_cooldown = 3600  # 1小時
        self.failure_threshold = 3  # 連續失敗次數閾值
        
        # 測試主機列表
        self.test_hosts = ["8.8.8.8", "1.1.1.1", "google.com"]
        
        # 遠端軟體進程名稱
        self.remote_processes = [
            "teamviewer.exe", "anydesk.exe", "parsec.exe", "parsecd.exe",
            "chrome_remote_desktop.exe", "mstsc.exe", "rdpclip.exe", 
            "vnc", "radmin", "rustdesk.exe", "nomachine"
        ]
        
        # 狀態變數
        self.current_status = {
            'network_ok': True,  # 初始假設網路正常
            'remote_active': False,
            'remote_processes': [],
            'last_check': None,
            'consecutive_failures': 0
        }
        
        # 載入重開計數器
        self.load_reboot_count()
        
        # 建立GUI
        self.setup_gui()

        # 初始化系統匣圖示
        self.setup_tray()
        
        # 啟動狀態更新線程
        self.start_status_thread()
        
        # 進行初始檢測
        self.perform_initial_check()

        # 程式啟動即自動開始監控
        self.root.after(0, self.start_monitoring)
    
    def setup_gui(self):
        """設定GUI介面"""
        self.root = tk.Tk()
        self.root.title("網路監控器 v1.0")
        self.root.geometry("600x500")
        self.root.resizable(True, True)
        
        # 設定圖示（如果有的話）
        try:
            # self.root.iconbitmap("icon.ico")  # 可以添加圖示檔案
            pass
        except:
            pass
        
        # 建立主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置網格權重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # 標題
        title_label = ttk.Label(main_frame, text="網路監控器", font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # 狀態顯示區域
        status_frame = ttk.LabelFrame(main_frame, text="連線狀態", padding="10")
        status_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        status_frame.columnconfigure(1, weight=1)
        
        # 網路狀態
        ttk.Label(status_frame, text="網路連線:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.network_status_label = ttk.Label(status_frame, text="待檢測", foreground="blue")
        self.network_status_label.grid(row=0, column=1, sticky=tk.W)
        
        # 遠端軟體狀態
        ttk.Label(status_frame, text="遠端軟體:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10))
        self.remote_status_label = ttk.Label(status_frame, text="待檢測", foreground="blue")
        self.remote_status_label.grid(row=1, column=1, sticky=tk.W)
        
        # 監控狀態
        ttk.Label(status_frame, text="監控狀態:").grid(row=2, column=0, sticky=tk.W, padx=(0, 10))
        self.monitor_status_label = ttk.Label(status_frame, text="已停止", foreground="red")
        self.monitor_status_label.grid(row=2, column=1, sticky=tk.W)
        
        # 最後檢查時間
        ttk.Label(status_frame, text="最後檢查:").grid(row=3, column=0, sticky=tk.W, padx=(0, 10))
        self.last_check_label = ttk.Label(status_frame, text="從未檢查")
        self.last_check_label.grid(row=3, column=1, sticky=tk.W)
        
        # 重啟計數
        ttk.Label(status_frame, text="重啟次數:").grid(row=4, column=0, sticky=tk.W, padx=(0, 10))
        self.reboot_count_label = ttk.Label(status_frame, text=f"{self.reboot_count}/{self.max_reboots}")
        self.reboot_count_label.grid(row=4, column=1, sticky=tk.W)
        
        # 控制按鈕區域
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=2, column=0, columnspan=2, pady=(0, 10))
        
        self.start_button = ttk.Button(control_frame, text="開始監控", command=self.start_monitoring)
        self.start_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stop_button = ttk.Button(control_frame, text="停止監控", command=self.stop_monitoring, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.reset_button = ttk.Button(control_frame, text="重置計數器", command=self.reset_reboot_count)
        self.reset_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.test_button = ttk.Button(control_frame, text="測試連線", command=self.test_connection_manual)
        self.test_button.pack(side=tk.LEFT)
        
        # 設定區域
        settings_frame = ttk.LabelFrame(main_frame, text="設定", padding="10")
        settings_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        settings_frame.columnconfigure(1, weight=1)
        
        # 檢查間隔
        ttk.Label(settings_frame, text="檢查間隔(秒):").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.interval_var = tk.StringVar(value=str(self.check_interval))
        interval_entry = ttk.Entry(settings_frame, textvariable=self.interval_var, width=10)
        interval_entry.grid(row=0, column=1, sticky=tk.W)
        
        # 最大重啟次數
        ttk.Label(settings_frame, text="最大重啟次數:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10))
        self.max_reboots_var = tk.StringVar(value=str(self.max_reboots))
        max_reboots_entry = ttk.Entry(settings_frame, textvariable=self.max_reboots_var, width=10)
        max_reboots_entry.grid(row=1, column=1, sticky=tk.W)
        
        # 應用設定按鈕
        apply_button = ttk.Button(settings_frame, text="應用設定", command=self.apply_settings)
        apply_button.grid(row=2, column=0, columnspan=2, pady=(10, 0))
        
        # 日誌顯示區域
        log_frame = ttk.LabelFrame(main_frame, text="日誌", padding="10")
        log_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(4, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, state=tk.DISABLED)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 清除日誌按鈕
        clear_log_button = ttk.Button(log_frame, text="清除日誌", command=self.clear_log)
        clear_log_button.grid(row=1, column=0, pady=(5, 0))
        
        # 狀態列
        self.status_bar = ttk.Label(self.root, text="就緒", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.grid(row=1, column=0, sticky=(tk.W, tk.E))
    
    def log_message(self, message, level="INFO"):
        """在GUI中顯示日誌訊息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {level}: {message}\n"
        
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, formatted_message)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        
        # 更新狀態列
        self.status_bar.config(text=message)
    
    def clear_log(self):
        """清除日誌顯示"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    def load_reboot_count(self):
        """載入重開計數器"""
        count_file = "gui_reboot_count.json"
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
                self.log_message(f"載入重開計數器失敗: {e}", "ERROR")
                self.reboot_count = 0
    
    def save_reboot_count(self):
        """儲存重開計數器"""
        count_file = "gui_reboot_count.json"
        data = {
            'count': self.reboot_count,
            'last_reboot': self.last_reboot_time.isoformat() if self.last_reboot_time else None
        }
        try:
            with open(count_file, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            self.log_message(f"儲存重開計數器失敗: {e}", "ERROR")
    
    def is_remote_software_running(self):
        """檢查是否有遠端軟體正在運行"""
        try:
            if sys.platform.startswith('win'):
                result = subprocess.run(['tasklist'], capture_output=True, text=True, startupinfo=_win_startupinfo_and_flags()[0], creationflags=_win_startupinfo_and_flags()[1])
                running_processes = result.stdout.lower()
                
                found_processes = []
                for proc_name in self.remote_processes:
                    if proc_name.lower() in running_processes:
                        found_processes.append(proc_name)
                
                return len(found_processes) > 0, found_processes
            else:
                # Linux/Mac 系統
                result = subprocess.run(['ps','aux'], capture_output=True, text=True, startupinfo=_win_startupinfo_and_flags()[0], creationflags=_win_startupinfo_and_flags()[1])
                running_processes = result.stdout.lower()
                
                found_processes = []
                for proc_name in self.remote_processes:
                    if proc_name.lower().replace('.exe', '') in running_processes:
                        found_processes.append(proc_name)
                
                return len(found_processes) > 0, found_processes
                
        except Exception as e:
            self.log_message(f"檢查遠端軟體狀態失敗: {e}", "ERROR")
            return False, []
    
    def ping_host(self, host, timeout=5):
        """Ping 指定主機"""
        try:
            if sys.platform.startswith('win'):
                cmd = ['ping', '-n', '1', '-w', str(timeout * 1000), host]
            else:
                cmd = ['ping', '-c', '1', '-W', str(timeout), host]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 2, startupinfo=_win_startupinfo_and_flags()[0], creationflags=_win_startupinfo_and_flags()[1])
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            return False
        except Exception as e:
            self.log_message(f"Ping {host} 失敗: {e}", "ERROR")
            return False
    
    def test_dns_resolution(self, hostname="google.com"):
        """測試DNS解析"""
        try:
            socket.gethostbyname(hostname)
            return True
        except socket.gaierror:
            return False
    
    def check_network_connectivity(self):
        """檢查網路連線狀態"""
        results = {
            'timestamp': datetime.now().isoformat(),
            'ping_results': {},
            'dns_test': False,
            'overall_status': False
        }
        
        # 測試 Ping
        successful_pings = 0
        for host in self.test_hosts:
            ping_result = self.ping_host(host, 5)
            results['ping_results'][host] = ping_result
            if ping_result:
                successful_pings += 1
        
        # 測試 DNS 解析
        results['dns_test'] = self.test_dns_resolution()
        
        # 判斷整體網路狀態（更寬鬆的條件）
        ping_success_rate = successful_pings / len(self.test_hosts)
        results['overall_status'] = (
            ping_success_rate >= 0.3 or  # 至少30%的ping成功
            results['dns_test']  # 或者DNS測試成功
        )
        
        return results
    
    def analyze_network_failure(self, test_results):
        """分析網路故障原因"""
        analysis = []
        
        ping_results = test_results['ping_results']
        successful_pings = sum(1 for result in ping_results.values() if result)
        
        if successful_pings == 0:
            analysis.append("所有主機 Ping 測試失敗")
        elif successful_pings < len(ping_results):
            analysis.append(f"部分主機 Ping 失敗 ({successful_pings}/{len(ping_results)})")
        
        if not test_results['dns_test']:
            analysis.append("DNS 解析失敗")
        
        return "; ".join(analysis) if analysis else "網路故障原因不明"

    def restart_computer(self):
        """重新啟動電腦（無需使用者確認）"""
        self.log_message(f"準備重新啟動電腦 (第 {self.reboot_count + 1} 次)", "WARNING")
        # 直接累加計數並記錄時間
        self.reboot_count += 1
        self.last_reboot_time = datetime.datetime.now()
        self.save_reboot_count()
        try:
            if sys.platform.startswith('win'):
                # 若要立刻重啟可將 '10' 改成 '0'
                subprocess.run(['shutdown','/r','/t','10','/c','網路監控器自動重啟'], check=True, startupinfo=_win_startupinfo_and_flags()[0], creationflags=_win_startupinfo_and_flags()[1])
            else:
                subprocess.run(['sudo','reboot'], check=True, startupinfo=_win_startupinfo_and_flags()[0], creationflags=_win_startupinfo_and_flags()[1])
            self.log_message("重啟命令已執行", "INFO")
        except subprocess.CalledProcessError as e:
            self.log_message(f"重啟失敗: {e}", "ERROR")
        except Exception as e:
            self.log_message(f"重啟過程中發生錯誤: {e}", "ERROR")

    
    def update_status_display(self):
        """更新狀態顯示"""
        # 更新網路狀態
        if self.current_status['network_ok']:
            self.network_status_label.config(text="正常", foreground="green")
        else:
            self.network_status_label.config(text="異常", foreground="red")
        
        # 更新遠端軟體狀態
        if self.current_status['remote_active']:
            processes_text = ", ".join(self.current_status['remote_processes'][:3])  # 只顯示前3個
            if len(self.current_status['remote_processes']) > 3:
                processes_text += "..."
            self.remote_status_label.config(text=f"運行中 ({processes_text})", foreground="green")
        else:
            self.remote_status_label.config(text="未運行", foreground="red")
        
        # 更新監控狀態
        if self.is_monitoring:
            self.monitor_status_label.config(text="監控中", foreground="green")
        else:
            self.monitor_status_label.config(text="已停止", foreground="red")
        
        # 更新最後檢查時間
        if self.current_status['last_check']:
            self.last_check_label.config(text=self.current_status['last_check'].strftime("%H:%M:%S"))
        
        # 更新重啟計數
        self.reboot_count_label.config(text=f"{self.reboot_count}/{self.max_reboots}")
        if self.reboot_count >= self.max_reboots:
            self.reboot_count_label.config(foreground="red")
        else:
            self.reboot_count_label.config(foreground="black")
    
    def monitoring_loop(self):
        """監控循環"""
        consecutive_failures = 0
        
        while self.is_monitoring:
            try:
                # 檢查是否有遠端軟體運行
                remote_active, remote_processes = self.is_remote_software_running()
                self.current_status['remote_active'] = remote_active
                self.current_status['remote_processes'] = remote_processes
                self.current_status['last_check'] = datetime.now()
                
                if not remote_active:
                    self.log_message("未檢測到遠端軟體運行，跳過本次檢查", "DEBUG")
                    consecutive_failures = 0
                    time.sleep(self.check_interval)
                    continue
                
                self.log_message(f"檢測到遠端軟體運行: {', '.join(remote_processes)}", "INFO")
                
                # 檢查網路連線
                test_results = self.check_network_connectivity()
                self.current_status['network_ok'] = test_results['overall_status']
                
                if test_results['overall_status']:
                    if consecutive_failures > 0:
                        self.log_message("網路連線已恢復", "INFO")
                    consecutive_failures = 0
                else:
                    consecutive_failures += 1
                    failure_analysis = self.analyze_network_failure(test_results)
                    
                    self.log_message(f"網路連線失敗 (連續 {consecutive_failures} 次)", "WARNING")
                    self.log_message(f"故障分析: {failure_analysis}", "WARNING")
                    
                    # 如果連續失敗次數達到閾值且未超過重啟限制
                    if (consecutive_failures >= self.failure_threshold and 
                        self.reboot_count < self.max_reboots):
                        
                        # 檢查冷卻時間
                        if (self.last_reboot_time is None or 
                            datetime.now() - self.last_reboot_time > timedelta(seconds=self.reboot_cooldown)):
                            
                            self.log_message(f"網路持續斷線，準備執行自動重啟", "CRITICAL")
                            self.root.after(0, self.restart_computer)  # 在主線程中執行
                        else:
                            remaining_cooldown = self.reboot_cooldown - (datetime.now() - self.last_reboot_time).seconds
                            self.log_message(f"重啟冷卻中，剩餘 {remaining_cooldown} 秒", "INFO")
                    
                    elif self.reboot_count >= self.max_reboots:
                        self.log_message(f"已達到最大重啟次數 ({self.max_reboots})，停止自動重啟", "CRITICAL")
                
                self.current_status['consecutive_failures'] = consecutive_failures
                time.sleep(self.check_interval)
                
            except Exception as e:
                self.log_message(f"監控過程中發生錯誤: {e}", "ERROR")
                time.sleep(self.check_interval)
    
    def start_status_thread(self):
        """啟動狀態更新線程"""
        def status_update_loop():
            while True:
                self.root.after(0, self.update_status_display)
                time.sleep(1)  # 每秒更新一次顯示
        
        status_thread = threading.Thread(target=status_update_loop, daemon=True)
        status_thread.start()
    
    def perform_initial_check(self):
        """執行初始檢測"""
        def initial_check_thread():
            try:
                # 檢查遠端軟體
                remote_active, remote_processes = self.is_remote_software_running()
                self.current_status['remote_active'] = remote_active
                self.current_status['remote_processes'] = remote_processes
                
                # 檢查網路連線
                test_results = self.check_network_connectivity()
                self.current_status['network_ok'] = test_results['overall_status']
                self.current_status['last_check'] = datetime.now()
                
                # 記錄檢測結果
                if remote_active:
                    self.root.after(0, lambda: self.log_message(f"檢測到遠端軟體: {', '.join(remote_processes)}", "INFO"))
                else:
                    self.root.after(0, lambda: self.log_message("未檢測到遠端軟體運行", "INFO"))
                
                if test_results['overall_status']:
                    self.root.after(0, lambda: self.log_message("網路連線正常", "INFO"))
                else:
                    failure_analysis = self.analyze_network_failure(test_results)
                    self.root.after(0, lambda: self.log_message(f"網路檢測異常: {failure_analysis}", "WARNING"))
                
            except Exception as e:
                self.root.after(0, lambda: self.log_message(f"初始檢測失敗: {e}", "ERROR"))
        
        # 在背景執行初始檢測
        threading.Thread(target=initial_check_thread, daemon=True).start()
    
    def start_monitoring(self):
        """開始監控"""
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        self.log_message("開始網路監控", "INFO")
        
        # 更新按鈕狀態
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        
        # 啟動監控線程
        self.monitor_thread = threading.Thread(target=self.monitoring_loop, daemon=True)
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """停止監控"""
        if not self.is_monitoring:
            return
        
        self.is_monitoring = False
        self.log_message("停止網路監控", "INFO")
        
        # 更新按鈕狀態
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
    
    def reset_reboot_count(self):
        """重置重啟計數器"""
        if messagebox.askyesno("確認重置", "確定要重置重啟計數器嗎？"):
            self.reboot_count = 0
            self.last_reboot_time = None
            self.save_reboot_count()
            self.log_message("重啟計數器已重置", "INFO")
    
    def apply_settings(self):
        """應用設定"""
        try:
            new_interval = int(self.interval_var.get())
            new_max_reboots = int(self.max_reboots_var.get())
            
            if new_interval < 10:
                messagebox.showerror("設定錯誤", "檢查間隔不能小於10秒")
                return
            
            if new_max_reboots < 0 or new_max_reboots > 10:
                messagebox.showerror("設定錯誤", "最大重啟次數必須在0-10之間")
                return
            
            self.check_interval = new_interval
            self.max_reboots = new_max_reboots
            
            self.log_message(f"設定已更新: 檢查間隔={new_interval}秒, 最大重啟次數={new_max_reboots}", "INFO")
            messagebox.showinfo("設定成功", "設定已成功更新")
            
        except ValueError:
            messagebox.showerror("設定錯誤", "請輸入有效的數字")
    
    def test_connection_manual(self):
        """手動測試連線"""
        self.log_message("開始手動測試連線...", "INFO")
        
        # 在另一個線程中執行測試，避免阻塞GUI
        def test_thread():
            test_results = self.check_network_connectivity()
            remote_active, remote_processes = self.is_remote_software_running()
            
            self.root.after(0, lambda: self.log_message(f"網路狀態: {'正常' if test_results['overall_status'] else '異常'}", "INFO"))
            self.root.after(0, lambda: self.log_message(f"遠端軟體: {'運行中' if remote_active else '未運行'}", "INFO"))
            
            if remote_processes:
                self.root.after(0, lambda: self.log_message(f"檢測到的遠端軟體: {', '.join(remote_processes)}", "INFO"))
            
            if not test_results['overall_status']:
                failure_analysis = self.analyze_network_failure(test_results)
                self.root.after(0, lambda: self.log_message(f"故障分析: {failure_analysis}", "WARNING"))
        
        threading.Thread(target=test_thread, daemon=True).start()
    
    def run(self):
        """運行GUI"""
        self.log_message("網路監控器 GUI 已啟動", "INFO")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()
    
    def on_closing(self):
        # Instead of closing, hide to system tray
        try:
            self.root.withdraw()
            if hasattr(self, 'tray_icon') and self.tray_icon is not None:
                try:
                    self.tray_icon.notify('程式已縮小到系統匣；從右下角圖示喚回。')
                except Exception:
                    pass
            return
        except Exception:
            # If anything goes wrong, fallback to original close flow
            if self.is_monitoring:
                self.stop_monitoring()
            try:
                self.root.destroy()
            except Exception:
                pass
        if self.is_monitoring:
            if messagebox.askokcancel("關閉程式", "監控正在進行中，確定要關閉程式嗎？"):
                self.stop_monitoring()
                time.sleep(1)  # 等待監控線程結束
                self.root.destroy()
        else:
            self.root.destroy()


if __name__ == "__main__":
    try:
        app = NetworkMonitorGUI()
        app.run()
    except Exception as e:
        print(f"程式啟動失敗: {e}")
        messagebox.showerror("啟動錯誤", f"程式啟動失敗: {e}")

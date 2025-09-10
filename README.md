# 網路監控器

這是一個用於監控網路連線狀態的 Python 程式，當檢測到遠端軟體運行時，會自動監控網路連線，並在網路斷線時嘗試自動重新開機修復問題。

## 功能特色

-  **智能檢測**: 只在遠端軟體運行時啟動監控
-  **自動重啟**: 網路斷線時自動重新開機修復
-  **詳細日誌**: 完整記錄網路狀態和故障分析
-  **限制保護**: 防止無限重啟，設有次數和時間限制
-  **安全機制**: 冷卻時間防止頻繁重啟
-  **廣泛支援**: 支援 TeamViewer、AnyDesk、Parsec 等主流遠端軟體
-  **GUI介面**: 直觀的圖形介面，即時監控狀態
-  **測試工具**: 內建檢測工具確保功能正常

## 檔案說明

- `network_monitor_gui.py` - **🌟 GUI圖形介面版本（強烈推薦）**
- `network_monitor_simple.py` - 簡化版本（僅使用標準庫）
- `network_monitor.py` - 完整版本（需要安裝額外套件）
- `test_detection.py` - **🧪 檢測測試工具（建議先運行）**
- `config.json` - 配置檔案
- `start_gui.bat` - GUI版本啟動器（自動獲取管理員權限）
- `start_monitor.bat` - 命令行版本啟動器
- `requirements.txt` - 完整版本依賴套件
- `requirements_simple.txt` - 簡化版本說明
- `GUI_使用說明.md` - GUI詳細使用指南

## 快速開始

### 🧪 第一步：檢測測試（建議）

在使用監控器前，建議先運行檢測工具確認系統狀態：

```powershell
python test_detection.py
```

此工具會檢測：
- 當前運行的遠端軟體
- 網路連線狀態
- 系統相容性

### 🚀 第二步：選擇使用方式

#### 方法一：GUI圖形介面版本（🌟 強烈推薦）

GUI版本提供直觀的圖形介面，方便監控和控制：

```powershell
# 直接運行
python network_monitor_gui.py

# 或使用啟動器（自動獲取管理員權限）
start_gui.bat
```

**GUI版本特色：**
- 🖥️ 直觀的圖形介面
- 📊 即時狀態顯示
- 🎛️ 簡單的設定調整
- 📝 內建日誌查看器
- 🔘 一鍵操作控制
- 🚀 初始化自動檢測

#### 方法二：簡化命令行版本

簡化版本僅使用 Python 標準庫，無需安裝額外套件：

```powershell
python network_monitor_simple.py
```

#### 方法三：完整命令行版本

1. 安裝依賴套件：
```powershell
pip install -r requirements.txt
```

2. 運行程式：
```powershell
python network_monitor.py
```

## GUI版本功能說明

### 主要介面區域

**狀態顯示區域：**
- 網路連線狀態（正常/異常）
- 遠端軟體運行狀態
- 監控狀態（監控中/已停止）
- 最後檢查時間
- 重啟次數統計

**控制按鈕：**
- **開始監控**: 啟動自動監控
- **停止監控**: 停止監控
- **重置計數器**: 重置重啟次數計數器
- **測試連線**: 手動測試網路連線狀態

**設定區域：**
- 檢查間隔：設定監控的時間間隔（秒）
- 最大重啟次數：設定允許的最大自動重啟次數
- 應用設定：保存設定變更

**日誌顯示：**
- 即時顯示監控日誌
- 清除日誌功能
- 自動滾動到最新訊息

### 狀態指示器

- 🟢 **綠色**: 正常狀態
- 🔴 **紅色**: 異常或停止狀態
- 🟡 **橙色**: 檢查中或警告狀態

### 安全機制

- 重啟前會顯示確認對話框
- 關閉程式前會檢查監控狀態
- 防止意外操作的多重確認

## 配置說明

可以修改 `config.json` 檔案來調整監控參數：

```json
{
    "max_reboots": 2,                    // 最大重啟次數
    "check_interval": 30,                // 檢查間隔（秒）
    "log_file": "network_monitor.log",   // 日誌檔案名稱
    "reboot_cooldown": 3600,             // 重啟冷卻時間（秒）
    "test_hosts": [                      // 測試連線的主機
        "8.8.8.8",
        "1.1.1.1",
        "google.com"
    ],
    "remote_software_processes": [        // 要檢測的遠端軟體進程
        "teamviewer.exe",
        "anydesk.exe",
        "parsec.exe",
        "parsecd.exe",
        "chrome_remote_desktop.exe",
        "mstsc.exe",
        "rdpclip.exe",
        "rustdesk.exe",
        "nomachine"
    ],
    "ping_timeout": 5,                   // Ping 超時時間（秒）
    "connection_failures_threshold": 3    // 連續失敗閾值
}
```

## 網路檢測優化 🌐

### 智能檢測邏輯
- **多主機測試**: 同時測試 Google DNS (8.8.8.8)、Cloudflare DNS (1.1.1.1) 和 google.com
- **寬鬆標準**: 只要30%的Ping成功或DNS解析正常即視為網路正常
- **快速反應**: 減少誤判，提高檢測準確性

### 故障分析
程式會自動分析網路故障原因：
- Ping 失敗分析
- DNS 解析問題檢測
- 網路介面卡狀態檢查
- 詳細故障報告記錄

## 支援的遠端軟體 🎯

程式已優化檢測以下遠端軟體（2025年9月更新）：

### 主流遠端軟體
- **TeamViewer** (`teamviewer.exe`)
- **AnyDesk** (`anydesk.exe`) 
- **Parsec** (`parsec.exe`, `parsecd.exe`) - ⭐ 新增支援
- **Chrome Remote Desktop** (`chrome_remote_desktop.exe`)
- **RustDesk** (`rustdesk.exe`) - ⭐ 新增支援
- **NoMachine** (`nomachine`) - ⭐ 新增支援

### 系統內建
- **Windows 遠端桌面** (`mstsc.exe`, `rdpclip.exe`)
- **VNC** (`vnc`)
- **Radmin** (`radmin`)

### 檢測改進
- ✅ 更精確的進程名稱匹配
- ✅ 支援多進程檢測（如 Parsec 的主程式和後台程式）
- ✅ 跨平台相容性（Windows/Linux/Mac）

## 工具集說明 🧰

### 主程式
- `network_monitor_gui.py` - GUI版本（推薦新手使用）
- `network_monitor_simple.py` - 簡化版本（輕量化）
- `network_monitor.py` - 完整版本（功能最豐富）

### 輔助工具
- `test_detection.py` - **檢測測試工具**
  - 檢測當前運行的遠端軟體
  - 測試網路連線狀態
  - 驗證程式相容性
  - 生成詳細報告

### 啟動器
- `start_gui.bat` - 自動獲取管理員權限啟動GUI
- `start_monitor.bat` - 命令行版本啟動器

### 說明文件
- `README.md` - 主要說明文件
- `GUI_使用說明.md` - GUI詳細操作指南

## 注意事項 ⚠️

### 重要提醒
1. **管理員權限**: 在 Windows 上執行重啟操作需要管理員權限
2. **防毒軟體**: 某些防毒軟體可能會阻擋重啟操作，請加入白名單
3. **網路環境**: 確保測試主機（8.8.8.8 等）在您的網路環境中可達
4. **遠端軟體**: 確保遠端軟體正在運行且進程名稱正確

### 使用建議
- 🧪 **首次使用前請先運行檢測工具** (`test_detection.py`)
- 🔒 **建議使用 `start_gui.bat` 自動獲取管理員權限**
- 📝 **定期檢查日誌了解系統狀態**
- ⚡ **避免在系統繁忙時啟動監控**

### 安全機制
- 重啟前會顯示確認對話框（GUI版本）
- 最大重啟次數限制（預設2次）
- 重啟冷卻時間（預設1小時）
- 只在檢測到遠端軟體時才啟動監控

## 停止監控 🛑

### GUI版本
- 點擊「停止監控」按鈕
- 或直接關閉視窗（會有確認提示）

### 命令行版本
- 按 `Ctrl+C` 安全停止監控程式

## 重置功能 🔄

### 重置重啟計數器
如果需要重置重啟計數器，可以刪除以下檔案：
```powershell
# 完整版本
del reboot_count.json

# 簡化版本  
del simple_reboot_count.json

# GUI版本
del gui_reboot_count.json
```

### 重置設定
- 刪除 `config.json` 重新生成預設設定
- 或直接在GUI中調整設定並應用

## 故障排除 🔧

### 常見問題

#### 1. 程式無法檢測到遠端軟體
**解決方案:**
- 運行 `python test_detection.py` 檢查檢測狀態
- 確認遠端軟體正在運行
- 檢查進程名稱是否在支援列表中
- 嘗試重新啟動遠端軟體

#### 2. 網路檢測顯示異常但實際正常
**解決方案:**
- 運行測試工具確認網路狀態
- 檢查防火牆設定是否阻擋Ping
- 確認DNS設定正確
- 嘗試更換測試主機列表

#### 3. 重啟命令失敗
**解決方案:**
- 確保以管理員身份運行程式
- 檢查系統權限設定
- 確認防毒軟體未阻擋操作

#### 4. GUI介面無法啟動
**解決方案:**
- 確認Python版本支援tkinter
- 檢查是否有圖形界面環境
- 嘗試使用命令行版本

### 偵錯步驟

1. **先運行檢測工具:**
   ```powershell
   python test_detection.py
   ```

2. **檢查日誌檔案:**
   - GUI版本: 程式內建日誌檢視器
   - 命令行版本: 查看 `.log` 檔案

3. **重置計數器:**
   ```powershell
   # 刪除重啟計數檔案
   del *reboot_count.json
   ```

4. **測試網路連線:**
   - 使用程式內建的「測試連線」功能
   - 手動ping測試主機確認網路狀態

## 版本歷史 📅

### v1.1 (2025-09-10) - 最新版本
- ✅ **新增 Parsec 支援** - 支援 `parsec.exe` 和 `parsecd.exe`
- ✅ **新增 RustDesk 支援** - 開源遠端桌面軟體
- ✅ **新增 NoMachine 支援** - 企業級遠端軟體
- ✅ **優化網路檢測邏輯** - 降低誤判率，提高準確性
- ✅ **新增檢測測試工具** - `test_detection.py` 診斷工具
- ✅ **改善GUI初始化** - 啟動時自動檢測狀態
- ✅ **更新說明文件** - 完整的使用指南

### v1.0 (2025-08-29)
- 🎉 初始版本發布
- ✅ 基本網路監控功能
- ✅ 自動重啟機制
- ✅ GUI圖形介面
- ✅ 多版本支援（GUI/簡化/完整）

**💡 小提示**: 建議先使用檢測工具確認系統狀態，再啟動監控功能，這樣可以避免大部分的問題！

---
## 📄 授權

本專案採用 MIT 授權條款 [MIT License](https://github.com/kuroneko11375/NetworkMonitor/blob/main/LICENSE).


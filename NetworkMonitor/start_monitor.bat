@echo off
echo 網路監控器啟動器
echo ==================

:: 檢查是否以管理員身份運行
net session >nul 2>&1
if %errorLevel% == 0 (
    echo 已獲得管理員權限，啟動監控器...
    echo.
    python network_monitor_simple.py
) else (
    echo 需要管理員權限才能執行重啟操作
    echo 正在以管理員身份重新啟動...
    powershell -Command "Start-Process cmd -ArgumentList '/c cd /d %cd% && %0' -Verb RunAs"
)

pause

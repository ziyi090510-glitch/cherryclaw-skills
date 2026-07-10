@echo off
REM VNC 网关自动启动脚本
REM 注册到 Windows 任务计划程序或启动文件夹

set PYTHON=C:\Program Files\Python312\python.exe
set SCRIPT=C:\Users\Administrator\Desktop\vnc_gateway.py
set LOG=C:\Users\Administrator\Desktop\vnc_gateway_watchdog.log

echo [%date% %time%] Starting VNC Gateway... >> %LOG%

:: 杀旧进程
for /f "tokens=2 delims=," %%a in ('tasklist /fi "imagename eq python.exe" /fo csv ^| findstr "vnc_gateway"') do (
    taskkill /F /PID %%a >nul 2>&1
)
timeout /t 2 /nobreak >nul

:: 启动
start /B "" "%PYTHON%" "%SCRIPT%"
echo [%date% %time%] VNC Gateway started on port 5098 >> %LOG%

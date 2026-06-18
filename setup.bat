@echo off
chcp 65001 >nul
echo ========================================
echo  黄金数据日报 - Windows 计划任务安装
echo ========================================
echo.

set PROJECT_DIR=D:\gold-daily-report
set PYTHON_PATH=python

echo 安装 Python 依赖...
pip install -r "%PROJECT_DIR%\requirements.txt"

echo.
echo 创建计划任务（每天 9:00、17:00 推送）...
schtasks /create /tn "GoldDailyReportMorning" /tr "%PYTHON_PATH% %PROJECT_DIR%\main.py" /sc daily /st 09:00 /f
schtasks /create /tn "GoldDailyReportAfternoon" /tr "%PYTHON_PATH% %PROJECT_DIR%\main.py" /sc daily /st 17:00 /f

echo.
echo ========================================
echo  ✅ 计划任务创建完成！
echo     每天 9:00 / 17:00 自动推送黄金日报
echo.
echo  手动运行测试：python %PROJECT_DIR%\main.py
echo ========================================
pause

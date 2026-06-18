@echo off
cd /d D:\gold-daily-report
git add --all
git commit -m "chore: cleanup"
git push origin master
del "%~f0"

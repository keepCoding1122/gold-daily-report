@echo off
cd /d D:\gold-daily-report
git add --all
git commit -m "fix: KeyError crash + add AI summary + optimize layout"
git push origin master

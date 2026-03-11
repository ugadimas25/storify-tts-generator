@echo off
cd /d "D:\b_outside\a_intesa_global_technology\Storify\Storify-Insights\api\ai-audiobook-agent"
C:\Users\Dimas\.conda\envs\tts-generator\python.exe -m src.social.daily_poster >> logs\poster.log 2>&1

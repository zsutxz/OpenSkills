@echo off
rem Daily 08:00 trigger by Task Scheduler task LLM-AI-Daily-Digest
rem Log: E:\AI\LLMWiki-Repo\agent-workspace\digest-run.log (check here first when troubleshooting)
set "LOGDIR=E:\AI\LLMWiki-Repo\agent-workspace"
if not exist "%LOGDIR%" mkdir "%LOGDIR%"
set "LOGFILE=%LOGDIR%\digest-run.log"
echo ================================================== >> "%LOGFILE%"
echo [%date% %time%] digest run start >> "%LOGFILE%"
cd /d E:\AI\HeAgent
C:\Users\skype\AppData\Roaming\npm\claude.cmd -p "Run skill llm-ai-daily-digest to produce today's LLM / AI Agent daily digest. Unattended mode: follow all skill steps (arXiv fetch and parse, Weibo attempt, digest write and rotation, star-paper download with abstract translation, community article download on demand). Mark unavailable sources honestly. At the end output the list of produced files." --allowedTools "Bash Read Write Glob Grep WebFetch WebSearch mcp__web_reader__webReader Skill" >> "%LOGFILE%" 2>&1
echo [%date% %time%] digest run end, exit=%ERRORLEVEL% >> "%LOGFILE%"

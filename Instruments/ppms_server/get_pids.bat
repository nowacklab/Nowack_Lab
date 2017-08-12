::First save current pids with the wanted process name
setlocal EnableExtensions EnableDelayedExpansion
set PROCESSNAME=ipy.exe
set "OLDPIDS=p"
for /f "TOKENS=1" %%a in ('wmic PROCESS where "Name='%PROCESSNAME%'" get ProcessID ^| findstr [0-9]') do (set "OLDPIDS=!OLDPIDS!%%ap")

echo %OLDPIDS%
endlocal

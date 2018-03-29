:: Arg %1 is list of PIDs obtained by get_pids.bat.
:: This script compares them to the current PIDs to see which process was opened.

setlocal EnableExtensions EnableDelayedExpansion
set "RETPIDS="
set OLDPIDS=%1
set PROCESSNAME=ipy.exe

::Check and find processes missing in the old pid list
for /f "TOKENS=1" %%a in ('wmic PROCESS where "Name='%PROCESSNAME%'" get ProcessID ^| findstr [0-9]') do (
if "!OLDPIDS:p%%ap=zz!"=="%OLDPIDS%" (set "RETPIDS=/PID %%a !RETPIDS!")
)

echo %RETPIDS%
endlocal
exit

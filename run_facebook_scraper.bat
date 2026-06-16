@echo off
setlocal

REM ==========================================
REM DATE/TIME LOG FOLDER
REM ==========================================

for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value ^| find "="') do set dt=%%I

set YYYY=%dt:~0,4%
set MM=%dt:~4,2%
set DD=%dt:~6,2%
set HH=%dt:~8,2%
set MIN=%dt:~10,2%
set SS=%dt:~12,2%

set LOGDIR=logs
if not exist "%LOGDIR%" mkdir "%LOGDIR%"

set LOGFILE=%LOGDIR%\facebook_scraper_%YYYY%-%MM%-%DD%_%HH%-%MIN%-%SS%.log

echo ========================================== > "%LOGFILE%"
echo FACEBOOK SCRAPER STARTED >> "%LOGFILE%"
echo DATE: %DATE% %TIME% >> "%LOGFILE%"
echo ========================================== >> "%LOGFILE%"

REM ==========================================
REM CHANGE TO PROJECT DIRECTORY
REM ==========================================

cd /d "D:\Facebook_Project"

REM ==========================================
REM RUN URL COLLECTION
REM ==========================================

echo. >> "%LOGFILE%"
echo ========================================== >> "%LOGFILE%"
echo RUNNING collect_urls_photo.py >> "%LOGFILE%"
echo ========================================== >> "%LOGFILE%"

python collect_urls_photo.py >> "%LOGFILE%" 2>&1

if errorlevel 1 (
    echo ERROR IN collect_urls_photo.py >> "%LOGFILE%"
    goto END
)

REM ==========================================
REM RUN FACEBOOK SCRAPER
REM ==========================================

echo. >> "%LOGFILE%"
echo ========================================== >> "%LOGFILE%"
echo RUNNING scraping_facebook.py >> "%LOGFILE%"
echo ========================================== >> "%LOGFILE%"

python scraping_facebook.py >> "%LOGFILE%" 2>&1

if errorlevel 1 (
    echo ERROR IN scraping_facebook.py >> "%LOGFILE%"
    goto END
)

:END

echo. >> "%LOGFILE%"
echo ========================================== >> "%LOGFILE%"
echo PROCESS COMPLETED >> "%LOGFILE%"
echo DATE: %DATE% %TIME% >> "%LOGFILE%"
echo ========================================== >> "%LOGFILE%"

echo.
echo Finished.
echo Log File:
echo %LOGFILE%

pause
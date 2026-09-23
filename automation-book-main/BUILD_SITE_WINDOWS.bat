@echo off
if defined AUTOMATION_BOOK_BUILD_INNER goto :inner_build
setlocal
set "AUTOMATION_BOOK_BUILD_INNER=1"
call "%~f0" %*
set "AUTOMATION_BOOK_BUILD_RESULT=%ERRORLEVEL%"
echo.
if not "%AUTOMATION_BOOK_BUILD_RESULT%"=="0" echo The build stopped with error code %AUTOMATION_BOOK_BUILD_RESULT%.
echo The window will remain open so you can read or copy the complete output.
choice /C X /N /M "Press X to close this window: "
exit /b %AUTOMATION_BOOK_BUILD_RESULT%

:inner_build
setlocal
chcp 65001 >nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

set "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"

if not "%~1"=="" (
  set "WORD_FILE=%~1"
) else (
  set "WORD_FILE=%PROJECT_DIR%private-source\Automation_book4Aug2026.docx"
)

if not defined WORD_FILE goto :missing_word
if not exist "%WORD_FILE%" goto :missing_word

echo.
echo Automation Book build started.
echo Keep this window open. A full rebuild may take several minutes.
echo Word source: %WORD_FILE%
echo.
echo What did you change in Word?
echo   [E] Edit existing questions only
echo   [A] Add questions only
echo   [D] Delete or unpublish questions only
echo   [M] Mixed changes: any combination of Edit, Add, and Delete
choice /C EADM /N /M "Press E, A, D, or M (do not press Enter): "
if errorlevel 4 (
  set "CHANGE_TYPE=mixed"
) else if errorlevel 3 (
  set "CHANGE_TYPE=delete"
) else if errorlevel 2 (
  set "CHANGE_TYPE=add"
) else (
  set "CHANGE_TYPE=edit"
)

if /I "%CHANGE_TYPE%"=="delete" goto :deletion_reminder
if /I "%CHANGE_TYPE%"=="mixed" goto :deletion_reminder_done
goto :deletion_reminder_done

:deletion_reminder
echo.
echo Safe deletion reminder:
echo Keep the styled question heading as an empty draft.
echo Remove the question text, the separate solution marker, and the solution.
echo Do not physically remove a middle heading unless a technical maintainer
echo has checked the resulting renumbering and question-specific figures.
echo.
pause

:deletion_reminder_done
if /I "%CHANGE_TYPE%"=="mixed" (
  echo.
  echo Mixed mode selected. The change summary will list every edited, added,
  echo removed, and possibly renumbered public question.
  echo If the mixed changes include a deletion, keep the old numbered heading
  echo as an empty draft so later questions are not renumbered accidentally.
  echo.
)

where py >nul 2>&1
if %errorlevel%==0 (
  set "PYTHON_CMD=py -3"
) else (
  where python >nul 2>&1
  if errorlevel 1 goto :missing_python
  set "PYTHON_CMD=python"
)

where pandoc >nul 2>&1
if errorlevel 1 goto :missing_pandoc

where soffice >nul 2>&1
if errorlevel 1 (
  if exist "%ProgramFiles%\LibreOffice\program\soffice.exe" (
    set "PATH=%ProgramFiles%\LibreOffice\program;%PATH%"
  ) else if exist "%ProgramFiles(x86)%\LibreOffice\program\soffice.exe" (
    set "PATH=%ProgramFiles(x86)%\LibreOffice\program;%PATH%"
  ) else (
    goto :missing_libreoffice
  )
)

echo.
echo Installing or checking Python packages...
%PYTHON_CMD% -m pip install -r requirements.txt
if errorlevel 1 goto :failed

set "STAGING_ROOT=%TEMP%\automation-book-build-%RANDOM%-%RANDOM%"
set "STAGING_DOCS=%STAGING_ROOT%\docs"
mkdir "%STAGING_DOCS%"
if errorlevel 1 goto :failed
xcopy "%PROJECT_DIR%docs\*" "%STAGING_DOCS%\" /E /I /Q /Y >nul
if errorlevel 1 goto :failed
copy /Y "%PROJECT_DIR%docs\assets\book-data.js" "%STAGING_ROOT%\before-book-data.js" >nul
if errorlevel 1 goto :failed

echo.
echo Building the website from:
echo %WORD_FILE%
%PYTHON_CMD% scripts\build-from-word-semantic.py "%WORD_FILE%" --out "%STAGING_DOCS%"
if errorlevel 1 goto :failed

%PYTHON_CMD% scripts\summarize-question-changes.py ^
  --before "%STAGING_ROOT%\before-book-data.js" ^
  --after "%STAGING_DOCS%\assets\book-data.js" ^
  --operation "%CHANGE_TYPE%"
if errorlevel 1 goto :failed

echo.
echo Validating the generated public website...
%PYTHON_CMD% scripts\validate-book.py --docs "%STAGING_DOCS%"
if errorlevel 1 goto :failed

echo.
echo Replacing docs only after the staged build passed validation...
robocopy "%STAGING_DOCS%" "%PROJECT_DIR%docs" /MIR /NFL /NDL /NJH /NJS /NP >nul
if errorlevel 8 goto :failed
rmdir /S /Q "%STAGING_ROOT%"

echo.
echo ============================================================
echo BUILD AND VALIDATION SUCCEEDED
echo The original docs folder was kept unchanged until validation passed.
echo Check the change summary and every affected question before publishing.
echo ============================================================
start "" "%PROJECT_DIR%docs\index.html"
exit /b 0

:missing_word
echo.
echo ERROR: The Word file was not found.
echo Expected: private-source\Automation_book4Aug2026.docx
echo Or drag another DOCX file onto BUILD_SITE_WINDOWS.bat.
goto :failed_end

:missing_python
echo.
echo ERROR: Python 3 is not installed or is not available in PATH.
goto :failed_end

:missing_pandoc
echo.
echo ERROR: Pandoc is not installed or is not available in PATH.
goto :failed_end

:missing_libreoffice
echo.
echo ERROR: LibreOffice was not found.
echo Install LibreOffice and restart Windows before trying again.
goto :failed_end

:failed
echo.
echo ERROR: BUILD OR VALIDATION FAILED.
if defined STAGING_ROOT echo The existing docs folder was not replaced.
if defined STAGING_ROOT echo Technical files remain in: %STAGING_ROOT%
echo Do not publish. Copy the complete error message for technical support.

:failed_end
exit /b 1

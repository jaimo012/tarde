@echo off
echo 🚀 DART 스크래핑 시스템 배포 시작...
echo.

echo 📁 Git 상태 확인 중...
git status --porcelain > temp_status.txt
set /p status_result=<temp_status.txt
del temp_status.txt

if "%status_result%"=="" (
    echo ✅ 변경사항이 없습니다.
    echo 배포할 내용이 없어 종료합니다.
    pause
    exit /b 0
)

echo 📝 변경된 파일들:
git status --porcelain

echo.
echo 📦 파일 스테이징 중...
git add .
if %errorlevel% neq 0 (
    echo ❌ 파일 스테이징 실패
    pause
    exit /b 1
)

echo ✅ 스테이징 완료

echo.
echo 💾 커밋 생성 중...
git commit -m "feat: smart slack notification system - prevent spam alerts"
if %errorlevel% neq 0 (
    echo ❌ 커밋 실패
    pause
    exit /b 1
)

echo ✅ 커밋 완료

echo.
echo 🌐 GitHub에 푸시 중...
git push origin main
if %errorlevel% neq 0 (
    echo ❌ 푸시 실패
    pause
    exit /b 1
)

echo ✅ 푸시 완료

echo.
echo 📜 최근 커밋 로그:
git log --oneline -5

echo.
echo 🎉 배포가 성공적으로 완료되었습니다!
echo 변경사항이 GitHub에 반영되었습니다.
echo.
pause

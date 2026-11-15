@echo off
setlocal
REM JobBoard Validation 1 - local start (Windows)
REM Requires: JDK 17, Maven on PATH (or set MVN below)

set "MVN=mvn"
if exist "%TEMP%\tools\apache-maven-3.9.9\bin\mvn.cmd" set "MVN=%TEMP%\tools\apache-maven-3.9.9\bin\mvn.cmd"

cd /d "%~dp0"

echo [1/3] Building Java modules...
call %MVN% -DskipTests package
if errorlevel 1 exit /b 1

echo [2/3] Starting Eureka, Config, Gateway, Java MS (H2) and ms-interview (Node)...
start "eureka" cmd /k %MVN% -pl eureka-server spring-boot:run
timeout /t 15 /nobreak >nul
start "config" cmd /k %MVN% -pl config-server spring-boot:run
timeout /t 10 /nobreak >nul
start "gateway" cmd /k %MVN% -pl api-gateway spring-boot:run
start "candidate" cmd /k %MVN% -pl ms-candidate spring-boot:run -Dspring-boot.run.profiles=h2
start "job" cmd /k %MVN% -pl ms-job spring-boot:run -Dspring-boot.run.profiles=h2
start "application" cmd /k %MVN% -pl ms-application spring-boot:run -Dspring-boot.run.profiles=h2
if not exist "%~dp0ms-interview\node_modules" call npm --prefix "%~dp0ms-interview" install
start "interview" cmd /k "cd /d %~dp0ms-interview && npm start"

echo [3/3] Starting ms-notification (Python)...
start "notification" cmd /k "cd /d %~dp0ms-notification && python -m uvicorn app.main:app --port 8085"

echo.
echo Open: Eureka http://localhost:8761
echo       Gateway http://localhost:8080/actuator/health
echo       Candidate http://localhost:8081/actuator/health
echo       Interview http://localhost:8084/health
echo       Notification http://localhost:8085/actuator/health
endlocal

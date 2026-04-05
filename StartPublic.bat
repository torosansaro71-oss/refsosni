@echo off
title Roblox Cookie Refresher - PUBLIC
color 0b

echo Starting local server on port 5000...
start /b python server.py >nul 2>&1

echo.
echo ========================================================
echo GENERATING PUBLIC LINK (This might take a few seconds)
echo ========================================================
echo.
echo Please wait for the link to appear below (it will look like https://something.lhr.life).
echo Send that link to your friends, and they can use your tool!
echo.
echo Press CTRL+C when you want to stop the server.
echo.

ssh -o StrictHostKeyChecking=accept-new -R 80:localhost:5000 nokey@localhost.run

pause

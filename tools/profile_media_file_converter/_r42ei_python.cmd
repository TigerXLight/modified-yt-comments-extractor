@echo off
setlocal
py -3 %*
if errorlevel 1 python %*

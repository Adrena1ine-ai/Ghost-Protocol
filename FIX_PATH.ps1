# Скрипт для добавления Python Scripts в PATH

# Получаем правильный путь
$scriptsPath = "C:\Users\Antaras\AppData\Roaming\Python\Python314\Scripts"

# Проверяем, существует ли папка
if (Test-Path $scriptsPath) {
    Write-Host "✅ Папка найдена: $scriptsPath" -ForegroundColor Green
    
    # Добавляем в PATH временно (для текущей сессии)
    $env:Path += ";$scriptsPath"
    Write-Host "✅ PATH обновлен для текущей сессии" -ForegroundColor Green
    
    # Добавляем в PATH постоянно
    $currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if ($currentPath -notlike "*$scriptsPath*") {
        [Environment]::SetEnvironmentVariable("Path", "$currentPath;$scriptsPath", "User")
        Write-Host "✅ PATH обновлен постоянно (требуется перезапуск PowerShell)" -ForegroundColor Green
    } else {
        Write-Host "ℹ️ PATH уже содержит этот путь" -ForegroundColor Yellow
    }
    
    # Проверяем команду
    Write-Host "`nПроверка команды ghost:" -ForegroundColor Cyan
    & "$scriptsPath\ghost.exe" --help
    
} else {
    Write-Host "❌ Папка не найдена: $scriptsPath" -ForegroundColor Red
    Write-Host "Проверьте установку пакета: pip install ghost-protocol" -ForegroundColor Yellow
}

Write-Host "`n⚠️ ВАЖНО: Перезапустите PowerShell, чтобы изменения вступили в силу!" -ForegroundColor Yellow


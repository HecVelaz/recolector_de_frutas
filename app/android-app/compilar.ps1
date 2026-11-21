param([switch]$Pruebas)

$ErrorActionPreference = 'Stop'
$env:JAVA_HOME = 'C:\Program Files\Android\Android Studio\jbr'
if (-not (Test-Path -LiteralPath "$env:JAVA_HOME\bin\java.exe")) {
    throw 'No se encontró el JDK de Android Studio. Revisá JAVA_HOME en compilar.ps1.'
}
Push-Location $PSScriptRoot
$originalTaskPath = $env:Path
try {
    # Una comilla suelta en el PATH de Windows rompe el proceso Java de pruebas.
    # Se normaliza solo en este proceso, sin cambiar la configuracion del equipo.
    $env:Path = $env:Path.Replace('"', '')
    $gradleTasks = @(':app:assembleDebug', ':app:lintDebug')
    # Un daemon ya abierto conserva java.library.path del PATH anterior.
    if ($Pruebas) { $gradleTasks += @(':app:testDebugUnitTest', '--no-daemon') }
    & .\gradlew.bat @gradleTasks --console=plain
    if ($LASTEXITCODE -ne 0) { throw "Gradle terminó con código $LASTEXITCODE" }
} finally {
    $env:Path = $originalTaskPath
    Pop-Location
}

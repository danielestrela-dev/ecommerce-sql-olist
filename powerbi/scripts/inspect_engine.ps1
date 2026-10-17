param([string]$WorkspaceRoot)
$ErrorActionPreference = 'Stop'
$pbiBin = 'C:\Program Files\Microsoft Power BI Desktop\bin'
Add-Type -Path (Join-Path $pbiBin 'Microsoft.AnalysisServices.Server.Core.dll')
Add-Type -Path (Join-Path $pbiBin 'Microsoft.AnalysisServices.Server.Tabular.dll')
Add-Type -Path (Join-Path $pbiBin 'Microsoft.AnalysisServices.Server.Tabular.Json.dll')
$workspaces = if ($WorkspaceRoot) { $WorkspaceRoot } else { Join-Path $env:LOCALAPPDATA 'Microsoft\Power BI Desktop\AnalysisServicesWorkspaces' }
Get-ChildItem -LiteralPath $workspaces -Recurse -Filter msmdsrv.port.txt | ForEach-Object {
    $enginePort = (Get-Content -LiteralPath $_.FullName -Encoding Unicode -Raw).Trim()
    try {
        $engineServer = New-Object Microsoft.AnalysisServices.Tabular.Server
        $engineServer.Connect("Data Source=localhost:$enginePort")
        foreach ($engineDatabase in $engineServer.Databases) {
            [pscustomobject]@{Port=$enginePort;Id=$engineDatabase.ID;Name=$engineDatabase.Name;Tables=($engineDatabase.Model.Tables.Name -join ',')}
        }
        $engineServer.Disconnect()
    } catch { Write-Output "Port $enginePort : $($_.Exception.Message)" }
}

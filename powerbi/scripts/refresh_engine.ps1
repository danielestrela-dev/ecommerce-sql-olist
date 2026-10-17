param([Parameter(Mandatory=$true)][string]$EnginePort,[Parameter(Mandatory=$true)][string]$DatabaseId)
$ErrorActionPreference = 'Stop'
$pbiBin = 'C:\Program Files\Microsoft Power BI Desktop\bin'
Add-Type -Path (Join-Path $pbiBin 'Microsoft.AnalysisServices.Server.Core.dll')
Add-Type -Path (Join-Path $pbiBin 'Microsoft.AnalysisServices.Server.Tabular.dll')
Add-Type -Path (Join-Path $pbiBin 'Microsoft.AnalysisServices.Server.Tabular.Json.dll')
$engineServer = New-Object Microsoft.AnalysisServices.Tabular.Server
$engineServer.Connect("Data Source=localhost:$EnginePort")
$engineDatabase = @($engineServer.Databases) | Where-Object { $_.ID -eq $DatabaseId }
if (($engineDatabase.Model.Tables.Name -join ',') -ne 'FatoPedidos,DimCalendario,DimEstado') { throw 'Modelo inesperado' }
$engineDatabase.Model.RequestRefresh([Microsoft.AnalysisServices.Tabular.RefreshType]::Full)
$engineDatabase.Model.SaveChanges()
Write-Output 'Atualizacao completa concluida.'
$engineServer.Disconnect()

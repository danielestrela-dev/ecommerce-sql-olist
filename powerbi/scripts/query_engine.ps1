param([Parameter(Mandatory=$true)][string]$EnginePort,[Parameter(Mandatory=$true)][string]$DatabaseId,[string]$DaxQueryPath)
$ErrorActionPreference = 'Stop'
$pbiBin = 'C:\Program Files\Microsoft Power BI Desktop\bin'
Add-Type -Path (Join-Path $pbiBin 'Microsoft.PowerBI.AdomdClient.dll')
$modelConnection = New-Object Microsoft.AnalysisServices.AdomdClient.AdomdConnection("Data Source=localhost:$EnginePort;Initial Catalog=$DatabaseId")
$modelConnection.Open()
$modelCommand = $modelConnection.CreateCommand()
$modelCommand.CommandText = 'EVALUATE ROW("Pedidos", [Pedidos], "Entregues", [Pedidos entregues], "Vendas", [Vendas (R$)], "Ticket", [Ticket medio (R$)], "Cancelados", [Pedidos cancelados], "Cancelamento", [Taxa cancelamento], "Validas", [Entregas validas], "Atrasados", [Entregas atrasadas], "TaxaAtraso", [Taxa atraso], "Prazo", [Prazo medio (dias)])'
if ($DaxQueryPath) { $modelCommand.CommandText = Get-Content -LiteralPath $DaxQueryPath -Raw }
$modelReader = $modelCommand.ExecuteReader()
$outputRows = @()
while ($modelReader.Read()) {
    $outputRow = [ordered]@{}
    for ($i=0;$i -lt $modelReader.FieldCount;$i++) { $outputRow[$modelReader.GetName($i)] = $modelReader.GetValue($i) }
    $outputRows += [pscustomobject]$outputRow
}
$outputRows | ConvertTo-Json
$modelReader.Close()
$modelConnection.Close()

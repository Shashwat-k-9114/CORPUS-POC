[CmdletBinding()]
param(
    [ValidateSet("create", "seed", "reset")]
    [string]$Action = "create",
    [switch]$ConfirmReset,
    [string]$ApiUrl = "http://127.0.0.1:8000"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot

function New-DemoPdf([string]$Path, [string]$Text) {
    $stream = "BT /F1 24 Tf 20 100 Td ($Text) Tj ET"
    $objects = @(
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        "<< /Length $([Text.Encoding]::ASCII.GetByteCount($stream)) >>`nstream`n$stream`nendstream"
    )
    $body = "%PDF-1.4`n"
    $offsets = [System.Collections.Generic.List[int]]::new()
    $offsets.Add(0)
    for ($index = 0; $index -lt $objects.Count; $index++) {
        $offsets.Add([Text.Encoding]::ASCII.GetByteCount($body))
        $body += "$($index + 1) 0 obj`n$($objects[$index])`nendobj`n"
    }
    $xref = [Text.Encoding]::ASCII.GetByteCount($body)
    $body += "xref`n0 $($objects.Count + 1)`n0000000000 65535 f `n"
    foreach ($offset in $offsets | Select-Object -Skip 1) {
        $body += "{0:D10} 00000 n `n" -f $offset
    }
    $body += "trailer`n<< /Size $($objects.Count + 1) /Root 1 0 R >>`nstartxref`n$xref`n%%EOF"
    [IO.File]::WriteAllBytes($Path, [Text.Encoding]::ASCII.GetBytes($body))
}

function New-DemoContext {
    $allCustodians = (Invoke-WebRequest -Uri "$ApiUrl/v1/custodians" -UseBasicParsing).Content | ConvertFrom-Json
    $existing = @($allCustodians | Where-Object slug -eq "demo")
    if ($existing) {
        $corpora = (Invoke-WebRequest -Uri "$ApiUrl/v1/custodians/$($existing[0].id)/corpora" -UseBasicParsing).Content | ConvertFrom-Json
        $corpus = @($corpora)[0]
        return [pscustomobject]@{ CustodianId = $existing[0].id; CorpusId = $corpus.id }
    }
    $body = @{ slug = "demo"; name = "CORPUS demo custodian" } | ConvertTo-Json
    $created = Invoke-RestMethod -Uri "$ApiUrl/v1/custodians" -Method Post -ContentType "application/json" -Body $body
    return [pscustomobject]@{ CustodianId = $created.custodian.id; CorpusId = $created.default_corpus.id }
}

function Add-DemoPdf([string]$Path, [string]$Name, [string]$Channel) {
    if (-not (Test-Path -LiteralPath $Path)) { throw "Demo fixture not found: $Path" }
    $context = New-DemoContext
    $result = curl.exe --silent --show-error -X POST `
        -F "file=@$Path;filename=$Name;type=application/pdf" `
        -F "custodian_id=$($context.CustodianId)" `
        -F "corpus_id=$($context.CorpusId)" `
        -F "arrival_channel=$Channel" `
        "$ApiUrl/v1/admissions"
    $result | ConvertFrom-Json | ConvertTo-Json -Depth 8
}

switch ($Action) {
    "create" { New-DemoContext | ConvertTo-Json }
    "seed" {
        $context = New-DemoContext
        $smallPdf = Join-Path ([IO.Path]::GetTempPath()) "corpus-demo-small.pdf"
        $largePdf = Join-Path ([IO.Path]::GetTempPath()) "corpus-demo-second.pdf"
        New-DemoPdf $smallPdf "CORPUS safe review fixture"
        New-DemoPdf $largePdf "CORPUS second safe fixture"
        try {
            Add-DemoPdf $smallPdf "small-success.pdf" "demo-small" | Out-Host
            Add-DemoPdf $smallPdf "exact-duplicate.pdf" "demo-duplicate" | Out-Host
            Add-DemoPdf $largePdf "second-fixture.pdf" "demo-second" | Out-Host
        }
        finally {
            Remove-Item -LiteralPath $smallPdf, $largePdf -Force -ErrorAction SilentlyContinue
        }
        $bad = Join-Path ([IO.Path]::GetTempPath()) "corpus-demo-corrupt.pdf"
        Set-Content -LiteralPath $bad -Value "%PDF-1.4`nnot a complete PDF`n%%EOF" -NoNewline
        try { Add-DemoPdf $bad "failed-unprocessable.pdf" "demo-failure" | Out-Host }
        finally { Remove-Item -LiteralPath $bad -Force -ErrorAction SilentlyContinue }
        Write-Output "Demo records seeded for custodian $($context.CustodianId), corpus $($context.CorpusId)."
    }
    "reset" {
        if (-not $ConfirmReset) { throw "Reset is scoped to slug=demo but still destructive. Re-run with -ConfirmReset." }
        $demoId = (& docker compose exec -T postgres psql -U corpus -d corpus -Atc "SELECT id FROM custodians WHERE slug = 'demo'").Trim()
        $sql = Get-Content -Raw (Join-Path $PSScriptRoot "demo-reset.sql")
        & docker compose exec -T postgres psql -U corpus -d corpus -v ON_ERROR_STOP=1 -c $sql
        if ($LASTEXITCODE -ne 0) { throw "Demo reset SQL failed with exit code $LASTEXITCODE." }
        if ($demoId) {
            & docker compose exec -T worker sh -c "rm -rf -- /data/blobs/canonical/$demoId /data/blobs/derived/$demoId"
            if ($LASTEXITCODE -ne 0) { throw "Demo blob cleanup failed with exit code $LASTEXITCODE." }
        }
        Write-Output "Demo source records and only the demo custodian blob prefixes were cleared; the empty demo custodian/corpus remains the default review context."
    }
}

# Mo bao cao bang Word (chi doc), cap nhat cac truong TOC trong bo nho, in so trang tung chuong.
# Tuy chon -Pdf: xuat ban PDF canh file .docx (khong ghi de .docx).
param(
    [string]$Docx = (Join-Path $PSScriptRoot "..\BaoCao_DoAn_BigData.docx"),
    [switch]$Pdf
)
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$path = (Resolve-Path $Docx).Path
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
    $doc = $word.Documents.Open($path, $false, $true)
    foreach ($t in $doc.TablesOfContents) { $t.Update() }
    $doc.Repaginate()
    $pages = $doc.ComputeStatistics(2)
    $words = $doc.ComputeStatistics(0)
    "TOTAL_PAGES=$pages"
    "WORDS=$words"
    foreach ($p in $doc.Paragraphs) {
        if ($p.OutlineLevel -eq 1) {
            $txt = $p.Range.Text.Trim()
            $abs = $p.Range.Information(3)
            $disp = $p.Range.Information(1)
            "H1|abs=$abs|shown=$disp|$txt"
        }
    }
    if ($Pdf) {
        $out = [System.IO.Path]::ChangeExtension($path, ".pdf")
        $doc.ExportAsFixedFormat($out, 17)
        "PDF=$out"
    }
    $doc.Close(0)
}
finally {
    $word.Quit()
    [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($word)
}

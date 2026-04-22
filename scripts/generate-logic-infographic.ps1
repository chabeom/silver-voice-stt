Add-Type -AssemblyName System.Drawing

function New-RoundedRectPath {
    param(
        [float]$X,
        [float]$Y,
        [float]$Width,
        [float]$Height,
        [float]$Radius
    )

    $d = $Radius * 2
    $path = New-Object System.Drawing.Drawing2D.GraphicsPath
    $path.AddArc($X, $Y, $d, $d, 180, 90)
    $path.AddArc($X + $Width - $d, $Y, $d, $d, 270, 90)
    $path.AddArc($X + $Width - $d, $Y + $Height - $d, $d, $d, 0, 90)
    $path.AddArc($X, $Y + $Height - $d, $d, $d, 90, 90)
    $path.CloseFigure()
    return $path
}

function Draw-Card {
    param(
        [System.Drawing.Graphics]$Graphics,
        [float]$X,
        [float]$Y,
        [float]$Width,
        [float]$Height,
        [float]$Radius,
        [System.Drawing.Brush]$FillBrush,
        [string]$Title,
        [string[]]$Lines,
        [System.Drawing.Font]$TitleFont,
        [System.Drawing.Font]$BodyFont,
        [System.Drawing.Pen]$BorderPen,
        [System.Drawing.Brush]$TitleBrush,
        [System.Drawing.Brush]$BodyBrush
    )

    $shadow = New-RoundedRectPath ($X + 8) ($Y + 10) $Width $Height $Radius
    $shadowBrush = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(26, 83, 112, 148))
    $Graphics.FillPath($shadowBrush, $shadow)

    $path = New-RoundedRectPath $X $Y $Width $Height $Radius
    $Graphics.FillPath($FillBrush, $path)
    $Graphics.DrawPath($BorderPen, $path)

    $Graphics.DrawString($Title, $TitleFont, $TitleBrush, $X + 18, $Y + 18)
    $cursorY = $Y + 60
    foreach ($line in $Lines) {
        $Graphics.DrawString("• $line", $BodyFont, $BodyBrush, $X + 20, $cursorY)
        $cursorY += 28
    }

    $shadowBrush.Dispose()
    $shadow.Dispose()
    $path.Dispose()
}

function Draw-Arrow {
    param(
        [System.Drawing.Graphics]$Graphics,
        [float]$X1,
        [float]$Y1,
        [float]$X2,
        [float]$Y2,
        [System.Drawing.Color]$Color,
        [float]$Width = 6,
        [string]$Label = "",
        [System.Drawing.Font]$LabelFont = $null,
        [System.Drawing.Brush]$LabelBrush = $null,
        [float]$LabelX = 0,
        [float]$LabelY = 0
    )

    $pen = New-Object System.Drawing.Pen($Color, $Width)
    $pen.StartCap = [System.Drawing.Drawing2D.LineCap]::Round
    $pen.EndCap = [System.Drawing.Drawing2D.LineCap]::Round
    $Graphics.DrawLine($pen, $X1, $Y1, $X2, $Y2)

    $size = 15
    $dx = $X2 - $X1
    $dy = $Y2 - $Y1
    $len = [Math]::Sqrt(($dx * $dx) + ($dy * $dy))
    if ($len -gt 0) {
        $ux = $dx / $len
        $uy = $dy / $len
        $px = -$uy
        $py = $ux

        $tip = New-Object System.Drawing.PointF($X2, $Y2)
        $left = New-Object System.Drawing.PointF(($X2 - ($ux * $size) + ($px * ($size * 0.6))), ($Y2 - ($uy * $size) + ($py * ($size * 0.6))))
        $right = New-Object System.Drawing.PointF(($X2 - ($ux * $size) - ($px * ($size * 0.6))), ($Y2 - ($uy * $size) - ($py * ($size * 0.6))))
        $brush = New-Object System.Drawing.SolidBrush($Color)
        $Graphics.FillPolygon($brush, @($tip, $left, $right))
        $brush.Dispose()
    }

    if ($Label -and $LabelFont -and $LabelBrush) {
        $Graphics.DrawString($Label, $LabelFont, $LabelBrush, $LabelX, $LabelY)
    }

    $pen.Dispose()
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$outputPath = Join-Path $repoRoot 'docs\project-logic-flow-ko.png'

$width = 1800
$height = 1100
$bitmap = New-Object System.Drawing.Bitmap($width, $height)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$graphics.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit

$bgRect = New-Object System.Drawing.Rectangle 0, 0, $width, $height
$bgBrush = New-Object System.Drawing.Drawing2D.LinearGradientBrush(
    $bgRect,
    [System.Drawing.Color]::FromArgb(248, 251, 255),
    [System.Drawing.Color]::FromArgb(255, 247, 238),
    45
)
$graphics.FillRectangle($bgBrush, $bgRect)

$blobBrushA = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(78, 176, 216, 255))
$blobBrushB = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(82, 180, 248, 219))
$blobBrushC = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(72, 223, 210, 255))
$graphics.FillEllipse($blobBrushA, 20, 20, 240, 240)
$graphics.FillEllipse($blobBrushB, 1450, 40, 220, 220)
$graphics.FillEllipse($blobBrushC, 1300, 830, 300, 200)

$titleFont = New-Object System.Drawing.Font('Malgun Gothic', 36, [System.Drawing.FontStyle]::Bold)
$subtitleFont = New-Object System.Drawing.Font('Malgun Gothic', 16, [System.Drawing.FontStyle]::Regular)
$cardTitleFont = New-Object System.Drawing.Font('Malgun Gothic', 18, [System.Drawing.FontStyle]::Bold)
$cardBodyFont = New-Object System.Drawing.Font('Malgun Gothic', 13, [System.Drawing.FontStyle]::Regular)
$smallFont = New-Object System.Drawing.Font('Malgun Gothic', 12, [System.Drawing.FontStyle]::Regular)
$noteFont = New-Object System.Drawing.Font('Malgun Gothic', 14, [System.Drawing.FontStyle]::Bold)

$titleBrush = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(24, 32, 48))
$subtitleBrush = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(92, 105, 126))
$bodyBrush = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(54, 65, 82))
$lineBrush = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(110, 145, 192))
$borderPen = New-Object System.Drawing.Pen([System.Drawing.Color]::FromArgb(225, 233, 244), 2)
$lineColor = [System.Drawing.Color]::FromArgb(110, 145, 192)

$graphics.DrawString('Silver Voice STT 로직 흐름', $titleFont, $titleBrush, 80, 54)
$graphics.DrawString('업로드부터 추론, 교정, 재학습까지 이어지는 전체 파이프라인', $subtitleFont, $subtitleBrush, 84, 112)

$unitRect = New-Object System.Drawing.Rectangle 0, 0, 1, 1
$blueBrush = New-Object System.Drawing.Drawing2D.LinearGradientBrush($unitRect, [System.Drawing.Color]::FromArgb(194, 226, 255), [System.Drawing.Color]::FromArgb(233, 245, 255), 45)
$mintBrush = New-Object System.Drawing.Drawing2D.LinearGradientBrush($unitRect, [System.Drawing.Color]::FromArgb(187, 248, 224), [System.Drawing.Color]::FromArgb(236, 255, 246), 45)
$lavBrush = New-Object System.Drawing.Drawing2D.LinearGradientBrush($unitRect, [System.Drawing.Color]::FromArgb(214, 206, 255), [System.Drawing.Color]::FromArgb(244, 239, 255), 45)
$goldBrush = New-Object System.Drawing.Drawing2D.LinearGradientBrush($unitRect, [System.Drawing.Color]::FromArgb(255, 235, 165), [System.Drawing.Color]::FromArgb(255, 247, 219), 45)
$darkBrush = New-Object System.Drawing.Drawing2D.LinearGradientBrush($unitRect, [System.Drawing.Color]::FromArgb(43, 52, 69), [System.Drawing.Color]::FromArgb(25, 32, 43), 90)

Draw-Card $graphics 80 190 290 170 26 $blueBrush '1. 사용자 웹' @('파일 업로드', '브라우저 녹음', '로그인 / 회원가입') $cardTitleFont $cardBodyFont $borderPen $titleBrush $bodyBrush
Draw-Card $graphics 440 190 290 170 26 $mintBrush '2. FastAPI API' @('JWT 인증', '업로드 검증', '작업 생성') $cardTitleFont $cardBodyFont $borderPen $titleBrush $bodyBrush
Draw-Card $graphics 440 430 250 150 24 $goldBrush 'MinIO' @('원본 음성 저장', '전처리 파일 보관') $cardTitleFont $cardBodyFont $borderPen $titleBrush $bodyBrush
Draw-Card $graphics 720 430 270 150 24 $lavBrush 'Redis + Celery' @('비동기 작업 큐', '재시도 / 백그라운드 처리') $cardTitleFont $cardBodyFont $borderPen $titleBrush $bodyBrush
Draw-Card $graphics 1030 170 360 420 30 $darkBrush '3. STT Worker' @('16kHz mono 변환', 'VAD 적용', '노이즈 감소(선택)', 'Whisper / faster-whisper 추론', 'timestamp / confidence 계산', '한국어 후처리') $cardTitleFont $cardBodyFont $borderPen ([System.Drawing.Brushes]::White) ([System.Drawing.Brushes]::WhiteSmoke)
Draw-Card $graphics 1430 250 290 190 26 $blueBrush '4. PostgreSQL 저장' @('audio_jobs', 'transcripts', 'transcript_segments', 'corrections / model_versions') $cardTitleFont $cardBodyFont $borderPen $titleBrush $bodyBrush
Draw-Card $graphics 1430 520 290 210 26 $mintBrush '5. 관리자 대시보드' @('업로드 이력', '예측문 vs 수정문 비교', '통계 / 모델 비교', 'correction export') $cardTitleFont $cardBodyFont $borderPen $titleBrush $bodyBrush
Draw-Card $graphics 310 770 1240 220 34 $lavBrush '6. 학습 파이프라인' @('AI-Hub 데이터셋 + correction export 수집', '전처리 / split / manifest 생성', 'Whisper fine-tuning', 'WER / CER 평가', '새 모델 버전 등록') $cardTitleFont $cardBodyFont $borderPen $titleBrush $bodyBrush

$notePath = New-RoundedRectPath 84 1018 760 54 18
$noteShadowPath = New-RoundedRectPath 90 1024 760 54 18
$noteShadowBrush = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(22, 83, 112, 148))
$noteFill = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(250, 255, 255, 255))
$graphics.FillPath($noteShadowBrush, $noteShadowPath)
$graphics.FillPath($noteFill, $notePath)
$graphics.DrawPath($borderPen, $notePath)
$graphics.DrawString('현재 상태: 서비스형 MVP 구현 완료, AI-Hub 학습 실행은 다음 단계', $noteFont, $titleBrush, 106, 1033)

Draw-Arrow $graphics 370 275 440 275 $lineColor 6
Draw-Arrow $graphics 585 360 585 430 $lineColor 6
Draw-Arrow $graphics 815 360 880 360 $lineColor 6
Draw-Arrow $graphics 860 505 1030 505 $lineColor 6 '비동기 작업 전달' $smallFont $lineBrush 844 470
Draw-Arrow $graphics 1390 345 1430 345 $lineColor 6
Draw-Arrow $graphics 1575 440 1575 520 $lineColor 6 '관리자 분석 / export' $smallFont $lineBrush 1454 456
Draw-Arrow $graphics 1430 645 940 865 $lineColor 6 'correction export' $smallFont $lineBrush 1170 708
Draw-Arrow $graphics 310 880 180 880 $lineColor 6 '학습 완료 모델 반영' $smallFont $lineBrush 112 842
Draw-Arrow $graphics 180 880 180 360 $lineColor 6
Draw-Arrow $graphics 180 360 80 360 $lineColor 6 'SSE 실시간 상태 반영 / 결과 조회 / 수정 저장' $smallFont $lineBrush 88 388

$graphics.DrawString('AI-Hub 데이터셋', $cardTitleFont, $titleBrush, 356, 826)
$graphics.DrawString('교정 데이터 export', $cardTitleFont, $titleBrush, 1280, 826)

$bitmap.Save($outputPath, [System.Drawing.Imaging.ImageFormat]::Png)

foreach ($font in @($titleFont, $subtitleFont, $cardTitleFont, $cardBodyFont, $smallFont, $noteFont)) {
    $font.Dispose()
}
foreach ($brush in @($bgBrush, $blobBrushA, $blobBrushB, $blobBrushC, $titleBrush, $subtitleBrush, $bodyBrush, $lineBrush, $blueBrush, $mintBrush, $lavBrush, $goldBrush, $darkBrush, $noteShadowBrush, $noteFill)) {
    $brush.Dispose()
}
$notePath.Dispose()
$noteShadowPath.Dispose()
$borderPen.Dispose()
$graphics.Dispose()
$bitmap.Dispose()

Write-Output $outputPath


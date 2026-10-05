Add-Type -AssemblyName System.Drawing
function CropZoom {
  param([string]$src,[string]$dst,[int]$x,[int]$y,[int]$w,[int]$h,[int]$scale)
  $img=[System.Drawing.Image]::FromFile((Resolve-Path $src).Path)
  $rect=New-Object System.Drawing.Rectangle($x,$y,$w,$h)
  $bmp=New-Object System.Drawing.Bitmap([int]($w*$scale),[int]($h*$scale))
  $g=[System.Drawing.Graphics]::FromImage($bmp)
  $g.InterpolationMode=[System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
  $dstRect=New-Object System.Drawing.Rectangle(0,0,[int]($w*$scale),[int]($h*$scale))
  $g.DrawImage($img,$dstRect,$rect,[System.Drawing.GraphicsUnit]::Pixel)
  $g.Dispose()
  $bmp.Save($dst,[System.Drawing.Imaging.ImageFormat]::Png)
  $bmp.Dispose(); $img.Dispose()
  Write-Host "SAVED $dst"
}
CropZoom -src 'results\audit\v2_kol.png' -dst 'results\audit\crop_kol_head.png'  -x 0 -y 280 -w 1542 -h 400 -scale 2
CropZoom -src 'results\audit\v2_lb.png'   -dst 'results\audit\crop_lb_podium.png' -x 0 -y 200 -w 1542 -h 330 -scale 2
CropZoom -src 'results\audit\v2_lb.png'   -dst 'results\audit\crop_lb_rows.png'   -x 0 -y 540 -w 1542 -h 700 -scale 2

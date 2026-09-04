# 智法通 - 问答流式接口端到端调试脚本
$ErrorActionPreference = "Stop"

# 1. 登录获取token
$login = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/auth/login" `
    -Method POST -ContentType "application/json" `
    -Body '{"username":"admin","password":"admin123"}'
$token = $login.access_token
Write-Output "登录成功，token长度: $($token.Length)"

# 2. 调用流式问答接口并记录每个事件的耗时
$client = New-Object System.Net.Http.HttpClient
$client.Timeout = [TimeSpan]::FromMinutes(15)
$req = New-Object System.Net.Http.HttpRequestMessage("POST", "http://localhost:8000/api/v1/qa/ask/stream")
$req.Content = New-Object System.Net.Http.StringContent(
    '{"question":"劳动合同解除后经济补偿金如何计算？","stream":true}',
    [Text.Encoding]::UTF8, "application/json")
$req.Headers.Authorization = New-Object System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", $token)

$sw = [Diagnostics.Stopwatch]::StartNew()
$resp = $client.SendAsync($req, [Net.Http.HttpCompletionOption]::ResponseHeadersRead).Result
Write-Output "[响应头返回] $($sw.Elapsed.TotalSeconds.ToString('F1'))s status=$($resp.StatusCode)"

$stream = $resp.Content.ReadAsStreamAsync().Result
$reader = New-Object IO.StreamReader($stream)
$contentChunkCount = 0
while ($null -ne ($line = $reader.ReadLine())) {
    if ($line -like "data:*") {
        $short = $line.Substring(0, [Math]::Min(300, $line.Length))
        if ($line -like '*"type": "content"*' -or $line -like '*"type":"content"*') {
            $contentChunkCount++
            # 只打印前3个content块，避免刷屏
            if ($contentChunkCount -le 3) {
                Write-Output "[$($sw.Elapsed.TotalSeconds.ToString('F1'))s] $short"
            }
        } else {
            Write-Output "[$($sw.Elapsed.TotalSeconds.ToString('F1'))s] $short"
        }
    }
}
Write-Output "[流结束] $($sw.Elapsed.TotalSeconds.ToString('F1'))s 共收到content块: $contentChunkCount"

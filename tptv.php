<?php
/**
 * 直播源获取 - 完整实现
 *
 * 流程: /mix/kepler -> /mix/lamb -> playauth -> CDN重定向 -> mobaibox
 *
 * 用法: pzinfo.php?id=HD-100M-4320P-cctv8k&license=cntv
 */

error_reporting(0);
define('IS_CLI', PHP_SAPI === 'cli');

// ============================================================
// 参数
// ============================================================
$id = isset($_GET['id']) ? $_GET['id'] : 'HD-100M-4320P-cctv8k';
$license = isset($_GET['license']) ? $_GET['license'] : 'cntv';

// ============================================================
// 常量
// ============================================================
define('UCS_HOTLINK_KEY', 'jbAYqxwebBOMaYKW');
define('YAUTH_SECRET', 'ygtrkdwirmehifdhgtmx');
define('PLATFORM_ID', 'Ystenplatform_JS_taipanAPK_20161209001');
define('DEVICE_TYPE', 'STB');
define('BASELINE_VERSION', '20260110');
define('PROTOCOL', 'V2.0');
define('CHARSET_61', 'TwafeUkYGrwZ71d0SvXEmP693nbxWKy4RqtCuHcQpA2VjlLDJhF8oBMg5NI');

// 设备身份
define('DEV_UID', '响应体拿');
define('DEV_TEL', '自己找');
define('DEV_ACCOUNT', DEV_TEL);
define('DEV_USER_ID', DEV_TEL);
define('DEV_MAC', '自己找');
define('DEV_TXKEY', '不重要');
define('DEV_DEVICE_ID', '响应体拿');
define('DEV_STB_ID', DEV_DEVICE_ID);
define('DEV_OTT_TOKEN', DEV_TXKEY);
define('DEV_APP_VER', 'V9.2.0.6.YP_JS.26.01.23');
define('DEV_APP_VC', '9206');

// UA
define('UA_MIX', 'okhttp/3.12.0');
define('UA_AUTH', 'okhttp/3.8.1');
define('UA_M3U8', 'okhttp/3.8.1');
define('CACHE_TTL', 600);
define('CACHE_DIR', sys_get_temp_dir() . DIRECTORY_SEPARATOR . 'pzinfo_cache');

// ============================================================
// 工具函数
// ============================================================

function disable_curl_ssl_verification($ch) {
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    curl_setopt($ch, CURLOPT_SSL_VERIFYHOST, 0);
}

function debug_log($message) {
    if (getenv('DEBUG')) {
        if (IS_CLI && defined('STDERR')) {
            fwrite(STDERR, $message . "\n");
        } else {
            error_log($message);
        }
    }
}

function progress($message) {
    if (IS_CLI) {
        echo $message;
    }
}

function cache_path($key) {
    return CACHE_DIR . DIRECTORY_SEPARATOR . sha1($key) . '.json';
}

function cache_get($key) {
    $path = cache_path($key);
    if (!is_file($path)) {
        return null;
    }

    $raw = file_get_contents($path);
    $item = json_decode($raw, true);
    if (!$item || !isset($item['expires']) || time() >= $item['expires']) {
        @unlink($path);
        return null;
    }

    return $item['value'] ?? null;
}

function cache_set($key, $value, $ttl = CACHE_TTL) {
    if (!is_dir(CACHE_DIR) && !@mkdir(CACHE_DIR, 0777, true) && !is_dir(CACHE_DIR)) {
        return false;
    }

    $path = cache_path($key);
    $tmp = $path . '.' . getmypid() . '.tmp';
    $item = [
        'expires' => time() + $ttl,
        'value' => $value,
    ];

    $ok = file_put_contents($tmp, json_encode($item, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE), LOCK_EX);
    if ($ok === false) {
        @unlink($tmp);
        return false;
    }

    return @rename($tmp, $path);
}

function get_first_valid_ip($value) {
    foreach (explode(',', (string) $value) as $ip) {
        $ip = trim($ip);
        if (filter_var($ip, FILTER_VALIDATE_IP)) {
            return $ip;
        }
    }
    return '';
}

function get_public_ip() {
    $endpoints = [
        ['https://myip.ipip.net/json', 'data.ip'],
        ['http://myip.ipip.net/json', 'data.ip'],
    ];

    foreach ($endpoints as $endpoint) {
        list($body) = http_request($endpoint[0]);
        if ($body === false || $body === '') {
            continue;
        }

        if ($endpoint[1] === 'plain') {
            $ip = get_first_valid_ip($body);
        } else {
            $json = json_decode($body, true);
            $ip = '';
            foreach (explode('.', $endpoint[1]) as $key) {
                if (!is_array($json) || !isset($json[$key])) {
                    $ip = '';
                    break;
                }
                $ip = $json[$key];
                $json = $json[$key];
            }
            $ip = get_first_valid_ip($ip);
        }

        if ($ip !== '') {
            return $ip;
        }
    }

    return '';
}

function get_client_ip() {
    if (IS_CLI) {
        return get_public_ip();
    }

    foreach (['HTTP_CF_CONNECTING_IP', 'HTTP_X_REAL_IP', 'HTTP_X_FORWARDED_FOR', 'REMOTE_ADDR'] as $key) {
        $ip = get_first_valid_ip($_SERVER[$key] ?? '');
        if ($ip !== '') {
            return $ip;
        }
    }

    return get_public_ip();
}

function get_cached_client_ip() {
    $cachedIp = cache_get('client_ip');
    if ($cachedIp !== null && get_first_valid_ip($cachedIp) !== '') {
        progress("[缓存] IP 命中 ... ");
        return $cachedIp;
    }

    $clientIp = get_client_ip();
    if ($clientIp !== '') {
        cache_set('client_ip', $clientIp);
    }
    return $clientIp;
}

function redirect_to_live_source($url) {
    $url = str_replace(["\r", "\n"], '', $url);

    if (IS_CLI) {
        echo str_repeat('=', 80) . "\n";
        echo "302 Location: " . $url . "\n";
        echo str_repeat('=', 80) . "\n";
        exit;
    }

    header('Cache-Control: no-store');
    header('Location: ' . $url, true, 302);
    exit;
}

function http_request($url, $headers = [], $data = '', $method = 'GET', $noBody = false) {
    if ($data !== '' && strtoupper($method) === 'GET') {
        $method = 'POST';
    }

    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $url);
    disable_curl_ssl_verification($ch);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 10);
    curl_setopt($ch, CURLOPT_CUSTOMREQUEST, $method);

    if (!empty($headers)) {
        curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
    }
    if ($data !== '') {
        curl_setopt($ch, CURLOPT_POSTFIELDS, $data);
    }
    if ($noBody) {
        curl_setopt($ch, CURLOPT_NOBODY, true);
        curl_setopt($ch, CURLOPT_HEADER, true);
    }

    $body = curl_exec($ch);
    $info = curl_getinfo($ch);
    curl_close($ch);
    return [$body, $info];
}

function append_query_param_if_missing($url, $key, $value) {
    if (preg_match('/(?:^|[?&])' . preg_quote($key, '/') . '=/', $url)) {
        return $url;
    }

    $separator = (strpos($url, '?') === false) ? '?' : '&';
    return $url . $separator . $key . '=' . $value;
}

function fba_random($length) {
    $chars = CHARSET_61;
    $result = '';
    for ($i = 0; $i < $length; $i++) {
        $result .= $chars[random_int(0, strlen($chars) - 1)];
    }
    return $result;
}

function fba_blend_key($baseKey, $randomStr, $cut = 10) {
    if (empty($baseKey)) {
        $baseKey = 'jwDhF2NrTWVapORV';
    }
    if (empty($randomStr)) {
        return $baseKey;
    }
    $prefix = (strlen($baseKey) >= $cut)
        ? substr($baseKey, 0, strlen($baseKey) - $cut) : '';
    $suffix = substr($randomStr, 0, $cut);
    return $prefix . $suffix;
}

function fba_derive_aes_key($blendedKey) {
    $key = array_fill(0, 16, 0);
    $bytes = unpack('C*', $blendedKey);
    $idx = 0;
    foreach ($bytes as $b) {
        $key[$idx % 16] ^= $b;
        $idx++;
    }
    return pack('C*', ...$key);
}

function fba_encrypt($blendedKey, $plaintext) {
    $aesKey = fba_derive_aes_key($blendedKey);
    $padLen = 16 - (strlen($plaintext) % 16);
    $data = $plaintext . str_repeat(chr($padLen), $padLen);
    $encrypted = openssl_encrypt($data, 'aes-128-ecb', $aesKey, OPENSSL_RAW_DATA);
    return strtoupper(bin2hex($encrypted));
}

function fba_decrypt($blendedKey, $hexData) {
    $aesKey = fba_derive_aes_key($blendedKey);
    $data = hex2bin($hexData);
    $decrypted = openssl_decrypt($data, 'aes-128-ecb', $aesKey, OPENSSL_RAW_DATA);
    if ($decrypted === false || $decrypted === '') {
        return '';
    }

    $padLen = ord(substr($decrypted, -1));
    if ($padLen < 1 || $padLen > 16) {
        return $decrypted;
    }

    $padding = substr($decrypted, -$padLen);
    if ($padding !== str_repeat(chr($padLen), $padLen)) {
        return $decrypted;
    }

    return substr($decrypted, 0, -$padLen);
}

function make_yauth($deviceId, $mac, $appVer, $appVc) {
    $ts = intval(microtime(true) * 1000);
    $hexTs = dechex(intval($ts / 1000));
    $raw = implode('#', [
        $deviceId, $mac, $appVer, $appVc, DEVICE_TYPE, PROTOCOL
    ]);
    $md5 = md5(YAUTH_SECRET . $hexTs . $raw);
    return implode('#', [$md5, $hexTs, $raw]);
}

function make_ucs_headers($deviceId, $mac, $dynamicId) {
    return [
        'User-Agent: ' . UA_MIX,
        'Content-Type: application/json',
        'Host: bsu.taipan.jsa.bcs.ottcn.com:8120',
        'originUid: ' . DEV_UID,
        'deviceType: ' . DEVICE_TYPE,
        'baselineVersion: ' . BASELINE_VERSION,
        'serviceChannelId: ',
        'platformId: ' . PLATFORM_ID,
        'appVersionName: ' . DEV_APP_VER,
        'deviceId: ' . $deviceId,
        'appVersionCode: ' . DEV_APP_VC,
        'mac: ' . $mac,
        'dynamicId: ' . $dynamicId,
        'YAUTH: ' . make_yauth($deviceId, $mac, DEV_APP_VER, DEV_APP_VC),
    ];
}

function random_mac() {
    $parts = [];
    for ($i = 0; $i < 6; $i++) {
        $parts[] = strtoupper(str_pad(dechex(random_int(0, 255)), 2, '0', STR_PAD_LEFT));
    }
    return implode(':', $parts);
}

function random_phone() {
    return '151' . str_pad(random_int(0, 99999999), 8, '0', STR_PAD_LEFT);
}

// ============================================================
// Step 1: /mix/kepler -> ucsExtensionKey
// ============================================================
function get_ucs_extension_key() {
    $payload = json_encode([
        'uid' => DEV_UID,
        'account' => DEV_ACCOUNT,
        'mac' => DEV_MAC,
        'txKey' => DEV_TXKEY,
    ]);

    $strA = fba_random(10);
    $blended = fba_blend_key(UCS_HOTLINK_KEY, $strA, 10);
    $body = fba_encrypt($blended, $payload);
    $headers = make_ucs_headers(DEV_DEVICE_ID, DEV_MAC, $strA);

    list($resp, $info) = http_request(
        'http://bsu.taipan.jsa.bcs.ottcn.com:8120/nucs-gateway/ucs-extension-api/mix/kepler',
        $headers,
        $body
    );

    $httpCode = $info['http_code'];
    $json = json_decode($resp, true);
    if (!$json || empty($json['data']) || !$json['success']) {
        die("[错误] /mix/kepler 失败\n  HTTP: $httpCode\n  Response: $resp\n");
    }

    $decrypted = fba_decrypt($blended, $json['data']);
    $inner = json_decode($decrypted, true);
    $token = $inner['data'] ?? '';

    if (empty($token)) {
        debug_log("[DEBUG] /mix/kepler outer: " . $resp);
        debug_log("[DEBUG] /mix/kepler decrypted: " . $decrypted);
        debug_log("[DEBUG] /mix/kepler inner: " . var_export($inner, true));
        die("[错误] ucsExtensionKey 为空\n");
    }

    return $token;
}

// ============================================================
// Step 2: /mix/lamb -> pzinfo
// ============================================================
function get_pzinfo($contentId, $license, $ucsExtKey) {
    $payload = json_encode([
        'uid' => DEV_UID,
        'account' => DEV_ACCOUNT,
        'mac' => DEV_MAC,
        'token' => $ucsExtKey,
        'timestamp' => time(),
        'license' => $license,
        'txKey' => DEV_TXKEY,
        'deviceType' => DEVICE_TYPE,
        'contentId' => $contentId,
    ]);

    $strA = fba_random(10);
    $blended = fba_blend_key(UCS_HOTLINK_KEY, $strA, 10);
    $body = fba_encrypt($blended, $payload);
    $headers = make_ucs_headers(DEV_DEVICE_ID, DEV_MAC, $strA);

    list($resp, $info) = http_request(
        'http://bsu.taipan.jsa.bcs.ottcn.com:8120/nucs-gateway/ucs-extension-api/mix/lamb',
        $headers,
        $body
    );

    $json = json_decode($resp, true);
    if (!$json || empty($json['data']) || !$json['success']) {
        die("[错误] /mix/lamb 失败: $resp\n");
    }

    $decrypted = fba_decrypt($blended, $json['data']);
    $inner = json_decode($decrypted, true);
    $pzinfo = $inner['data'] ?? '';

    if (empty($pzinfo)) {
        die("[错误] pzinfo 为空\n");
    }

    return $pzinfo;
}

// ============================================================
// Step 3: AuthCode
// ============================================================
function get_auth_code($contentId, $clientIp) {
    $data = json_encode([
        'ContentID' => $contentId,
        'MAC' => DEV_MAC,
        'OTTUserToken' => DEV_OTT_TOKEN,
        'UserID' => DEV_USER_ID,
        'SPAuthResult' => '0',
    ]);

    list($body, $info) = http_request(
        'http://223.105.251.59:33200/EPG/Ott/jsp/Auth.jsp',
        [
            'User-Agent: ' . UA_AUTH,
            'Content-Type: application/json',
            'X-Forwarded-For: ' . $clientIp,
        ],
        $data
    );

    $json = json_decode($body, true);
    if (!$json || empty($json['AuthCode'])) {
        die("[错误] AuthCode 获取失败: $body\n");
    }

    $authCode = $json['AuthCode'];
    debug_log("[DEBUG] AuthCode decoded: " . urldecode($authCode));

    return [$authCode];
}

// ============================================================
// Step 4: CDN 重定向 (HEAD 请求, 不跟随)
// ============================================================
function get_cdn_redirect($contentId, $authCode) {
    $url = "http://183.207.249.71/gitv/live1/$contentId/$contentId?"
        . 'OTTUserToken=' . DEV_OTT_TOKEN
        . '&UserName=' . DEV_USER_ID
        . '&MAC=' . DEV_MAC
        . '&stbID=' . DEV_STB_ID;
    if ($authCode !== '') {
        $url .= '&' . $authCode;
    }

    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $url);
    disable_curl_ssl_verification($ch);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 8);
    curl_setopt($ch, CURLOPT_NOBODY, true);
    curl_setopt($ch, CURLOPT_FOLLOWLOCATION, false);
    curl_setopt($ch, CURLOPT_HEADER, true);
    curl_setopt($ch, CURLOPT_HTTPHEADER, [
        'User-Agent: ' . UA_AUTH,
        'Host: 183.207.249.71',
    ]);

    $result = curl_exec($ch);
    curl_close($ch);

    if (preg_match('/^Location:\s*(.+)$/im', $result, $m)) {
        return trim($m[1]);
    }
    return '';
}

// ============================================================
// 主流程
// ============================================================

progress("频道: $id   License: $license\n\n");

$liveCacheKey = $id;
$cachedLiveUrl = cache_get($liveCacheKey);
if ($cachedLiveUrl !== null && $cachedLiveUrl !== '') {
    progress("[缓存] 直播源命中\n\n");
    redirect_to_live_source($cachedLiveUrl);
}

progress("[0] 客户端IP ... ");
$clientIp = get_cached_client_ip();
progress("$clientIp\n");

progress("[1] /mix/kepler ... ");
$ucsExtKey = get_ucs_extension_key();
progress("OK\n");

progress("[2] /mix/lamb ... ");
$pzinfo = get_pzinfo($id, $license, $ucsExtKey);
progress("OK\n");

progress("[3] AuthCode ... ");
list($authCode) = get_auth_code($id, $clientIp);
progress("OK\n");

progress("[4] CDN 重定向 ... ");
$redirectUrl = get_cdn_redirect($id, $authCode);
if (empty($redirectUrl)) {
    die("失败\n");
}
progress("OK\n");

progress("[5] 组装 ... ");

$m3u8Url = str_replace('index.m3u8', '1.m3u8', $redirectUrl);

$mobaiboxUrl = preg_replace(
    '/^https?:\/\//',
    'https://tptvho.mobaibox.com/hwcdnbacksourceflag_',
    $m3u8Url
);

// APK 里是直接拼接, 不做 URL 编码
$finalUrl = $mobaiboxUrl;
$finalUrl = append_query_param_if_missing($finalUrl, 'OTTUserToken', DEV_OTT_TOKEN);
$finalUrl = append_query_param_if_missing($finalUrl, 'UserName', DEV_USER_ID);
$finalUrl = append_query_param_if_missing($finalUrl, 'MAC', DEV_MAC);
$finalUrl = append_query_param_if_missing($finalUrl, 'stbID', DEV_STB_ID);
$finalUrl = append_query_param_if_missing($finalUrl, 'pzinfo', $pzinfo);

cache_set($liveCacheKey, $finalUrl);
progress("OK\n\n");
redirect_to_live_source($finalUrl);

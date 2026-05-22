# Bilibili API Reference

Internal reference for how the downloader interacts with Bilibili's API.

## WBI Signature

Bilibili requires a signed `w_rid` parameter on most API calls.

### Algorithm

1. Fetch `img_key` and `sub_key` from `GET /x/web-interface/nav`
   - Extract from `wbi_img.img_url` and `wbi_img.sub_url` filenames
2. Compute mixin key: `mixinKeyEncTab` permutation of `img_key + sub_key`, first 32 chars
3. Add `wts` (current timestamp) to params
4. Sort params alphabetically
5. Strip chars `!'()*` from values
6. `w_rid = md5(urlencode(params) + mixin_key)`

See implementation in `scripts/download_bilibili.py::enc_wbi()`.

## Endpoints

### Video Metadata

```
GET https://api.bilibili.com/x/web-interface/wbi/view?bvid={BV}&wts={ts}&w_rid={sig}
```

Returns: title, cid, pages, owner info, ugc_season (collections).

### Stream URLs

```
GET https://api.bilibili.com/x/player/playurl?bvid={BV}&cid={CID}&qn=80&fnver=0&fnval=4048&fourk=1&wts={ts}&w_rid={sig}
```

Returns DASH manifest with separate video/audio streams, or MP4/FLV fallback.

Key parameters:
- `qn`: quality preference (80 = 1080P, but server decides based on auth)
- `fnval`: 4048 = request DASH format
- `fourk`: 1 = allow 4K if available

### Response Format (DASH)

```json
{
  "dash": {
    "video": [{"id": 32, "baseUrl": "...", "codecid": 7, "bandwidth": ...}],
    "audio": [{"id": 30280, "baseUrl": "...", "bandwidth": ...}]
  }
}
```

Quality IDs:
- 16: 360P
- 32: 480P
- 64: 720P
- 80: 1080P
- 112: 1080P+
- 116: 1080P60
- 120: 4K
- 125: HDR
- 126: Dolby Vision
- 127: 8K

Audio IDs:
- 30216: 64K
- 30232: 128K
- 30250: 320K / Dolby
- 30280: Hi-Res

## Authentication

Without SESSDATA cookie, the API returns max 480P (qn=32). To get higher quality:

1. Log in to bilibili.com in a browser
2. Copy SESSDATA from cookies
3. Add to requests: `Cookie: SESSDATA=xxx`

The current script does not support cookies — this is by design for simplicity. Use Bili23-Downloader GUI for authenticated downloads.

## Headers

Required on all requests:
```
Referer: https://www.bilibili.com/
User-Agent: Mozilla/5.0 ...
```

The Referer is essential — without it, CDN returns 403.

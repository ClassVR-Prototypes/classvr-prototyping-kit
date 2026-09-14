#!/usr/bin/env python3
"""Upload one file to ClassCloud storage (AVNFS) and verify it is served inline.

    python3 upload.py --file dist/app-build3.html --ticket-file /tmp/ticket.txt [--name app-build3.html]

The ticket comes from the Eduverse MCP tool `get_upload_ticket`; write it to a
file and pass the path (it is far too long for a command line). The upload
endpoint accepts ONLY the ticket as credential and ONLY a raw body — not
multipart — so this uses a plain POST with the bytes as the body.

Prints JSON: {ok, url, hash, sizeBytes, contentType, contentDisposition}
The `url` includes the query string. Keep the WHOLE url — the bare hash 403s.
"""
import argparse, json, os, sys, urllib.request, urllib.parse, urllib.error

# Default endpoint. The ticket is only valid at the server that minted it, so
# always pass the `uploadUrl` from the get_upload_ticket response (the
# connector may be pointed at another deployment, e.g. mcp-alpha.eduverse.com).
UPLOAD = 'https://mcp.eduverse.com/upload'

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--file', required=True)
    ap.add_argument('--ticket-file', required=True)
    ap.add_argument('--name', help='filename recorded on the server (default: basename of --file)')
    ap.add_argument('--type', default='text/html')
    ap.add_argument('--upload-url', default=UPLOAD, help='uploadUrl from the get_upload_ticket response')
    a = ap.parse_args()

    ticket = open(a.ticket_file).read().strip()
    data = open(a.file, 'rb').read()
    name = a.name or os.path.basename(a.file)
    q = urllib.parse.urlencode({'name': name, 'type': a.type})
    req = urllib.request.Request(a.upload_url + '?' + q, data=data, method='POST',
                                 headers={'Authorization': 'Bearer ' + ticket,
                                          'Content-Type': 'application/octet-stream'})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            body = json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        print(json.dumps({'ok': False, 'error': f'upload HTTP {e.code}', 'body': e.read().decode('utf-8', 'replace')[:400]}))
        return 1

    url = body.get('url')
    # verify it is reachable and will render as a page rather than download
    ct = cd = None
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method='GET'), timeout=60) as r:
            ct = r.headers.get('content-type'); cd = r.headers.get('content-disposition')
            served = r.read()
        identical = served == data
    except Exception as e:
        identical = False; ct = ct or ('verify failed: ' + str(e)[:120])

    result = {'ok': bool(url) and identical and (cd or '').startswith('inline'),
              'url': url, 'hash': body.get('hash'), 'sizeBytes': body.get('sizeBytes'),
              'deduplicated': body.get('deduplicated'),
              'contentType': ct, 'contentDisposition': cd, 'byteIdentical': identical}
    print(json.dumps(result, indent=2))
    return 0 if result['ok'] else 1

if __name__ == '__main__':
    sys.exit(main())

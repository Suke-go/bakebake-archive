import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import url from 'node:url';

const __dirname = path.dirname(url.fileURLToPath(import.meta.url));

// Config
const PORT = Number(process.env.PORT || getArg('--port') || 8080);
const DATA_DIR = path.resolve(
  __dirname,
  process.env.DATA_DIR || getArg('--dir') || 'data'
);

function getArg(name) {
  const idx = process.argv.indexOf(name);
  if (idx !== -1 && idx + 1 < process.argv.length) return process.argv[idx + 1];
  return undefined;
}

function mimeType(filePath) {
  const ext = path.extname(filePath).toLowerCase();
  switch (ext) {
    case '.json':
    case '.geojson':
      return 'application/json; charset=utf-8';
    case '.b3dm':
    case '.i3dm':
    case '.pnts':
    case '.cmpt':
    case '.glb':
    case '.bin':
    case '.ktx2':
      return 'application/octet-stream';
    case '.gltf':
      return 'model/gltf+json';
    case '.png':
      return 'image/png';
    case '.jpg':
    case '.jpeg':
      return 'image/jpeg';
    case '.webp':
      return 'image/webp';
    case '.gz':
      return 'application/gzip';
    default:
      return 'application/octet-stream';
  }
}

function setCors(res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader(
    'Access-Control-Allow-Headers',
    'Origin, X-Requested-With, Content-Type, Accept, Range'
  );
  res.setHeader('Access-Control-Allow-Methods', 'GET,HEAD,OPTIONS');
  res.setHeader('Access-Control-Expose-Headers', 'Content-Length, Content-Range');
  res.setHeader('Vary', 'Origin');
}

function safeJoin(base, requestPath) {
  const decoded = decodeURIComponent(requestPath);
  const p = path.normalize(decoded).replace(/^\/+/, '');
  const resolved = path.resolve(base, p);
  if (!resolved.startsWith(base)) return null; // prevent traversal
  return resolved;
}

const server = http.createServer((req, res) => {
  setCors(res);

  if (req.method === 'OPTIONS') {
    res.writeHead(204);
    res.end();
    return;
  }

  if (req.method !== 'GET' && req.method !== 'HEAD') {
    res.writeHead(405, { 'Content-Type': 'text/plain' });
    res.end('Method Not Allowed');
    return;
  }

  const parsed = new URL(req.url, `http://${req.headers.host}`);
  const filePath = safeJoin(DATA_DIR, parsed.pathname);
  if (!filePath) {
    res.writeHead(400, { 'Content-Type': 'text/plain' });
    res.end('Bad Request');
    return;
  }

  fs.stat(filePath, (err, stats) => {
    if (err || !stats.isFile()) {
      res.writeHead(404, { 'Content-Type': 'text/plain' });
      res.end('Not Found');
      return;
    }

    const size = stats.size;
    const range = req.headers.range;
    let type = mimeType(filePath);
    const lower = filePath.toLowerCase();

    // Support pre-compressed assets like *.json.gz or *.b3dm.gz
    let contentEncoding;
    if (lower.endsWith('.json.gz')) type = 'application/json; charset=utf-8';
    if (lower.endsWith('.gltf.gz')) type = 'model/gltf+json';
    if (lower.endsWith('.b3dm.gz') || lower.endsWith('.pnts.gz') || lower.endsWith('.i3dm.gz') || lower.endsWith('.cmpt.gz') || lower.endsWith('.glb.gz') || lower.endsWith('.bin.gz') || lower.endsWith('.ktx2.gz')) {
      type = 'application/octet-stream';
    }
    if (lower.endsWith('.gz')) contentEncoding = 'gzip';

    const lastModified = stats.mtime.toUTCString();
    const etag = `W/"${size}-${Number(stats.mtimeMs)}"`;

    // Conditional requests
    if (req.headers['if-none-match'] === etag || req.headers['if-modified-since'] === lastModified) {
      res.writeHead(304, {
        'ETag': etag,
        'Last-Modified': lastModified,
        'Cache-Control': 'public, max-age=604800, immutable, no-transform',
      });
      res.end();
      return;
    }

    if (range) {
      const match = /bytes=(\d*)-(\d*)/.exec(range);
      if (match) {
        let start = match[1] ? parseInt(match[1], 10) : 0;
        let end = match[2] ? parseInt(match[2], 10) : size - 1;
        if (isNaN(start)) start = 0;
        if (isNaN(end) || end >= size) end = size - 1;
        if (start > end) {
          res.writeHead(416, {
            'Content-Range': `bytes */${size}`,
            'Accept-Ranges': 'bytes',
          });
          res.end();
          return;
        }
        const chunkSize = end - start + 1;
        const headers = {
          'Content-Type': type,
          'Content-Length': chunkSize,
          'Content-Range': `bytes ${start}-${end}/${size}`,
          'Accept-Ranges': 'bytes',
          'Cache-Control': 'public, max-age=604800, immutable, no-transform',
          'X-Content-Type-Options': 'nosniff',
          'ETag': etag,
          'Last-Modified': lastModified,
        };
        if (contentEncoding) headers['Content-Encoding'] = contentEncoding;
        res.writeHead(206, headers);
        if (req.method === 'HEAD') return res.end();
        fs.createReadStream(filePath, { start, end }).pipe(res);
        return;
      }
    }

    const headers = {
      'Content-Type': type,
      'Content-Length': size,
      'Accept-Ranges': 'bytes',
      'Cache-Control': 'public, max-age=604800, immutable, no-transform',
      'X-Content-Type-Options': 'nosniff',
      'ETag': etag,
      'Last-Modified': lastModified,
    };
    if (contentEncoding) headers['Content-Encoding'] = contentEncoding;
    res.writeHead(200, headers);
    if (req.method === 'HEAD') return res.end();
    fs.createReadStream(filePath).pipe(res);
  });
});

server.listen(PORT, () => {
  // eslint-disable-next-line no-console
  console.log(`PLATEAU static server on http://localhost:${PORT}`);
  // eslint-disable-next-line no-console
  console.log(`Serving directory: ${DATA_DIR}`);
});

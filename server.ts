import {spawn, type ChildProcess} from 'node:child_process';
import fs from 'node:fs';
import http from 'node:http';
import net from 'node:net';
import path from 'node:path';

const PORT = 3000;
const STREAMLIT_HOST = '127.0.0.1';
const STREAMLIT_PORT = 8501;

function resolvePythonBin(): string {
  const venvPython = path.resolve(process.cwd(), '.venv', 'bin', 'python');
  if (fs.existsSync(venvPython)) {
    return venvPython;
  }
  return 'python3';
}

function startStreamlit(): ChildProcess {
  const pythonBin = resolvePythonBin();
  const child = spawn(
    pythonBin,
    [
      '-m',
      'streamlit',
      'run',
      'streamlit_app.py',
      `--server.port=${STREAMLIT_PORT}`,
      `--server.address=${STREAMLIT_HOST}`,
      '--server.headless=true',
      '--browser.gatherUsageStats=false',
      '--server.enableCORS=false',
      '--server.enableXsrfProtection=false',
    ],
    {
      cwd: process.cwd(),
      stdio: 'inherit',
      env: process.env,
    },
  );

  child.on('error', (err) => {
    console.error('Failed to launch Streamlit:', err);
  });
  return child;
}

function waitForStreamlit(timeoutMs = 15000): Promise<void> {
  const startedAt = Date.now();
  return new Promise((resolve) => {
    const probe = () => {
      const socket = net.connect(STREAMLIT_PORT, STREAMLIT_HOST);
      socket.once('connect', () => {
        socket.destroy();
        resolve();
      });
      socket.once('error', () => {
        socket.destroy();
        if (Date.now() - startedAt >= timeoutMs) {
          resolve();
          return;
        }
        setTimeout(probe, 250);
      });
    };
    probe();
  });
}

async function main(): Promise<void> {
  const streamlitProcess = startStreamlit();

  const cleanup = () => {
    if (!streamlitProcess.killed) {
      streamlitProcess.kill('SIGTERM');
    }
    process.exit(0);
  };
  process.on('SIGINT', cleanup);
  process.on('SIGTERM', cleanup);

  await waitForStreamlit();

  const server = http.createServer((req, res) => {
    const reqPath = (req.url || '/').split('?')[0];
    if (
      (req.method === 'GET' || req.method === 'HEAD') &&
      reqPath === '/googleaee54bf2d5a00ed1.html'
    ) {
      const verificationFile = path.resolve(process.cwd(), 'googleaee54bf2d5a00ed1.html');
      if (fs.existsSync(verificationFile)) {
        const body = fs.readFileSync(verificationFile);
        res.writeHead(200, {
          'Content-Type': 'text/html; charset=utf-8',
          'Content-Length': body.length,
        });
        res.end(req.method === 'HEAD' ? undefined : body);
        return;
      }
    }

    const proxyReq = http.request(
      {
        hostname: STREAMLIT_HOST,
        port: STREAMLIT_PORT,
        path: req.url || '/',
        method: req.method,
        headers: {
          ...req.headers,
          host: `${STREAMLIT_HOST}:${STREAMLIT_PORT}`,
        },
      },
      (proxyRes) => {
        res.writeHead(proxyRes.statusCode || 502, proxyRes.headers);
        proxyRes.pipe(res, {end: true});
      },
    );

    proxyReq.on('error', (err) => {
      if (!res.headersSent) {
        res.writeHead(502, {'Content-Type': 'text/plain; charset=utf-8'});
      }
      res.end(`SCRIPTXT Streamlit upstream unavailable: ${err.message}`);
    });

    req.pipe(proxyReq, {end: true});
  });

  server.on('upgrade', (req, clientSocket, head) => {
    const upstreamSocket = net.connect(STREAMLIT_PORT, STREAMLIT_HOST, () => {
      const headersLines = Object.entries(req.headers).map(([key, val]) => {
        const headerVal =
          key.toLowerCase() === 'host'
            ? `${STREAMLIT_HOST}:${STREAMLIT_PORT}`
            : Array.isArray(val)
              ? val.join(', ')
              : val || '';
        return `${key}: ${headerVal}`;
      });
      const rawReq =
        `${req.method || 'GET'} ${req.url || '/'} HTTP/${req.httpVersion}\r\n` +
        `${headersLines.join('\r\n')}\r\n\r\n`;
      upstreamSocket.write(rawReq);
      if (head && head.length > 0) {
        upstreamSocket.write(head);
      }
      upstreamSocket.pipe(clientSocket);
      clientSocket.pipe(upstreamSocket);
    });

    upstreamSocket.on('error', () => {
      clientSocket.destroy();
    });
    clientSocket.on('error', () => {
      upstreamSocket.destroy();
    });
  });

  server.listen(PORT, '0.0.0.0', () => {
    console.log(`SCRIPTXT proxy listening on http://0.0.0.0:${PORT} -> Streamlit :${STREAMLIT_PORT}`);
  });
}

void main();

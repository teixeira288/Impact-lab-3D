#!/usr/bin/env python3
"""Servidor local do Impact Lab 3D.

Uso:
    python3 serve.py                 # http://localhost:8000  (WebGPU funciona só neste computador)
    python3 serve.py --https         # https://<IP>:8000     (certificado autoassinado; para testar no celular pela rede Wi-Fi)
    python3 serve.py --port 9000

Por que existe: o Chrome só habilita WebGPU em "contexto seguro" (https:// ou http://localhost).
Este servidor também envia os tipos MIME corretos (.wasm, .wgsl, .js), desativa o cache (você sempre vê a
versão mais recente no celular) e imprime os endereços de acesso.
"""
import argparse, http.server, mimetypes, os, shutil, socket, ssl, subprocess, sys, tempfile

mimetypes.add_type('application/wasm', '.wasm')
mimetypes.add_type('text/plain; charset=utf-8', '.wgsl')
mimetypes.add_type('text/javascript; charset=utf-8', '.js')
mimetypes.add_type('text/javascript; charset=utf-8', '.mjs')


class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store, max-age=0')
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()

    def log_message(self, fmt, *args):
        if '--quiet' not in sys.argv:
            super().log_message(fmt, *args)


def lan_ips():
    ips = set()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('10.255.255.255', 1))
        ips.add(s.getsockname()[0])
        s.close()
    except OSError:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ips.add(info[4][0])
    except OSError:
        pass
    return sorted(i for i in ips if not i.startswith('127.'))


def make_cert(ips):
    if not shutil.which('openssl'):
        sys.exit('openssl não encontrado: instale-o ou use a opção do adb reverse / hospedagem HTTPS (veja o README).')
    d = tempfile.mkdtemp(prefix='impactlab-cert-')
    key, crt = os.path.join(d, 'key.pem'), os.path.join(d, 'cert.pem')
    san = ','.join(['DNS:localhost', 'IP:127.0.0.1'] + ['IP:' + i for i in ips])
    subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-keyout', key, '-out', crt, '-days', '30',
                    '-subj', '/CN=impact-lab-3d', '-addext', 'subjectAltName=' + san], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return crt, key


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', type=int, default=8000)
    ap.add_argument('--https', action='store_true', help='HTTPS com certificado autoassinado (para celular na mesma rede Wi-Fi)')
    ap.add_argument('--quiet', action='store_true')
    a = ap.parse_args()
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    ips = lan_ips()
    srv = http.server.ThreadingHTTPServer(('0.0.0.0', a.port), Handler)
    scheme = 'http'
    if a.https:
        crt, key = make_cert(ips)
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(crt, key)
        srv.socket = ctx.wrap_socket(srv.socket, server_side=True)
        scheme = 'https'
    print('\nImpact Lab 3D — servidor ativo (Ctrl+C para parar)\n')
    print(f'  Neste computador:   {scheme}://localhost:{a.port}')
    for ip in ips:
        print(f'  Na rede ({ip}):  {scheme}://{ip}:{a.port}')
    if not a.https:
        print('\n  ATENÇÃO: no celular, http://<IP> NÃO habilita WebGPU. Use --https, "adb reverse" ou hospedagem HTTPS (README).')
    else:
        print('\n  No celular o Chrome mostrará "Sua conexão não é particular": toque em Avançado > Continuar. É o certificado autoassinado local.')
    print(f'  Diagnóstico:        {scheme}://<endereço>:{a.port}/diagnostico.html\n')
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print('\nEncerrado.')


if __name__ == '__main__':
    main()

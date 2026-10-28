"""Run only with scripts/test-worker.sh in the isolated loopback namespace."""
import hashlib
import http.client
import http.server
import json
import os
from pathlib import Path
import signal
import socket
import sys
import threading
import unittest
from unittest.mock import patch
sys.path.insert(0, '/source/worker')
import render
import service
import ezdxf

class RenderingTests(unittest.TestCase):
    def test_known_legacy_glyph_indices(self):
        self.assertEqual(render.legacy_naskhd_glyphs('\u200c\u060c\u0642'), '\x9d\xa1\xde')
        self.assertEqual(render.legacy_naskhd_glyphs('ABC 123'), 'ABC 123')
        self.assertEqual(render.legacy_naskhd_glyphs('Ÿž'), '\x9f\x9e')

    def test_font_mapping_is_scoped(self):
        doc = ezdxf.new()
        doc.styles.new('Legacy', dxfattribs={'font':'C:\\Fonts\\naskhd.shx'})
        doc.styles.new('Unicode', dxfattribs={'font':'LiberationSans-Regular.ttf'})
        old = doc.modelspace().add_text('\u200c\u0642', dxfattribs={'style':'Legacy'})
        modern = doc.modelspace().add_text('\u200c\u0642', dxfattribs={'style':'Unicode'})
        render.prepare_fonts(doc, Path('/fonts'))
        self.assertEqual(old.dxf.text, '\x9d\xde')
        self.assertEqual(modern.dxf.text, '\u200c\u0642')
        self.assertEqual(doc.styles.get('Legacy').dxf.font, 'naskhd.shx')

    def test_layout_and_layer_metadata(self):
        from xml.etree import ElementTree as ET
        doc=ezdxf.new()
        doc.modelspace().add_line((0,0),(100,50),dxfattribs={'layer':'ModelLayer'})
        doc.layouts.get('Layout1').add_circle((10,10),5,dxfattribs={'layer':'PaperLayer'})
        path=Path('/scratch/layouts.dxf');doc.saveas(path)
        for index, expected in [(0,'ModelLayer'),(1,'PaperLayer')]:
            root=ET.fromstring(render.render(path, Path('/fonts'), index))
            info=json.loads(root.find('{http://www.w3.org/2000/svg}metadata').text)
            self.assertEqual(info['layout'],index)
            self.assertIn(expected,info['layers'])
            self.assertGreater(info['unitsPerSvgUnit'],0)
        with self.assertRaises(ValueError): render.render(path,Path('/fonts'),31)

    def test_parser_command_boundaries(self):
        config={'image':'a'*64,'fonts':'/fonts','scratch':'/scratch'}
        service.validate_config(config)
        args=service.container_command(config,'cadviewer-dummy','/scratch/input.dwg','dwg',2)
        for required in ('--network=none','--read-only','--cap-drop=ALL','--security-opt=no-new-privileges','--memory=2g','--pids-limit=64','--user=65534:65534'):
            self.assertIn(required,args)
        self.assertEqual(args[-2:],['--layout','2'])
        self.assertNotIn('/bin/sh', args)
        self.assertFalse(any('socket' in a or '/engine' in a for a in args))
        for invalid in ('dgn','../dwg','dwg;id'):
            with self.assertRaises(ValueError): service.container_command(config,'dummy','/scratch/a',invalid)
        with self.assertRaises(ValueError): service.container_command(config,'dummy','/scratch/a','dwg',32)

class GatewayTests(unittest.TestCase):
    def request(self, headers, expected):
        server=http.server.HTTPServer(('127.0.0.1',0),service.Gateway)
        server.token='d'*48;server.config={}
        result={}
        def client():
            conn=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=3)
            conn.request('POST','/convert',body=b'CAD',headers=headers)
            response=conn.getresponse();result['status']=response.status;result['body']=response.read();conn.close()
        with patch.object(service,'convert',return_value=b'<svg/>') as convert:
            thread=threading.Thread(target=client);thread.start()
            server.handle_request();thread.join(timeout=5);server.server_close()
            self.assertEqual(result['status'],expected)
            if expected==200: convert.assert_called_once_with({},b'CAD','dwg',2)
            else: convert.assert_not_called()
    def test_authorized(self): self.request({'Authorization':'Bearer '+'d'*48,'X-CAD-Format':'dwg','X-CAD-Layout':'2'},200)
    def test_unauthorized(self): self.request({'X-CAD-Format':'dwg'},401)
    def test_unsupported_format(self): self.request({'Authorization':'Bearer '+'d'*48,'X-CAD-Format':'dgn'},415)
    def test_invalid_layout(self): self.request({'Authorization':'Bearer '+'d'*48,'X-CAD-Format':'dwg','X-CAD-Layout':'../2'},400)
    def test_oversized_body(self): self.request({'Authorization':'Bearer '+'d'*48,'X-CAD-Format':'dwg','Content-Length':str(service.MAX_INPUT+1)},413)
    def test_transfer_encoding_rejected(self): self.request({'Authorization':'Bearer '+'d'*48,'X-CAD-Format':'dwg','Transfer-Encoding':'chunked'},400)

if __name__=='__main__':
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError()))
    unittest.main()
